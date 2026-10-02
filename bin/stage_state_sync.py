#!/usr/bin/env python3
"""stage_state_sync.py — кураторство, валидация и staging state/SPECS для bot-PR.

Используется шагом «Commit state» (update.yml) вместо `git add state/state.json
pkgs.json SPECS/`:

  * BASE (по умолчанию origin/master) — эталон рабочего дерева.
  * Bounded (непустая selection из CANDY_PACKAGE_ALLOWLIST или --selection):
      - изменённые entries state.json обязаны быть ⊆ selection;
      - pkgs.json и посторонние трек-файлы → abort;
      - спеки вне selection откатываются к BASE (churn дат/шаблона от
        gen_specs --all — остальные пакеты не трогаем);
      - спека selection-пакета с изменившейся целью обязана быть с новой
        Version (устаревшая/не перегенерированная → abort);
      - спека selection-пакета без сдвига цели, изменённая иначе чем дата → abort;
      - staged ≤ 1 + |selection| файлов (защита от «132 specs»).
  * Unbounded: чисто-датовый churn спек откатывается; контент-изменения и
    catch-up спек (Version == state) допустимы; версия спеки, не совпадающая
    ни с BASE, ни с state → abort; посторонние пути → abort.
  * Ничего не коммитит и не пушит — только git checkout (откат) + git add.

Exit 0 — staged (или «No changes»), exit 1 — abort с причиной в stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ALLOWLIST_ENV = "CANDY_PACKAGE_ALLOWLIST"
VERSION_RE = re.compile(r"^Version:\s*(\S+)", re.M)


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=check,
    )


def fail(msg: str) -> int:
    print(f"ABORT: {msg}")
    return 1


def parse_spec_version(text: str) -> str:
    m = VERSION_RE.search(text)
    return m.group(1) if m else ""


def pre_changelog(text: str) -> str:
    return text.split("%changelog", 1)[0]


def read_worktree(repo: Path, rel: str) -> str | None:
    try:
        return (repo / rel).read_text(encoding="utf-8")
    except OSError:
        return None


def read_base(repo: Path, base: str, rel: str) -> str | None:
    r = git(repo, "show", f"{base}:{rel}", check=False)
    return r.stdout if r.returncode == 0 else None


def parse_selection(explicit: str | None) -> list[str]:
    raw = explicit if explicit is not None else os.environ.get(ALLOWLIST_ENV, "")
    return [p.strip() for p in raw.split(",") if p.strip()]


def state_ver(st: dict, pkg: str) -> str:
    e = st.get(pkg)
    return str(e.get("ver", "")) if isinstance(e, dict) else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", default="", help="эталонный ref (default: origin/master)")
    ap.add_argument("--selection", default=None,
                    help="bounded allowlist; default — env CANDY_PACKAGE_ALLOWLIST")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    base = args.base
    if not base:
        for cand in ("origin/master", "FETCH_HEAD", "HEAD"):
            if git(repo, "rev-parse", "--verify", cand, check=False).returncode == 0:
                base = cand
                break
    if not base:
        return fail("нет эталонного ref (origin/master/FETCH_HEAD/HEAD)")

    selection = set(parse_selection(args.selection))
    bounded = bool(selection)

    # --- state.json: diff entries относительно BASE ---
    new_raw = read_worktree(repo, "state/state.json")
    old_raw = read_base(repo, base, "state/state.json")
    if new_raw is None:
        return fail("state/state.json отсутствует в рабочем дереве")
    if old_raw is None:
        return fail("state/state.json отсутствует в BASE")
    try:
        new_st, old_st = json.loads(new_raw), json.loads(old_raw)
    except ValueError as e:
        return fail(f"state/state.json — невалидный JSON: {e}")

    removed = sorted(set(old_st) - set(new_st))
    if removed:
        return fail(f"в state.json удалены entries: {','.join(removed)}")
    changed = sorted(k for k in new_st if old_st.get(k) != new_st.get(k))
    ver_changed = sorted(
        k for k in changed
        if not isinstance(old_st.get(k), dict)
        or old_st[k].get("ver") != new_st[k].get("ver")
    )

    if bounded:
        outside = [k for k in changed if k not in selection]
        if outside:
            return fail(
                f"изменённые entries state.json вне bounded selection: "
                f"{','.join(outside)} (selection: {','.join(sorted(selection))})"
            )

    # --- трек-файлы с изменениями относительно BASE ---
    diff = git(repo, "diff", "--name-only", base, "--").stdout.splitlines()
    state_changed = "state/state.json" in diff
    spec_diffs = [
        p for p in diff
        if p.startswith("SPECS/") and p.endswith(".spec") and "/" not in p[len("SPECS/"):]
    ]
    others = [
        p for p in diff
        if p not in {"state/state.json", "pkgs.json"} and p not in spec_diffs
    ]
    if others:
        return fail(f"посторонние изменённые трек-файлы: {','.join(others)}")
    if bounded and "pkgs.json" in diff:
        return fail("pkgs.json изменён в bounded-режиме (auto-triage должен быть NO-OP)")

    keep: list[str] = []
    reverted: list[str] = []

    # --- спеки ---
    for rel in spec_diffs:
        pkg = Path(rel).stem
        wt, bt = read_worktree(repo, rel), read_base(repo, base, rel)
        if wt is None:
            return fail(f"{rel}: спека удалена из рабочего дерева")
        if bt is None:
            return fail(f"{rel}: спеки нет в BASE (новый файл вне process)")
        wt_v, bt_v = parse_spec_version(wt), parse_spec_version(bt)
        s_v = state_ver(new_st, pkg)

        if bounded and pkg not in selection:
            reverted.append(rel)  # чужой пакет: churn дат/шаблона/drift — не трогаем
            continue

        if wt_v != bt_v:
            # версия спеки двигнулась — только вместе со своей state-целью
            if pkg not in ver_changed:
                if not bounded and wt_v == s_v:
                    keep.append(rel)  # catch-up спеки к уже существующей цели
                    continue
                return fail(
                    f"{rel}: Version {bt_v} -> {wt_v} без изменения state-цели"
                    + (f" (state ver {s_v})" if s_v else "")
                )
            if wt_v != s_v:
                return fail(
                    f"{rel}: Version спеки {wt_v} != state ver {s_v} "
                    f"(спека устарела/не перегенерена)"
                )
            keep.append(rel)
            continue

        # та же версия: чисто-датовый churn — откат; иный контент — по режиму
        if pre_changelog(wt) == pre_changelog(bt):
            reverted.append(rel)
            continue
        if bounded:
            return fail(
                f"{rel}: контент-изменение спеки selection-пакета "
                f"без сдвига state-цели"
            )
        keep.append(rel)

    # --- цель сдвинулась, но спека не приведена к новой Version ---
    for pkg in ver_changed:
        rel = f"SPECS/{pkg}.spec"
        wt = read_worktree(repo, rel)
        if wt is None:
            return fail(f"{rel}: спека отсутствует для изменившейся цели {pkg}")
        if parse_spec_version(wt) != state_ver(new_st, pkg):
            return fail(
                f"{rel}: Version спеки {parse_spec_version(wt)} != state ver "
                f"{state_ver(new_st, pkg)} для {pkg}"
            )
        if rel in spec_diffs and rel not in keep:
            return fail(f"{rel}: цель {pkg} сдвинулась, но спека не в staging")

    # --- откат churn ---
    for rel in reverted:
        git(repo, "checkout", base, "--", rel)

    # --- staging ---
    staged: list[str] = []
    if changed:
        git(repo, "add", "--", "state/state.json")
        staged.append("state/state.json")
    for rel in sorted(set(keep)):
        if git(repo, "diff", "--name-only", base, "--", rel).stdout.strip():
            git(repo, "add", "--", rel)
            staged.append(rel)
    if not bounded and "pkgs.json" in diff:
        git(repo, "add", "--", "pkgs.json")
        staged.append("pkgs.json")

    if bounded and len(staged) > 1 + len(selection):
        return fail(
            f"staged {len(staged)} файлов при bound 1+{len(selection)}="
            f"{1 + len(selection)}: {','.join(staged)}"
        )

    for rel in reverted:
        print(f"REVERTED: {rel}")
    if staged:
        print("STAGED:")
        for rel in staged:
            print(f"  {rel}")
    else:
        print("No changes to stage")
    print(
        f"OK: bounded={bounded} selection={','.join(sorted(selection)) or '-'} "
        f"state_changed={len(changed)} ver_changed={len(ver_changed)} "
        f"staged={len(staged)} reverted={len(reverted)} base={base}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
