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

Immutable-plan hardening (v2):
  * the plan carries EXACT `name@target` pairs; that planned target — never a
    re-fetched upstream value — is what the SRPM build, the repodata gate and
    the state/SPECS sync must use;
  * `materialize` re-fetches upstream ONLY for the bounded allowlist and fails
    closed if the planned target is not reproducible (upstream moved);
  * `state.<name>.locked == true` packages never enter the plan (locked);
  * before any COPR submit the open `bot/state-sync-*` PRs are checked
    fail-closed (API/HTTP/JSON/schema errors abort, never "0 open PR"); an
    open PR with the exact same content is reused, a different one aborts;
  * a planned target already published 8/8 with stale state/SPECS is recovered
    WITHOUT a rebuild (state-only reconcile);
  * enabling auto-merge is not completion: the run waits for the actual
    `merged` verdict and only then may be green.

Subcommands:
    plan               — print machine-readable changed-only plan (no mutation)
    materialize        — bounded state pin to exact planned targets + reproduce
    fingerprint        — sha256 fingerprint of the staged planned diff
    preflight          — fail-closed open bot-PR check (proceed/reuse/abort)
    observe-merge PR   — wait for the actual merge verdict of a bot PR
    gate-published     — list effective targets NOT published 8/8 (no mutation)
    revert-unpublished — reset state.json targets not published 8/8 to HEAD

This helper never submits, never commits, never pushes, never opens a PR.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import time
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
TARGET_RE = re.compile(r"[A-Za-z0-9.+~_:-]+")
ALLOWLIST_ENV = "CANDY_PACKAGE_ALLOWLIST"
PLAN_ENTRIES_ENV = "CANDY_PLAN_ENTRIES"
EXPECTED_FP_ENV = "CANDY_EXPECTED_FINGERPRINT"
STATE_PATH_ENV = "CANDY_STATE_PATH"
REPO_ENV = "GITHUB_REPOSITORY"
BOT_BRANCH_PREFIX = "bot/state-sync-"
GITHUB_API = "https://api.github.com"

MERGE_TIMEOUT_DEFAULT = 5400
MERGE_TIMEOUT_MIN = 60
MERGE_TIMEOUT_MAX = 21600
MERGE_POLL_DEFAULT = 30
MERGE_POLL_MIN = 5
MERGE_POLL_MAX = 900

# check-run conclusions that mean "not a success" for the required checks.
FAIL_CONCLUSIONS = frozenset(
    {"failure", "cancelled", "timed_out", "action_required", "startup_failure"})


def state_path() -> str:
    return os.environ.get(STATE_PATH_ENV, "state/state.json")


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


def locked_names(state: dict) -> set[str]:
    """Packages explicitly pinned by `state.<name>.locked == true`."""
    out: set[str] = set()
    if not isinstance(state, dict):
        return out
    for name, entry in state.items():
        if isinstance(entry, dict) and entry.get("locked") is True:
            out.add(name)
    return out


def state_matches_target(state: dict, name: str, target: str) -> bool:
    """True iff state.<name>.ver already represents `target` (base/same-commit)."""
    entry = state.get(name) if isinstance(state, dict) else None
    if not isinstance(entry, dict):
        return False
    ver = str(entry.get("ver", ""))
    if not ver:
        return False
    return (base_version(ver) == base_version(target)
            or same_commit_version(ver, target))


def format_entry(name: str, target: str) -> str:
    return f"{name}@{target}"


def parse_plan_entries(raw: str) -> list[tuple[str, str]]:
    """Parse an immutable `name@target ...` plan, fail-closed.

    Every whitespace token must be exactly `name@target` with a valid package
    name and a non-empty, grammar-clean target; duplicates abort. An empty or
    whitespace-only raw is an empty plan.
    """
    if raw is None or raw.strip() == "":
        return []
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for token in raw.split():
        name, sep, target = token.partition("@")
        if not sep or not PACKAGE_NAME_RE.fullmatch(name):
            raise PlanError(f"malformed plan entry: {token!r}")
        if not target or not TARGET_RE.fullmatch(target):
            raise PlanError(f"malformed plan target: {token!r}")
        if name in seen:
            raise PlanError(f"duplicate plan entry: {name!r}")
        seen.add(name)
        entries.append((name, target))
    return entries


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
                         max_wave: int,
                         locked: set[str] | None = None,
                         state: dict | None = None) -> dict:
    """Pure changed-only plan (no network) with immutable name@target entries.

    Returns dict with keys:
        plan               — build targets (<= max_wave, canonical order)
        build_entries      — exact `name@target` pairs for the build wave
        state_only         — targets already published 8/8 but with stale
                             state/SPECS (state-only reconcile, no rebuild)
        state_only_entries — exact `name@target` pairs for reconcile
        overflow           — changed targets beyond max_wave (deferred)
        active             — changed targets already had an active build
        unchanged          — already published 8/8 with matching state
        locked             — pinned by state.<name>.locked, never planned
        upstream_failed    — enabled package without a usable upstream target
        targets            — name -> exact planned target (all acted-on names)
    Raises PlanError when an enabled package has no usable upstream target.
    """
    locked = set(locked or ())
    plan: list[str] = []
    state_only: list[str] = []
    overflow: list[str] = []
    active_names: list[str] = []
    unchanged: list[str] = []
    upstream_failed: list[str] = []
    locked_out: list[str] = []
    targets: dict[str, str] = {}

    for name in order:
        if name not in enabled:
            continue
        if name in locked:
            # locked packages never participate in the autonomous plan
            locked_out.append(name)
            continue
        target = upstream.get(name, "")
        if not target:
            # per-package upstream unknown: never submit it; COPR/repodata
            # uncertainty (published state) is the fail-closed abort path.
            upstream_failed.append(name)
            continue
        targets[name] = target
        full = is_fully_published(name, target, published, chroots)
        if full and (state is None or state_matches_target(state, name, target)):
            unchanged.append(name)
            continue
        if full:
            # published 8/8 but state/SPECS still stale: recover state only,
            # never rebuild (state-only reconcile).
            state_only.append(name)
            continue
        if name in active:
            active_names.append(name)
            continue
        plan.append(name)

    build = plan[:max_wave]
    reconcile = state_only[:max_wave]
    return {
        "plan": build,
        "overflow": plan[max_wave:] + state_only[max_wave:],
        "active": active_names,
        "unchanged": unchanged,
        "upstream_failed": upstream_failed,
        "state_only": reconcile,
        "locked": locked_out,
        "targets": targets,
        "build_entries": [format_entry(n, targets[n]) for n in build],
        "state_only_entries": [format_entry(n, targets[n]) for n in reconcile],
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


def effective_with_allowlist(pkgs: list[dict], allowlist_raw: str,
                             state: dict | None = None) -> set[str]:
    enabled, _ = enabled_set(pkgs)
    allowed = parse_allowlist(allowlist_raw)
    if not allowed:
        return enabled
    unknown = [n for n in allowed if n not in enabled]
    if unknown:
        raise PlanError(f"allowlist references unknown/disabled: {unknown}")
    if state is not None:
        locked = locked_names(state)
        locked_allowed = [n for n in allowed if n in locked]
        if locked_allowed:
            raise PlanError(f"allowlist references locked packages: {locked_allowed}")
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
    locked = locked_names(state)
    allowed = parse_allowlist(allowlist_raw)
    if allowed:
        enabled = effective_with_allowlist(pkgs, allowlist_raw, state)
    if upstream is None:
        upstream = fetch_upstream(sorted(enabled))
    if published is None:
        published = fetch_all_published(chroots)
    if active is None:
        active = fetch_active_builds()

    result = compute_changed_plan(enabled, order, upstream, published,
                                  active, chroots, max_wave,
                                  locked=locked, state=state)
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


def resolve_merge_timeout(raw: str) -> int:
    if raw is None or str(raw).strip() == "":
        return MERGE_TIMEOUT_DEFAULT
    try:
        val = int(str(raw).strip())
    except ValueError:
        raise PlanError(f"merge timeout not an integer: {raw!r}")
    if val < MERGE_TIMEOUT_MIN or val > MERGE_TIMEOUT_MAX:
        raise PlanError(
            f"merge timeout {val} outside {MERGE_TIMEOUT_MIN}..{MERGE_TIMEOUT_MAX}")
    return val


def resolve_merge_poll(raw: str) -> int:
    if raw is None or str(raw).strip() == "":
        return MERGE_POLL_DEFAULT
    try:
        val = int(str(raw).strip())
    except ValueError:
        raise PlanError(f"merge poll not an integer: {raw!r}")
    if val < MERGE_POLL_MIN or val > MERGE_POLL_MAX:
        raise PlanError(f"merge poll {val} outside {MERGE_POLL_MIN}..{MERGE_POLL_MAX}")
    return val


# --------------------------------------------------------------------------
# Authenticated GitHub API (fail-closed) + open bot-PR guard + merge observer.
# --------------------------------------------------------------------------

def _http_json_auth(url: str, token: str, timeout: int = 60):
    req = urllib.request.Request(url, headers={
        "User-Agent": "candy-update-plan",
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            data = resp.read()
    except urllib.error.HTTPError as e:
        raise PlanError(f"HTTP {e.code} for {url}")
    except (urllib.error.URLError, OSError) as e:
        raise PlanError(f"network error for {url}: {e}")
    if not isinstance(status, int) or status < 200 or status >= 300:
        raise PlanError(f"non-2xx HTTP {status} for {url}")
    if not data:
        raise PlanError(f"empty HTTP body: {url}")
    try:
        return json.loads(data.decode("utf-8", "replace"))
    except json.JSONDecodeError as e:
        raise PlanError(f"invalid JSON from {url}: {e}")


def fetch_open_prs(repo: str, token: str) -> list:
    data = _http_json_auth(
        f"{GITHUB_API}/repos/{repo}/pulls?state=open&per_page=100", token)
    if not isinstance(data, list):
        raise PlanError("open PRs response is not a list (unexpected schema)")
    return data


def fetch_pr_files(repo: str, number: int, token: str) -> list:
    data = _http_json_auth(
        f"{GITHUB_API}/repos/{repo}/pulls/{number}/files?per_page=100", token)
    if not isinstance(data, list):
        raise PlanError("PR files response is not a list (unexpected schema)")
    return data


def fetch_pr(repo: str, number: int, token: str) -> dict:
    data = _http_json_auth(f"{GITHUB_API}/repos/{repo}/pulls/{number}", token)
    if not isinstance(data, dict):
        raise PlanError("PR response is not an object (unexpected schema)")
    return data


def fetch_check_runs(repo: str, sha: str, token: str) -> dict:
    data = _http_json_auth(
        f"{GITHUB_API}/repos/{repo}/commits/{sha}/check-runs", token)
    if not isinstance(data, dict):
        raise PlanError("check-runs response is not an object (unexpected schema)")
    return data


def is_bot_pr(pr) -> bool:
    if not isinstance(pr, dict):
        return False
    head = pr.get("head")
    if not isinstance(head, dict):
        return False
    ref = head.get("ref")
    return isinstance(ref, str) and ref.startswith(BOT_BRANCH_PREFIX)


def count_bot_prs(open_prs: list) -> int:
    return sum(1 for pr in open_prs if is_bot_pr(pr))


def pr_fingerprint(files: list) -> str:
    """Content fingerprint of a PR/commit file set: sorted filename + blob sha.

    Uses the resulting blob sha per changed file (not the branch prefix, title
    or package name), so a PR is reused only when its exact content matches.
    """
    if not isinstance(files, list):
        raise PlanError("PR files not a list")
    if len(files) >= 100:
        raise PlanError("PR files truncated (>=100) — content cannot be proven")
    lines: list[str] = []
    for f in files:
        if not isinstance(f, dict):
            raise PlanError("malformed PR file entry")
        fn, sha = f.get("filename"), f.get("sha")
        if not isinstance(fn, str) or not fn:
            raise PlanError("PR file missing filename")
        if not isinstance(sha, str) or not sha:
            raise PlanError(f"PR file {fn} missing blob sha")
        lines.append(f"{fn}\t{sha}")
    return hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()


def staged_fingerprint(repo: str = ".") -> str:
    """Fingerprint of the currently staged (index) diff: filename + index blob sha."""
    def g(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", repo, *args],
                              capture_output=True, text=True)

    names = g("diff", "--cached", "--name-only").stdout.split()
    if not names:
        raise PlanError("nothing staged: cannot fingerprint the planned diff")
    lines: list[str] = []
    for f in sorted(names):
        out = g("ls-files", "-s", "--", f).stdout.strip().splitlines()
        if not out:
            raise PlanError(f"staged file not in index: {f}")
        parts = out[0].split()
        if len(parts) < 2:
            raise PlanError(f"unexpected ls-files output for {f}")
        lines.append(f"{f}\t{parts[1]}")
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def evaluate_open_prs(open_prs: list, expected_fp: str, fetch_files) -> dict:
    """Fail-closed decision for open bot PRs before any COPR submit.

    PROCEED — no open bot PR (safe to build/create a PR).
    REUSE   — exactly one open bot PR whose content fingerprint equals the
              expected planned diff; reuse it and observe its merge.
    ABORT   — more than one bot PR, a different content, or content sameness
              cannot be proven (missing expected fingerprint).
    """
    if not isinstance(open_prs, list):
        raise PlanError("open PRs not a list")
    bots: list[dict] = []
    for pr in open_prs:
        if not isinstance(pr, dict):
            raise PlanError("malformed PR item")
        head = pr.get("head")
        if not isinstance(head, dict):
            raise PlanError("malformed PR head")
        if not isinstance(pr.get("number"), int) or not isinstance(head.get("ref"), str):
            raise PlanError("malformed PR number/ref (unexpected schema)")
        if is_bot_pr(pr):
            bots.append(pr)
    if not bots:
        return {"decision": "PROCEED", "reuse_pr": None,
                "reuse_branch": "", "reason": "no open bot PR"}
    if len(bots) > 1:
        return {"decision": "ABORT", "reuse_pr": None,
                "reuse_branch": "", "reason": "multiple open bot PRs"}
    pr = bots[0]
    if not expected_fp:
        return {"decision": "ABORT", "reuse_pr": None, "reuse_branch": "",
                "reason": "cannot prove planned content matches open bot PR"}
    fp = pr_fingerprint(fetch_files(pr["number"]))
    if fp == expected_fp:
        return {"decision": "REUSE", "reuse_pr": pr["number"],
                "reuse_branch": pr["head"]["ref"],
                "reason": "open bot PR matches planned content"}
    return {"decision": "ABORT", "reuse_pr": None, "reuse_branch": "",
            "reason": "open bot PR content differs from planned content"}


def merge_verdict(pr: dict, checks: dict | None = None) -> str:
    """Actual merge verdict: never treats auto-merge enablement as completion."""
    if not isinstance(pr, dict):
        raise PlanError("malformed PR object")
    if pr.get("merged") is True:
        return "merged"
    if pr.get("state") == "closed":
        return "closed_unmerged"
    if pr.get("mergeable") is False:
        return "conflict"
    if isinstance(checks, dict):
        runs = checks.get("check_runs")
        if isinstance(runs, list):
            for r in runs:
                if not isinstance(r, dict):
                    continue
                if (r.get("status") == "completed"
                        and r.get("conclusion") in FAIL_CONCLUSIONS):
                    return "checks_failed"
    return "pending"


def observe_until(pr_number: int, fetch_pr_fn, fetch_checks_fn, now, sleep,
                  timeout: int, poll: int, max_errors: int = 5) -> str:
    """Poll until the actual merge verdict or a terminal non-success.

    Returns merged | closed_unmerged | conflict | checks_failed | timeout |
    api_error. Enabling auto-merge alone never yields `merged`.
    """
    deadline = now() + timeout
    errs = 0
    while True:
        try:
            prj = fetch_pr_fn(pr_number)
            verdict = merge_verdict(prj)
            if verdict == "pending":
                sha = (prj.get("head") or {}).get("sha") if isinstance(prj.get("head"), dict) else None
                if sha:
                    verdict = merge_verdict(prj, fetch_checks_fn(sha))
            errs = 0
        except PlanError:
            errs += 1
            if errs >= max_errors:
                return "api_error"
            sleep(poll)
            continue
        if verdict == "merged":
            return "merged"
        if verdict in ("closed_unmerged", "conflict", "checks_failed"):
            return verdict
        if now() >= deadline:
            return "timeout"
        sleep(poll)


def cmd_plan() -> int:
    try:
        max_wave = resolve_max_wave(os.environ.get("CANDY_MAX_WAVE", ""))
        plan = build_plan(max_wave, os.environ.get(ALLOWLIST_ENV, ""))
    except PlanError as e:
        print(f"[PLAN-FAIL] {e}", file=sys.stderr)
        return 3
    build = plan["plan"]
    state_only = plan["state_only"]
    if state_only:
        # state-only reconcile takes precedence: converge state before new builds
        mode, allow = "state-only", state_only
    elif build:
        mode, allow = "build", build
    else:
        mode, allow = "none", []
    print("PLAN_SCHEMA=candy-update-plan/v2")
    print(f"CHROOTS={len(plan['chroots'])}")
    print(f"MAX_WAVE={plan['max_wave']}")
    print(f"ENABLED={plan['enabled_count']}")
    print(f"LOCKED={len(plan['locked'])}")
    print(f"UNCHANGED={len(plan['unchanged'])}")
    print(f"ACTIVE={len(plan['active'])}")
    print(f"UPSTREAM_FAILED={len(plan['upstream_failed'])}")
    print(f"OVERFLOW={len(plan['overflow'])}")
    print(f"STATE_ONLY={len(state_only)}")
    print(f"BUILD={len(build)}")
    print(f"MODE={mode}")
    print(f"BUILD_ENTRIES={' '.join(plan['build_entries'])}")
    print(f"STATE_ONLY_ENTRIES={' '.join(plan['state_only_entries'])}")
    print(f"ALLOWLIST_CSV={','.join(allow)}")
    print(f"BUILD_ALLOWLIST_CSV={','.join(build)}")
    print(f"STATE_ONLY_ALLOWLIST_CSV={','.join(state_only)}")
    print(f"LOCKED_NAMES={' '.join(plan['locked'])}")
    print(f"ACTIVE_NAMES={' '.join(plan['active'])}")
    print(f"UPSTREAM_FAILED_NAMES={' '.join(plan['upstream_failed'])}")
    print(f"OVERFLOW_NAMES={' '.join(plan['overflow'])}")
    if mode == "none":
        print("PLAN_EMPTY=1")
    return 0


def cmd_materialize() -> int:
    """Pin state.json to the exact planned targets, bounded + reproducible.

    Re-fetches upstream ONLY for the bounded allowlist and aborts (fail-closed)
    if the planned target is no longer reproducible — a re-fetch must never
    silently move the target after planning.
    """
    try:
        entries = parse_plan_entries(os.environ.get(PLAN_ENTRIES_ENV, ""))
        if not entries:
            raise PlanError("materialize: empty CANDY_PLAN_ENTRIES")
        if len(entries) > MAX_WAVE_HARD:
            raise PlanError(f"materialize: {len(entries)} entries > wave {MAX_WAVE_HARD}")
        names = [n for n, _ in entries]
        if len(set(names)) != len(names):
            raise PlanError("materialize: duplicate package name in plan")
        allowed = parse_allowlist(os.environ.get(ALLOWLIST_ENV, ""))
        if not allowed:
            raise PlanError("materialize: non-empty allowlist required")
        if set(names) != set(allowed):
            raise PlanError(
                f"materialize: allowlist {sorted(allowed)} != plan {sorted(names)}")
        state = load_state(state_path())
        locked = locked_names(state)
        if locked & set(names):
            raise PlanError(f"materialize: locked packages in plan: {sorted(locked & set(names))}")
        fresh = fetch_upstream(names)
        for name, target in entries:
            got = fresh.get(name, "")
            if not got:
                raise PlanError(f"materialize: cannot reproduce target for {name}")
            if (base_version(got) != base_version(target)
                    and not same_commit_version(got, target)):
                raise PlanError(
                    f"materialize: target changed after planning for {name}: "
                    f"{target} -> {got}")
        for name, target in entries:
            state.setdefault(name, {})
            state[name]["ver"] = target
            state[name]["ts"] = time.time()
        Path(state_path()).write_text(json.dumps(state, ensure_ascii=False, indent=1))
    except PlanError as e:
        print(f"[MATERIALIZE-FAIL] {e}", file=sys.stderr)
        return 3
    print(f"MATERIALIZED={len(entries)}")
    print("REPRODUCED=1")
    return 0


def cmd_fingerprint() -> int:
    try:
        fp = staged_fingerprint(".")
    except PlanError as e:
        print(f"[FINGERPRINT-FAIL] {e}", file=sys.stderr)
        return 3
    print(f"EXPECTED_FINGERPRINT={fp}")
    return 0


def cmd_preflight() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get(REPO_ENV, "")
    try:
        entries = parse_plan_entries(os.environ.get(PLAN_ENTRIES_ENV, ""))
    except PlanError as e:
        print(f"[PREFLIGHT-FAIL] {e}", file=sys.stderr)
        return 3
    if not entries:
        print("DECISION=PROCEED")
        print("OPEN_BOT_PRS=0")
        print("REUSE_PR=")
        print("REUSE_BRANCH=")
        print("REASON=no planned entries")
        return 0
    if not repo or not token:
        print("[PREFLIGHT-FAIL] missing GITHUB_REPOSITORY/GITHUB_TOKEN",
              file=sys.stderr)
        return 3
    expected_fp = os.environ.get(EXPECTED_FP_ENV, "")
    try:
        open_prs = fetch_open_prs(repo, token)
        result = evaluate_open_prs(
            open_prs, expected_fp,
            lambda n: fetch_pr_files(repo, n, token))
    except PlanError as e:
        print(f"[PREFLIGHT-FAIL] {e}", file=sys.stderr)
        return 3
    print(f"DECISION={result['decision']}")
    print(f"OPEN_BOT_PRS={count_bot_prs(open_prs)}")
    print(f"REUSE_PR={result['reuse_pr'] if result['reuse_pr'] is not None else ''}")
    print(f"REUSE_BRANCH={result['reuse_branch']}")
    print(f"REASON={result['reason']}")
    if result["decision"] == "ABORT":
        print("[PREFLIGHT-ABORT] open bot PR blocks submit (fail-closed)",
              file=sys.stderr)
        return 1
    return 0


def cmd_observe_merge(argv: list[str]) -> int:
    if len(argv) < 3:
        print("[OBSERVE-FAIL] usage: observe-merge PR_NUMBER", file=sys.stderr)
        return 3
    try:
        pr_number = int(argv[2])
    except ValueError:
        print("[OBSERVE-FAIL] PR number not an integer", file=sys.stderr)
        return 3
    repo = os.environ.get(REPO_ENV, "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not repo or not token:
        print("[OBSERVE-FAIL] missing GITHUB_REPOSITORY/GITHUB_TOKEN",
              file=sys.stderr)
        return 3
    try:
        timeout = resolve_merge_timeout(os.environ.get("CANDY_MERGE_TIMEOUT", ""))
        poll = resolve_merge_poll(os.environ.get("CANDY_MERGE_POLL", ""))
    except PlanError as e:
        print(f"[OBSERVE-FAIL] {e}", file=sys.stderr)
        return 3
    status = observe_until(
        pr_number,
        lambda n: fetch_pr(repo, n, token),
        lambda sha: fetch_check_runs(repo, sha, token),
        time.time, time.sleep, timeout, poll)
    print(f"MERGE_STATUS={status}")
    if status == "merged":
        print(f"MERGED_PR={pr_number}")
        return 0
    print(f"[OBSERVE-FAIL] PR {pr_number} not merged: {status}", file=sys.stderr)
    return 1


def cmd_gate_published() -> int:
    try:
        chroots = fetch_project_chroots()
        published = fetch_all_published(chroots)
        pkgs = load_pkgs()
        state = load_state(state_path())
        effective = effective_with_allowlist(
            pkgs, os.environ.get(ALLOWLIST_ENV, ""), state)
        revert = to_revert(state, published, effective, chroots)
    except PlanError as e:
        print(f"[GATE-FAIL] {e}", file=sys.stderr)
        return 3
    print(f"UNPUBLISHED={' '.join(revert)}")
    print(f"PUBLISHED_OK={len(effective) - len(revert)}")
    return 0


def cmd_revert_unpublished() -> int:
    try:
        chroots = fetch_project_chroots()
        published = fetch_all_published(chroots)
        pkgs = load_pkgs()
        state = load_state(state_path())
        effective = effective_with_allowlist(
            pkgs, os.environ.get(ALLOWLIST_ENV, ""), state)
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
    Path(state_path()).write_text(
        json.dumps(state, ensure_ascii=False, indent=1))
    print(f"Reverted {changed} unpublished state target(s): {' '.join(revert)}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: update-plan.py "
              "{plan|materialize|fingerprint|preflight|observe-merge|"
              "gate-published|revert-unpublished}", file=sys.stderr)
        return 1
    cmd = argv[1]
    if cmd == "plan":
        return cmd_plan()
    if cmd == "materialize":
        return cmd_materialize()
    if cmd == "fingerprint":
        return cmd_fingerprint()
    if cmd == "preflight":
        return cmd_preflight()
    if cmd == "observe-merge":
        return cmd_observe_merge(argv)
    if cmd == "gate-published":
        return cmd_gate_published()
    if cmd == "revert-unpublished":
        return cmd_revert_unpublished()
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    sys.exit(main(sys.argv))
