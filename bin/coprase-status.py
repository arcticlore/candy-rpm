#!/usr/bin/env python3
"""coprase-status.py — Check COPR build status with full pagination + version comparison.

Usage:
    coprase-status.py check       — print list of packages needing submission
    coprase-status.py submit      — slot-managed submit loop
    coprase-status.py clean       — list duplicate builds (informational)
"""

from __future__ import annotations
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

OWNER = "arcticlore"
PROJECT = "candy"
COPR_URL = "https://copr.fedorainfracloud.org/api_3"
PAGE_LIMIT = 100

# Slot management
MAX_BUILDS = 3
POLL_INTERVAL = 30
MAX_WAIT = 3600  # 1 hour total


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


def build_history(all_builds: list[dict]) -> dict[str, list[tuple[str, str]]]:
    """Build name -> [(state, version)] sorted by ID descending (newest first)."""
    history: dict[str, list[tuple[str, str]]] = {}
    for b in sorted(all_builds, key=lambda x: x.get("id", 0), reverse=True):
        sp = b.get("source_package", {})
        name = sp.get("name", "")
        state = b.get("state", "")
        ver = sp.get("version", "")
        if name:
            history.setdefault(name, []).append((state, ver))
    return history


def load_versions() -> dict[str, str]:
    """Load current target versions from state.json."""
    try:
        st = json.loads(Path("state/state.json").read_text())
        return {k: v.get("ver", "") for k, v in st.items() if isinstance(v, dict)}
    except Exception:
        return {}


def latest_succeeded_ver(history_entry: list[tuple[str, str]]) -> tuple[str, str]:
    """Return (version, full_version) of the latest succeeded build."""
    for state, ver in history_entry:
        if state == "succeeded":
            return ver, ver
    return "", ""


def needs_submission(name: str, current_ver: str, history_entry: list[tuple[str, str]]) -> bool:
    """Determine if a package needs submission.

    Returns True if:
    - No builds at all, OR
    - No succeeded build, OR
    - Latest succeeded version differs from current version
    """
    if not history_entry:
        return True  # never built

    for state, build_ver in history_entry:
        if state == "succeeded":
            # Strip release tag: "0.15.6-1" -> "0.15.6", "1.0.0" -> "1.0.0"
            base_ver = build_ver.split("-", 1)[0] if "-" in build_ver else build_ver
            if base_ver == current_ver:
                return False  # already succeeded at this version
            return True  # version differs, needs rebuild

    return True  # no succeeded build at all


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
    """Submit a single build to COPR."""
    if dry_run:
        print(f"  [DRY] Would submit: {srpm_path}")
        return True
    r = subprocess.run(
        ["copr-cli", "build", "--nowait", f"{OWNER}/{PROJECT}", srpm_path],
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        print(f"  [ERROR] copr-cli: {r.stderr[:200]}")
        return False
    if "Build was added" in r.stdout or "already exists" in r.stdout.lower():
        for line in r.stdout.splitlines():
            if "https://" in line:
                print(f"  [OK] {line.strip()}")
                break
        return True
    print(f"  [WARN] {r.stdout[:200]}")
    return False


def cmd_check():
    """Print packages needing submission."""
    print("Fetching all COPR builds (pagination)...")
    all_builds = fetch_all_builds(OWNER, PROJECT)
    print(f"Total builds fetched: {len(all_builds)}")

    history = build_history(all_builds)
    versions = load_versions()

    enabled = set()
    with open("pkgs.json") as f:
        for p in json.load(f).get("packages", []):
            if p.get("enabled", True):
                enabled.add(p["name"])

    needs = []
    ok = []
    skipped_ver = []
    for name in sorted(enabled):
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
            for st, bv in hist:
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


def cmd_submit():
    """Slot-managed submit loop."""
    print("Fetching all COPR builds (pagination)...")
    all_builds = fetch_all_builds(OWNER, PROJECT)
    print(f"Total builds fetched: {len(all_builds)}")

    history = build_history(all_builds)
    versions = load_versions()

    enabled = set()
    with open("pkgs.json") as f:
        for p in json.load(f).get("packages", []):
            if p.get("enabled", True):
                enabled.add(p["name"])

    # Determine what needs submission
    to_submit: list[str] = []
    for name in sorted(enabled):
        ver = versions.get(name, "")
        if needs_submission(name, ver, history.get(name, [])):
            srpm = glob.glob(f"SRPMS/{name}-*.src.rpm")
            if srpm:
                to_submit.append(name)

    print(f"Packages to submit: {len(to_submit)}")

    if not to_submit:
        print("Nothing to submit!")
        return

    srpms = {}
    for name in to_submit:
        files = glob.glob(f"SRPMS/{name}-*.src.rpm")
        if files:
            srpms[name] = files[0]

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


def cmd_clean():
    """List duplicate builds (informational)."""
    all_builds = fetch_all_builds(OWNER, PROJECT)
    history = build_history(all_builds)

    dups = {}
    for name, builds in history.items():
        succeeded = [ver for st, ver in builds if st == "succeeded"]
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
    elif cmd == "submit":
        cmd_submit()
    elif cmd == "clean":
        cmd_clean()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
