#!/usr/bin/env python3
"""Approve only the bounded validation run of an in-repository state-sync PR.

The repository's outside-contributor workflow policy treats github-actions[bot]
as a new contributor on every generated PR.  That leaves the pull_request copy
of validate.yml at ``action_required`` and blocks auto-merge even though the
exact-head workflow_dispatch checks are green.

This helper is intended only from a trusted ``pull_request_target`` workflow.
It never checks out PR code.  Before approving anything it proves that the PR
is an in-repository, github-actions[bot]-authored reconciliation branch and
that its complete file set is limited to modified state/state.json plus one or
more existing SPECS/*.spec files.  Every mismatch fails closed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BOT = "github-actions[bot]"
BRANCH_RE = re.compile(r"^bot/state-sync-[1-9][0-9]*-[1-9][0-9]*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SPEC_RE = re.compile(r"^SPECS/[A-Za-z0-9][A-Za-z0-9+._-]*\.spec$")
WORKFLOW_PATH = ".github/workflows/validate.yml"
MAX_FILES = 26


class ApprovalError(RuntimeError):
    pass


def validate_event(event: dict[str, Any], repo: str) -> tuple[int, str, str]:
    if event.get("action") not in {"opened", "reopened", "synchronize"}:
        raise ApprovalError(f"unsupported pull_request_target action: {event.get('action')!r}")
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        raise ApprovalError("pull_request payload missing")
    user = pr.get("user") or {}
    if user.get("login") != BOT or user.get("type") != "Bot":
        raise ApprovalError("PR author is not github-actions[bot]")
    base = pr.get("base") or {}
    head = pr.get("head") or {}
    if base.get("ref") != "master" or (base.get("repo") or {}).get("full_name") != repo:
        raise ApprovalError("PR base is not this repository's master")
    if (head.get("repo") or {}).get("full_name") != repo:
        raise ApprovalError("fork PRs are never auto-approved")
    branch = head.get("ref")
    sha = head.get("sha")
    if not isinstance(branch, str) or not BRANCH_RE.fullmatch(branch):
        raise ApprovalError(f"untrusted bot branch: {branch!r}")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ApprovalError(f"invalid PR head SHA: {sha!r}")
    number = pr.get("number") or event.get("number")
    if not isinstance(number, int) or number <= 0:
        raise ApprovalError("invalid PR number")
    return number, branch, sha


def validate_files(files: list[dict[str, Any]]) -> None:
    if not 2 <= len(files) <= MAX_FILES:
        raise ApprovalError(f"unexpected changed-file count: {len(files)}")
    names: list[str] = []
    for item in files:
        name = item.get("filename")
        status = item.get("status")
        if status != "modified":
            raise ApprovalError(f"non-modification in bot PR: {name!r} status={status!r}")
        if name != "state/state.json" and not (isinstance(name, str) and SPEC_RE.fullmatch(name)):
            raise ApprovalError(f"path outside bounded reconciliation scope: {name!r}")
        names.append(name)
    if names.count("state/state.json") != 1:
        raise ApprovalError("state/state.json must be modified exactly once")
    if not any(SPEC_RE.fullmatch(name) for name in names):
        raise ApprovalError("bot reconciliation must modify at least one spec")


def select_exact_run(runs: list[dict[str, Any]], sha: str) -> dict[str, Any] | None:
    exact = [r for r in runs if r.get("head_sha") == sha and r.get("event") == "pull_request"]
    if not exact:
        return None
    exact.sort(key=lambda r: int(r.get("id", 0)), reverse=True)
    run = exact[0]
    if run.get("path") != WORKFLOW_PATH:
        raise ApprovalError(f"unexpected workflow path: {run.get('path')!r}")
    return run


class GitHubAPI:
    def __init__(self, token: str, api_url: str = "https://api.github.com") -> None:
        if not token:
            raise ApprovalError("GITHUB_TOKEN is empty")
        self.base = api_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "candy-bot-bounded-run-approver",
        }

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode()
        headers = dict(self.headers)
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, headers=headers, method=method, data=data)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read()
                return None if not body else json.loads(body)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:1000]
            raise ApprovalError(f"GitHub API {method} {path}: HTTP {exc.code}: {detail}") from exc

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str) -> Any:
        return self.request("POST", path, {})


def approve(event: dict[str, Any], *, repo: str, api: GitHubAPI, timeout: int = 90,
            poll: int = 3) -> str:
    number, branch, sha = validate_event(event, repo)
    files = api.get(f"/repos/{repo}/pulls/{number}/files?per_page=100")
    if not isinstance(files, list):
        raise ApprovalError("changed-file response is not a list")
    validate_files(files)

    deadline = time.monotonic() + timeout
    query = urllib.parse.urlencode({"event": "pull_request", "branch": branch, "per_page": 100})
    while True:
        payload = api.get(f"/repos/{repo}/actions/workflows/validate.yml/runs?{query}")
        runs = payload.get("workflow_runs", []) if isinstance(payload, dict) else []
        run = select_exact_run(runs, sha)
        if run is not None:
            status, conclusion = run.get("status"), run.get("conclusion")
            run_id = run.get("id")
            if not isinstance(run_id, int) or run_id <= 0:
                raise ApprovalError("validation run has invalid id")
            if status == "completed" and conclusion == "action_required":
                actor = run.get("actor") or {}
                if actor.get("login") != BOT or actor.get("type") != "Bot":
                    raise ApprovalError("action-required validation actor is not github-actions[bot]")
                api.post(f"/repos/{repo}/actions/runs/{run_id}/approve")
                return f"approved bounded bot validation run {run_id} for PR #{number} @ {sha}"
            if status in {"queued", "in_progress", "waiting", "requested", "pending"}:
                return f"validation run {run_id} already active; approval not required"
            if status == "completed" and conclusion in {
                "success", "failure", "cancelled", "timed_out", "neutral", "skipped", "stale"
            }:
                return f"validation run {run_id} already completed with {conclusion}"
            raise ApprovalError(f"unexpected validation state: status={status!r} conclusion={conclusion!r}")
        if time.monotonic() >= deadline:
            raise ApprovalError(f"no exact-head pull_request validation found within {timeout}s")
        time.sleep(poll)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_PATH"), required=False)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), required=False)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    try:
        if not args.event or not args.repo:
            raise ApprovalError("--event and --repo are required")
        event = json.loads(Path(args.event).read_text())
        api = GitHubAPI(os.environ.get("GITHUB_TOKEN", ""), os.environ.get("GITHUB_API_URL", "https://api.github.com"))
        print(approve(event, repo=args.repo, api=api, timeout=args.timeout))
        return 0
    except (ApprovalError, OSError, json.JSONDecodeError) as exc:
        print(f"bounded bot approval refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
