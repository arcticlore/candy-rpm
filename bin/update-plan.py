#!/usr/bin/env python3
"""update-plan.py — changed-only, fail-closed plan/gate for scheduled COPR updates.

Policy (bounded autonomy for arcticlore/candy):
  * one daily schedule (wired in .github/workflows/update.yml);
  * changed-only: a package enters the submit plan ONLY when its fresh upstream
    version is genuinely absent from the published repodata of ALL configured
    chroots; an unchanged / same-version / release-bumped target never enters
    the plan;
  * a target counts as published ONLY when its base version is present in the
    repodata of every one of the 8 configured chroots;
  * active builds are never resubmitted (they are resume/wait, not new);
  * max-wave bounds one run (<= MAX_WAVE_DEFAULT);
  * ANY API/HTTP/JSON/repodata uncertainty is fail-closed: the planner aborts
    non-zero, it NEVER degrades into an empty "successful" plan.

Subcommands:
    plan               — print machine-readable changed-only plan (no mutation)
    gate-published     — list effective targets NOT published 8/8 (no mutation)
    revert-unpublished — reset state.json targets not published 8/8 to HEAD

This helper never submits, never commits, never pushes, never opens a PR.
"""

from __future__ import annotations

import gzip
import json
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

OWNER = "arcticlore"
PROJECT = "candy"
COPR_RESULTS = "https://download.copr.fedorainfracloud.org/results"
COPR_API = "https://copr.fedorainfracloud.org/api_3"

# The project's configured chroots: a target is "published" only after it is
# present in the repodata of ALL of them. Order is canonical (sorted).
EXPECTED_CHROOTS: tuple[str, ...] = (
    "fedora-43-aarch64",
    "fedora-43-x86_64",
    "fedora-44-aarch64",
    "fedora-44-x86_64",
    "fedora-45-aarch64",
    "fedora-45-x86_64",
    "fedora-rawhide-aarch64",
    "fedora-rawhide-x86_64",
)

MAX_WAVE_DEFAULT = 5
MAX_WAVE_HARD = 5

REPO_NS = "{http://linux.duke.edu/metadata/repo}"
COMMON_NS = "{http://linux.duke.edu/metadata/common}"
COMMIT_VER_RE = re.compile(r"^(\d{8})\.([0-9A-Za-z]+)$")
PACKAGE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+._-]*")
ALLOWLIST_ENV = "CANDY_PACKAGE_ALLOWLIST"


class PlanError(Exception):
    """Fail-closed planner error: uncertainty must never become a plan."""


def base_version(v: str) -> str:
    """Strip the RPM release part: '0.15.6-1' -> '0.15.6'."""
    return v.split("-", 1)[0] if "-" in v else v


def same_commit_version(old: str, new: str) -> bool:
    """YYYYMMDD.<hash>: identical hash == same upstream commit (date ignored)."""
    mo = COMMIT_VER_RE.match(old or "")
    mn = COMMIT_VER_RE.match(new or "")
    return bool(mo and mn and mo.group(2) == mn.group(2))


def is_fully_published(name: str, target: str,
                       published: dict[str, dict[str, set[str]]],
                       chroots: tuple[str, ...]) -> bool:
    """True iff `target` is present in the repodata of EVERY configured chroot.

    A release bump (same base version) counts as present; a date-only churn of
    a YYYYMMDD.<hash> version (same commit hash) counts as present too.
    """
    tb = base_version(target)
    for cr in chroots:
        versions = published.get(cr, {}).get(name)
        if not versions:
            return False
        if tb in versions:
            continue
        if any(same_commit_version(v, target) for v in versions):
            continue
        return False
    return True


def compute_changed_plan(enabled: set[str], order: list[str],
                         upstream: dict[str, str],
                         published: dict[str, dict[str, set[str]]],
                         active: set[str],
                         chroots: tuple[str, ...],
                         max_wave: int) -> dict:
    """Pure changed-only plan (no network).

    Returns dict with keys:
        plan      — targets to submit this run (<= max_wave, canonical order)
        overflow  — changed targets beyond max_wave (deferred to next run)
        active    — changed targets already had an active build (resume/wait)
        unchanged — already published 8/8 (or release/same-commit bump)
    Raises PlanError when an enabled package has no usable upstream target.
    """
    plan: list[str] = []
    overflow: list[str] = []
    active_names: list[str] = []
    unchanged: list[str] = []
    upstream_failed: list[str] = []

    for name in order:
        if name not in enabled:
            continue
        target = upstream.get(name, "")
        if not target:
            # per-package upstream unknown: never submit it; COPR/repodata
            # uncertainty (published state) is the fail-closed abort path.
            upstream_failed.append(name)
            continue
        if is_fully_published(name, target, published, chroots):
            unchanged.append(name)
            continue
        if name in active:
            active_names.append(name)
            continue
        plan.append(name)

    return {
        "plan": plan[:max_wave],
        "overflow": plan[max_wave:],
        "active": active_names,
        "unchanged": unchanged,
        "upstream_failed": upstream_failed,
    }


def to_revert(state: dict, published: dict[str, dict[str, set[str]]],
              effective: set[str], chroots: tuple[str, ...]) -> list[str]:
    """Effective targets whose state version is NOT published exact 8/8."""
    out: list[str] = []
    for name in sorted(effective):
        entry = state.get(name)
        if not isinstance(entry, dict):
            continue
        target = entry.get("ver", "")
        if not target:
            continue
        if not is_fully_published(name, target, published, chroots):
            out.append(name)
    return out


def should_open_pr(existing_automation_prs: list, has_diff: bool) -> bool:
    """At most ONE open automation state PR; identical/duplicate run is a no-op."""
    if not has_diff:
        return False
    return len(existing_automation_prs) == 0


# --------------------------------------------------------------------------
# I/O layer (network + git) — never mutates COPR.
# --------------------------------------------------------------------------

def _http_bytes(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "candy-update-plan"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            enc = (resp.headers.get("Content-Encoding") or "").lower()
    except urllib.error.HTTPError as e:
        raise PlanError(f"HTTP {e.code} for {url}")
    except (urllib.error.URLError, OSError) as e:
        raise PlanError(f"network error for {url}: {e}")
    if enc == "gzip" or (len(data) > 2 and data[0] == 0x1F and data[1] == 0x8B):
        try:
            data = gzip.decompress(data)
        except OSError:
            pass
    return data


def _http_json(url: str, timeout: int = 60) -> dict:
    data = _http_bytes(url, timeout)
    if not data:
        raise PlanError(f"empty HTTP body: {url}")
    try:
        return json.loads(data.decode("utf-8", "replace"))
    except json.JSONDecodeError as e:
        raise PlanError(f"invalid JSON from {url}: {e}")


def load_pkgs(path: str = "pkgs.json") -> list[dict]:
    try:
        return json.loads(Path(path).read_text()).get("packages", [])
    except Exception as e:
        raise PlanError(f"cannot load pkgs.json: {e}")


def load_state(path: str = "state/state.json") -> dict:
    try:
        return json.loads(Path(path).read_text())
    except Exception as e:
        raise PlanError(f"cannot load state.json: {e}")


def is_package_enabled(enabled: object) -> bool:
    if enabled is None:
        return True
    if isinstance(enabled, bool):
        return enabled
    if isinstance(enabled, str):
        return enabled not in ("false", "0")
    return True


def parse_allowlist(raw: str) -> list[str]:
    if raw is None or raw.strip() == "":
        return []
    names: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if not token or not PACKAGE_NAME_RE.fullmatch(token):
            raise PlanError(f"malformed allowlist token: {token!r}")
        names.append(token)
    return names


def fetch_project_chroots() -> tuple[str, ...]:
    data = _http_json(
        f"{COPR_API}/project?ownername={OWNER}&projectname={PROJECT}")
    repos = data.get("chroot_repos")
    if not isinstance(repos, dict) or not repos:
        raise PlanError("COPR project has no chroot_repos (uncertainty)")
    got = tuple(sorted(repos.keys()))
    if got != EXPECTED_CHROOTS:
        raise PlanError(
            "configured chroots changed: "
            f"expected {EXPECTED_CHROOTS}, got {got}")
    return got


def parse_primary_versions(data: bytes) -> dict[str, set[str]]:
    """name -> set of base versions from a primary.xml(.gz) document."""
    if len(data) > 2 and data[0] == 0x1F and data[1] == 0x8B:
        data = gzip.decompress(data)
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise PlanError(f"invalid primary repodata XML: {e}")
    out: dict[str, set[str]] = {}
    for pkg in root.iter(f"{COMMON_NS}package"):
        name_el = pkg.find(f"{COMMON_NS}name")
        ver_el = pkg.find(f"{COMMON_NS}version")
        if name_el is None or ver_el is None:
            continue
        name = (name_el.text or "").strip()
        ver = (ver_el.get("ver") or "").strip()
        if not name or not ver:
            continue
        out.setdefault(name, set()).add(ver)
    return out


def fetch_repodata_versions(chroot: str) -> dict[str, set[str]]:
    root_base = f"{COPR_RESULTS}/{OWNER}/{PROJECT}/{chroot}"
    repomd = _http_bytes(f"{root_base}/repodata/repomd.xml")
    try:
        root = ET.fromstring(repomd)
    except ET.ParseError as e:
        raise PlanError(f"invalid repomd.xml for {chroot}: {e}")
    href = None
    for data_el in root.iter(f"{REPO_NS}data"):
        if data_el.get("type") == "primary":
            loc = data_el.find(f"{REPO_NS}location")
            if loc is not None:
                href = loc.get("href")
            break
    if not href:
        raise PlanError(f"no primary location in repomd for {chroot}")
    primary = _http_bytes(f"{root_base}/{href}")
    versions = parse_primary_versions(primary)
    if not versions:
        raise PlanError(f"primary repodata for {chroot} is empty/unparsable")
    return versions


def fetch_all_published(chroots: tuple[str, ...]) -> dict[str, dict[str, set[str]]]:
    published: dict[str, dict[str, set[str]]] = {}
    for cr in chroots:
        published[cr] = fetch_repodata_versions(cr)
    return published


def fetch_active_builds() -> set[str]:
    data = _http_json(
        f"{COPR_API}/build/list?ownername={OWNER}&projectname={PROJECT}"
        "&limit=200&status=running+starting+pending+importing")
    items = data.get("items")
    if items is None:
        raise PlanError("COPR build list has no 'items' (uncertainty)")
    active = set()
    for b in items:
        sp = b.get("source_package", {})
        name = sp.get("name", "")
        if name and b.get("state") in ("running", "starting", "pending", "importing"):
            active.add(name)
    return active


def fetch_upstream(names: list[str]) -> dict[str, str]:
    """Latest upstream version per package via bin/api_ver.sh.

    A hard command failure (exception) is COPR-independent uncertainty and
    aborts. An empty result (no detectable release for that one package) is
    recorded as "" and the package is deferred — it is NEVER submitted.
    """
    out: dict[str, str] = {}
    for name in names:
        try:
            r = subprocess.run(["bin/api_ver.sh", name], capture_output=True,
                               text=True, timeout=90)
            ver = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""
        except Exception as e:
            raise PlanError(f"upstream fetch failed for {name}: {e}")
        out[name] = ver
    return out


def enabled_set(pkgs: list[dict]) -> tuple[set[str], list[str]]:
    order: list[str] = []
    enabled: set[str] = set()
    for p in pkgs:
        name = p.get("name")
        if not name:
            continue
        order.append(name)
        if is_package_enabled(p.get("enabled")):
            enabled.add(name)
    return enabled, order


def effective_with_allowlist(pkgs: list[dict], allowlist_raw: str) -> set[str]:
    enabled, _ = enabled_set(pkgs)
    allowed = parse_allowlist(allowlist_raw)
    if not allowed:
        return enabled
    unknown = [n for n in allowed if n not in enabled]
    if unknown:
        raise PlanError(f"allowlist references unknown/disabled: {unknown}")
    return set(allowed)


def build_plan(max_wave: int, allowlist_raw: str = "",
               pkgs: list[dict] | None = None,
               state: dict | None = None,
               upstream: dict[str, str] | None = None,
               published: dict | None = None,
               active: set[str] | None = None,
               chroots: tuple[str, ...] = EXPECTED_CHROOTS) -> dict:
    """Assemble the plan from pre-fetched inputs (injectable; pure-ish)."""
    if pkgs is None:
        pkgs = load_pkgs()
    if state is None:
        state = load_state()
    enabled, order = enabled_set(pkgs)
    allowed = parse_allowlist(allowlist_raw)
    if allowed:
        enabled = effective_with_allowlist(pkgs, allowlist_raw)
    if upstream is None:
        upstream = fetch_upstream(sorted(enabled))
    if published is None:
        published = fetch_all_published(chroots)
    if active is None:
        active = fetch_active_builds()

    result = compute_changed_plan(enabled, order, upstream, published,
                                  active, chroots, max_wave)
    result["enabled_count"] = len(enabled)
    result["chroots"] = list(chroots)
    result["max_wave"] = max_wave
    return result


def resolve_max_wave(raw: str) -> int:
    if raw is None or str(raw).strip() == "":
        return MAX_WAVE_DEFAULT
    try:
        val = int(str(raw).strip())
    except ValueError:
        raise PlanError(f"max-wave not an integer: {raw!r}")
    if val < 1 or val > MAX_WAVE_HARD:
        raise PlanError(f"max-wave {val} outside 1..{MAX_WAVE_HARD}")
    return val


def cmd_plan() -> int:
    import os
    try:
        max_wave = resolve_max_wave(os.environ.get("CANDY_MAX_WAVE", ""))
        plan = build_plan(max_wave, os.environ.get(ALLOWLIST_ENV, ""))
    except PlanError as e:
        print(f"[PLAN-FAIL] {e}", file=sys.stderr)
        return 3
    print("PLAN_SCHEMA=candy-update-plan/v1")
    print(f"CHROOTS={len(plan['chroots'])}")
    print(f"MAX_WAVE={plan['max_wave']}")
    print(f"ENABLED={plan['enabled_count']}")
    print(f"UNCHANGED={len(plan['unchanged'])}")
    print(f"ACTIVE={len(plan['active'])}")
    print(f"UPSTREAM_FAILED={len(plan['upstream_failed'])}")
    print(f"OVERFLOW={len(plan['overflow'])}")
    print(f"TO_SUBMIT={' '.join(plan['plan'])}")
    print(f"ALLOWLIST_CSV={','.join(plan['plan'])}")
    print(f"ACTIVE_NAMES={' '.join(plan['active'])}")
    print(f"UPSTREAM_FAILED_NAMES={' '.join(plan['upstream_failed'])}")
    print(f"OVERFLOW_NAMES={' '.join(plan['overflow'])}")
    if not plan["plan"]:
        print("PLAN_EMPTY=1")
    return 0


def cmd_gate_published() -> int:
    import os
    try:
        chroots = fetch_project_chroots()
        published = fetch_all_published(chroots)
        pkgs = load_pkgs()
        state = load_state()
        effective = effective_with_allowlist(pkgs, os.environ.get(ALLOWLIST_ENV, ""))
        revert = to_revert(state, published, effective, chroots)
    except PlanError as e:
        print(f"[GATE-FAIL] {e}", file=sys.stderr)
        return 3
    print(f"UNPUBLISHED={' '.join(revert)}")
    print(f"PUBLISHED_OK={len(effective) - len(revert)}")
    return 0


def cmd_revert_unpublished() -> int:
    import os
    try:
        chroots = fetch_project_chroots()
        published = fetch_all_published(chroots)
        pkgs = load_pkgs()
        state = load_state()
        effective = effective_with_allowlist(pkgs, os.environ.get(ALLOWLIST_ENV, ""))
        revert = to_revert(state, published, effective, chroots)
    except PlanError as e:
        print(f"[REVERT-FAIL] {e}", file=sys.stderr)
        return 3
    if not revert:
        print("No unpublished targets to revert")
        return 0
    head_raw = subprocess.run(
        ["git", "show", "HEAD:state/state.json"],
        capture_output=True, text=True)
    head_state = {}
    if head_raw.returncode == 0 and head_raw.stdout.strip():
        try:
            head_state = json.loads(head_raw.stdout)
        except json.JSONDecodeError:
            head_state = {}
    changed = 0
    for name in revert:
        prev = head_state.get(name)
        if isinstance(prev, dict) and prev.get("ver"):
            if state.get(name, {}).get("ver") != prev["ver"]:
                state[name] = prev
                changed += 1
    Path("state/state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=1))
    print(f"Reverted {changed} unpublished state target(s): {' '.join(revert)}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: update-plan.py {plan|gate-published|revert-unpublished}",
              file=sys.stderr)
        return 1
    cmd = argv[1]
    if cmd == "plan":
        return cmd_plan()
    if cmd == "gate-published":
        return cmd_gate_published()
    if cmd == "revert-unpublished":
        return cmd_revert_unpublished()
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
