#!/usr/bin/env python3
"""coprase-status.py — Check COPR build status with full pagination + version comparison.

Usage:
    coprase-status.py check       — print list of packages needing submission
    coprase-status.py versions    — refresh target versions from upstream (state.json)
    coprase-status.py submit      — slot-managed submit loop
    coprase-status.py clean       — list duplicate builds (informational)
"""

from __future__ import annotations
import glob
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

OWNER = "arcticlore"
PROJECT = "candy"
COPR_URL = "https://copr.fedorainfracloud.org/api_3"
PAGE_LIMIT = 100

# Slot management — keep it polite, we share COPR with other users
MAX_BUILDS = 2
POLL_INTERVAL = 60
MAX_WAIT = 7200  # 2 hours total

# copr-cli resilience: network flakes shouldn't kill the whole batch
SUBMIT_TIMEOUT = 180
SUBMIT_ATTEMPTS = 3

# Bounded-manual-run selection policy (fail-closed).
PACKAGE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+._-]*")
ALLOWLIST_ENV = "CANDY_PACKAGE_ALLOWLIST"


def is_package_enabled(enabled: object) -> bool:
    """Robust enabled semantics, compatible with gen_specs.Package.is_enabled().

    missing/None -> enabled; bool passthrough; legacy string "false"/"0" -> disabled;
    any other string -> enabled. Raw Python truthiness of a string is NEVER used
    for enablement, so a JSON `"enabled": "false"` cannot leak a package into
    the effective set (historical diagon bug, build 11022104).
    """
    if enabled is None:
        return True
    if isinstance(enabled, bool):
        return enabled
    if isinstance(enabled, str):
        return enabled not in ("false", "0")
    return True


def parse_package_allowlist(raw: str) -> list[str]:
    """Parse an explicit package allowlist, fail-closed (strict boundary).

    - raw that is None, empty or ENTIRELY whitespace -> [] (normal enabled mode);
    - any other raw value is EXPLICIT bounded intent and must pass every check:
      every comma-split token must be non-empty after trim and fullmatch the
      package-name grammar [A-Za-z0-9][A-Za-z0-9+._-]*; an exact duplicate
      (after trim) is a hard non-zero failure;
    - NO normalization: empty tokens and duplicates are NEVER dropped or merged
      — a visibly non-empty but ambiguous input can never widen to the normal set;
    - ordering is preserved; caller may sort for canonical logging.
    """
    if raw is None:
        return []
    s = str(raw)
    if s.strip() == "":
        return []
    names: list[str] = []
    seen: set[str] = set()
    for token in s.split(","):
        token = token.strip()
        if not token:
            raise SystemExit("[SELECTION-FAIL] empty package token in allowlist")
        if not PACKAGE_NAME_RE.fullmatch(token):
            raise SystemExit(f"[SELECTION-FAIL] malformed package name in allowlist: {token!r}")
        if token in seen:
            raise SystemExit(f"[SELECTION-FAIL] duplicate package name in allowlist: '{token}'")
        seen.add(token)
        names.append(token)
    return names


def select_effective(packages: list[dict], allowlist_raw: str) -> set[str]:
    """Fail-closed effective package set from pkgs.json + optional allowlist.

    - None / empty / whitespace-only allowlist -> the robust enabled set only
      (missing/bool/legacy-string policy);
    - any non-empty raw value -> EXPLICIT bounded intent: exactly the requested
      subset; unknown, disabled, malformed or duplicated package name is a hard
      non-zero failure, never a silent fallback to all/normal.
    """
    by_name: dict[str, dict] = {}
    for p in packages:
        if isinstance(p, dict) and p.get("name"):
            by_name[p["name"]] = p

    allowed = parse_package_allowlist(allowlist_raw)
    if not allowed:
        return {n for n, p in by_name.items() if is_package_enabled(p.get("enabled"))}

    effective: set[str] = set()
    for name in allowed:
        p = by_name.get(name)
        if p is None:
            raise SystemExit(f"[SELECTION-FAIL] allowlist: unknown package '{name}'")
        if not is_package_enabled(p.get("enabled")):
            raise SystemExit(f"[SELECTION-FAIL] allowlist: package '{name}' is disabled")
        effective.add(name)
    return effective


def load_pkg_list() -> list[dict]:
    """Load the packages list from pkgs.json (no filtering)."""
    return json.loads(Path("pkgs.json").read_text()).get("packages", [])


def current_effective_set() -> set[str]:
    """Effective package set from CANDY_PACKAGE_ALLOWLIST + pkgs.json."""
    return select_effective(load_pkg_list(), os.environ.get(ALLOWLIST_ENV, ""))


def audit_effective(effective: set[str]) -> None:
    """Log the canonical effective package set (no secrets)."""
    raw = os.environ.get(ALLOWLIST_ENV, "")
    if parse_package_allowlist(raw):
        print(f"  [SEL] BOUNDED: {','.join(sorted(effective))}")
    else:
        print(f"  [SEL] allowlist empty: normal enabled set ({len(effective)} packages)")


def submit_candidates(effective: set[str],
                      history: dict[str, list[tuple[str, str, int]]],
                      versions: dict[str, str], force: bool) -> list[str]:
    """Candidate packages to submit, strictly within the effective set.

    `force` reorders selection (bypasses needs_submission()) but can NEVER
    widen beyond the effective (already fail-closed) set.
    """
    candidates: list[str] = []
    for name in order_enabled(effective, history):
        ver = versions.get(name, "")
        if force or needs_submission(name, ver, history.get(name, [])):
            candidates.append(name)
    return candidates


def copr_api(endpoint: str, extra: str = "") -> dict:
    """Query COPR API."""
    url = f"{COPR_URL}/{endpoint}"
    if extra:
        url += f"?{extra}"
    try:
        r = subprocess.run(
            ["curl", "-4", "-s", "--connect-timeout", "10", "--max-time", "30", url],
            capture_output=True, text=True, timeout=35,
        )
        return json.loads(r.stdout)
    except Exception as e:
        print(f"  [WARN] COPR API error: {e}", file=sys.stderr)
        return {}


def fetch_all_builds(owner: str, project: str) -> list[dict]:
    """Fetch ALL builds with pagination."""
    all_builds: list[dict] = []
    offset = 0
    while True:
        data = copr_api(
            "build/list",
            f"ownername={owner}&projectname={project}&limit={PAGE_LIMIT}&offset={offset}",
        )
        items = data.get("items", [])
        all_builds.extend(items)
        if len(items) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT
        time.sleep(0.5)  # polite pagination
    return all_builds


def build_history(all_builds: list[dict]) -> dict[str, list[tuple[str, str, int]]]:
    """Build name -> [(state, version, submitted_on)] sorted by ID descending (newest first)."""
    history: dict[str, list[tuple[str, str, int]]] = {}
    for b in sorted(all_builds, key=lambda x: x.get("id", 0), reverse=True):
        sp = b.get("source_package", {})
        name = sp.get("name", "")
        state = b.get("state", "")
        ver = sp.get("version", "")
        ts = b.get("submitted_on", 0)
        if name:
            history.setdefault(name, []).append((state, ver, ts))
    return history


def load_versions() -> dict[str, str]:
    """Load current target versions from state.json."""
    try:
        st = json.loads(Path("state/state.json").read_text())
        return {k: v.get("ver", "") for k, v in st.items() if isinstance(v, dict)}
    except Exception:
        return {}


def latest_succeeded_ver(history_entry: list[tuple[str, str, int]]) -> tuple[str, str]:
    """Return (version, full_version) of the latest succeeded build."""
    for state, ver, _ in history_entry:
        if state == "succeeded":
            return ver, ver
    return "", ""


def needs_submission(name: str, current_ver: str, history_entry: list[tuple[str, str, int]]) -> bool:
    """Determine if a package needs submission.

    Returns True if:
    - No builds at all, OR
    - No succeeded build, OR
    - Latest succeeded version differs from current version
    """
    if not history_entry:
        return True  # never built

    for state, build_ver, _ in history_entry:
        if state == "succeeded":
            # Strip release tag: "0.15.6-1" -> "0.15.6", "1.0.0" -> "1.0.0"
            base_ver = build_ver.split("-", 1)[0] if "-" in build_ver else build_ver
            if base_ver == current_ver:
                return False  # already succeeded at this version
            return True  # version differs, needs rebuild

    return True  # no succeeded build at all


def load_prio() -> dict[str, int]:
    """Пакет -> prio из pkgs.json (по умолчанию 5)."""
    prio: dict[str, int] = {}
    try:
        with open("pkgs.json") as f:
            for p in json.load(f).get("packages", []):
                prio[p["name"]] = int(p.get("prio") or 5)
    except Exception:
        pass
    return prio


def failure_age(history_entry: list[tuple[str, str, int]], now: float | None = None) -> float:
    """Возраст последнего failed/canceled билда в секундах.

    Приоритетная сортировка: чем дольше пакет валяется в failed/canceled —
    тем раньше его берут в обработку.
    """
    if now is None:
        now = time.time()
    for _state, _ver, ts in history_entry:
        if _state in ("failed", "canceled") and ts:
            try:
                age = now - float(ts)
            except (TypeError, ValueError):
                continue
            return max(0.0, age)
    return 0.0


def order_enabled(enabled: set[str], history: dict[str, list[tuple[str, str, int]]]) -> list[str]:
    """Сортировка: prio (ниже = раньше), затем возраст failed/canceled (дольше = раньше)."""
    now = time.time()
    prio_of = load_prio()
    return sorted(
        enabled,
        key=lambda n: (prio_of.get(n, 5), -failure_age(history.get(n, []), now), n),
    )


def get_copr_active() -> dict[str, str]:
    """Get current active build states from COPR."""
    data = copr_api(
        "build/list",
        f"ownername={OWNER}&projectname={PROJECT}&limit=200&status=running+starting+pending+importing",
    )
    states: dict[str, str] = {}
    for b in data.get("items", []):
        sp = b.get("source_package", {})
        name = sp.get("name", "")
        state = b.get("state", "")
        if name and state in ("running", "starting", "pending", "importing"):
            states[name] = state
    return states


def submit_build(srpm_path: str, dry_run: bool = False) -> bool:
    """Submit a single build to COPR (copr-cli with timeout + retries)."""
    if dry_run:
        print(f"  [DRY] Would submit: {srpm_path}")
        return True
    for attempt in range(1, SUBMIT_ATTEMPTS + 1):
        if attempt > 1:
            print(f"  [RETRY {attempt}/{SUBMIT_ATTEMPTS}] {srpm_path}")
            time.sleep(5)
        try:
            r = subprocess.run(
                ["copr-cli", "build", "--nowait", f"{OWNER}/{PROJECT}", srpm_path],
                capture_output=True, text=True, timeout=SUBMIT_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            print(f"  [WARN] copr-cli timed out after {SUBMIT_TIMEOUT}s (attempt {attempt}/"
                  f"{SUBMIT_ATTEMPTS})")
            continue
        except Exception as e:
            print(f"  [WARN] copr-cli error: {e}")
            continue
        if r.returncode != 0:
            print(f"  [ERROR] copr-cli (attempt {attempt}): {r.stderr[:200]}")
            if "not found" in r.stderr.lower() or "command" in r.stderr.lower():
                return False  # copr-cli/config broken — no point retrying
            continue
        if "Build was added" in r.stdout or "already exists" in r.stdout.lower():
            for line in r.stdout.splitlines():
                if "https://" in line:
                    print(f"  [OK] {line.strip()}")
                    break
            return True
        print(f"  [WARN] {r.stdout[:200]}")
        return False
    print(f"  [FAIL] {srpm_path} — not submitted after {SUBMIT_ATTEMPTS} attempts")
    return False


def cmd_versions():
    """Обновить целевые версии (state.json) из апстрима — «штука» про обновления.

    Для каждого enabled-пакета: bin/api_ver.sh -> последняя апстрим-версия.
    Если она отличается от state.json — цель обновляется, и следующий check
    честно скажет «нужен сабмит». Пиннутые (.version в pkgs.json) не трогаем.
    Требует jq/curl (в контейнере есть) и GITHUB_TOKEN для github-API.
    """
    with open("pkgs.json") as f:
        pkgs = json.load(f).get("packages", [])
    st_path = Path("state/state.json")
    try:
        st = json.loads(st_path.read_text())
    except Exception:
        st = {}

    effective = current_effective_set()
    audit_effective(effective)

    updated = same = failed = 0
    for p in pkgs:
        name = p["name"]
        if name not in effective:
            continue
        if p.get("version"):  # пин — цель фиксирована
            continue
        try:
            r = subprocess.run(["bin/api_ver.sh", name], capture_output=True,
                               text=True, timeout=60)
            up = r.stdout.strip()
        except Exception as e:
            up = ""
        if not up:
            print(f"  [FAIL] {name}: апстрим недоступен")
            failed += 1
            continue
        old = st.get(name, {}).get("ver", "") if isinstance(st.get(name), dict) else ""
        if old == up:
            same += 1
            continue
        st.setdefault(name, {})["ver"] = up
        st[name]["ts"] = time.time()
        print(f"  [NEW]  {name}: {old or '(нет цели)'} -> {up}")
        updated += 1
    st_path.write_text(json.dumps(st, ensure_ascii=False, indent=2))
    print(f"\nЦели обновлены: {updated}, без изменений: {same}, не проверилось: {failed}")


def cmd_check():
    """Print packages needing submission."""
    print("Fetching all COPR builds (pagination)...")
    all_builds = fetch_all_builds(OWNER, PROJECT)
    print(f"Total builds fetched: {len(all_builds)}")

    history = build_history(all_builds)
    versions = load_versions()

    enabled = current_effective_set()
    audit_effective(enabled)

    needs = []
    ok = []
    skipped_ver = []
    for name in order_enabled(enabled, history):
        ver = versions.get(name, "")
        hist = history.get(name, [])
        if needs_submission(name, ver, hist):
            srpm = glob.glob(f"SRPMS/{name}-*.src.rpm")
            if not srpm:
                needs.append((name, "no SRPM", ver))
            else:
                needs.append((name, "has SRPM", ver))
        else:
            succ_ver = ""
            for st, bv, _ in hist:
                if st == "succeeded":
                    succ_ver = bv.split("-", 1)[0] if "-" in bv else bv
                    break
            ok.append((name, succ_ver, ver))

    print(f"\nNeed submission: {len(needs)}")
    for name, reason, ver in needs:
        print(f"  {name} ({reason}, ver={ver})")
    print(f"\nAlready OK: {len(ok)}")
    for name, succ_ver, target_ver in ok[:20]:
        print(f"  {name}: succeeded at {succ_ver} (target={target_ver})")


def pick_srpm(name: str, files: list[str], target_ver: str) -> str:
    """Выбрать SRPM по целевой версии (иначе по самому свежему mtime).

    Алфавитный первый попавшийся может быть устаревшим (Rio-0.5.26 старее
    Rio-0.5.27 и в glob идёт первым) — тогда в COPR вечно уезжала старая
    версия, а новая цель так и не собиралась.
    """
    if target_ver:
        for f in files:
            if f"{name}-{target_ver}-" in os.path.basename(f):
                return f
    return max(files, key=lambda f: os.stat(f).st_mtime)


def cmd_submit():
    """Slot-managed submit loop."""
    print("Fetching all COPR builds (pagination)...")
    all_builds = fetch_all_builds(OWNER, PROJECT)
    print(f"Total builds fetched: {len(all_builds)}")

    history = build_history(all_builds)
    versions = load_versions()

    enabled = current_effective_set()
    audit_effective(enabled)

    if not all_builds:
        print("[ABORT] COPR API вернул 0 билдов (сеть/API недоступны) — "
              "подтверждения статуса нет, чтобы не плодить дубликаты.",
              file=sys.stderr)
        return

    # Determine what needs submission
    force = "--force" in sys.argv
    to_submit = submit_candidates(enabled, history, versions, force)

    print(f"Packages to submit: {len(to_submit)}")

    if not to_submit:
        print("Nothing to submit!")
        return

    srpms = {}
    for name in to_submit:
        files = glob.glob(f"SRPMS/{name}-*.src.rpm")
        if files:
            srpms[name] = pick_srpm(name, files, versions.get(name, ""))

    submitted = set()
    start_time = time.time()

    while to_submit:
        elapsed = time.time() - start_time
        if elapsed > MAX_WAIT:
            print(f"\n[DONE] Timeout ({MAX_WAIT}s). Submitted: {len(submitted)}")
            break

        active = get_copr_active()
        active_count = len(active)
        free_slots = MAX_BUILDS - active_count

        print(f"[{time.strftime('%H:%M:%S')}] active={active_count}/{MAX_BUILDS} "
              f"free={free_slots} submitted={len(submitted)} remaining={len(to_submit)}")

        if free_slots <= 0:
            print(f"  All slots full, waiting {POLL_INTERVAL}s...")
            time.sleep(POLL_INTERVAL)
            continue

        # Submit up to free_slots packages
        batch = to_submit[:free_slots]
        for name in batch:
            if name not in srpms:
                print(f"  [SKIP] {name}: no SRPM")
                to_submit.remove(name)
                continue

            print(f"  [SUBMIT] {name}")
            if submit_build(srpms[name]):
                submitted.add(name)
                to_submit.remove(name)
            else:
                print(f"  [FAIL] {name}")
                to_submit.remove(name)  # don't retry failures

            time.sleep(2)  # rate limit

        if to_submit:
            time.sleep(POLL_INTERVAL)

    print(f"\nTotal submitted: {len(submitted)}")
    print(f"Remaining: {len(to_submit)}")
    if to_submit:
        print(f"Remaining packages: {', '.join(to_submit[:30])}")


def cmd_selection():
    """Report the effective package selection (fail-closed, machine-readable).

    Used by update.yml to gate post-submit helpers identically to the parser
    policy: BOUNDED when the allowlist is non-empty, ALL otherwise.
    """
    effective = current_effective_set()
    raw = os.environ.get(ALLOWLIST_ENV, "")
    bounded = bool(parse_package_allowlist(raw))
    print(f"SELECTION_MODE: {'BOUNDED' if bounded else 'ALL'}")
    if bounded:
        print("EFFECTIVE NAMES: " + ",".join(sorted(effective)))
    else:
        print(f"EFFECTIVE NAMES: {len(effective)}")


def cmd_clean():
    """List duplicate builds (informational)."""
    all_builds = fetch_all_builds(OWNER, PROJECT)
    history = build_history(all_builds)

    dups = {}
    for name, builds in history.items():
        succeeded = [ver for st, ver, _ in builds if st == "succeeded"]
        if len(builds) > 5:
            dups[name] = len(builds)
        if len(succeeded) > 1:
            print(f"  {name}: {len(succeeded)} succeeded builds: {succeeded[:5]}")

    print(f"\nPackages with >5 total builds: {len(dups)}")
    for name, count in sorted(dups.items(), key=lambda x: -x[1])[:20]:
        print(f"  {name}: {count} builds")


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    if len(sys.argv) < 2:
        print("Usage: coprase-status.py {check|submit|clean}")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "check":
        cmd_check()
    elif cmd == "versions":
        cmd_versions()
    elif cmd == "submit":
        cmd_submit()
    elif cmd == "selection":
        cmd_selection()
    elif cmd == "clean":
        cmd_clean()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
