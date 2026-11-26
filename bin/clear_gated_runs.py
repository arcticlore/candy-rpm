#!/usr/bin/env python3
"""clear_gated_runs.py — снять редундантный gated run на bot-PR (fail-closed).

Зачем. PR, созданный встроенным GITHUB_TOKEN, сам не запускает CI, поэтому
волна дополнительно делает явный `workflow_dispatch` validate.yml на точной
bot-ветке — именно его checks и становятся required contexts. Но GitHub, помимо
этого, заводит на тот же head SHA ПУСТОЙ `pull_request` run и гасит его как
`action_required` («workflow awaiting approval»). Jobs в нём нет, ни одного
check он не даёт — зато merge box остаётся BLOCKED, auto-merge не наступает
никогда, и полностью зелёный PR висит открытым до таймаута observe-merge.

Что делает скрипт. Находит на ТОЧНОМ head SHA ровно такие run'ы (событие
pull_request/pull_request_target, ветка bot/state-sync-*, conclusion
action_required) и снимает их: сначала approve, и только при его отказе —
DELETE. Порядок проверен на candy-opensuse #89: удаление прошло успешно, но
merge box остался BLOCKED, а statusCheckRollup головного коммита опустел —
удалённый pull_request-прогон уносит с собой обязательные контексты. Любая неопределённость (отказ API,
битый JSON, чужой SHA, не снятый run, таймаут) = ненулевой код выхода:
молча оставить PR в BLOCKED нельзя.

Используется только run-scoped GITHUB_TOKEN; личный PAT не читается.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Callable, Sequence

GITHUB_API = "https://api.github.com"
BRANCH_PREFIX = "bot/state-sync-"
GATED_EVENTS = frozenset({"pull_request", "pull_request_target"})
GATED_CONCLUSION = "action_required"
USER_AGENT = "candy-clear-gated-runs"


class GateError(RuntimeError):
    """Неопределённость или отказ — merge bot-PR считается незащищённым."""


def http_request(method: str, url: str, token: str, timeout: int = 60):
    """(status, parsed_json|None). Любой не-2xx/битый JSON = GateError."""
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": USER_AGENT,
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            body = resp.read()
    except urllib.error.HTTPError as exc:
        raise GateError(f"HTTP {exc.code} for {method} {url}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise GateError(f"network error for {method} {url}: {exc}") from exc
    if not isinstance(status, int) or status < 200 or status >= 300:
        raise GateError(f"non-2xx HTTP {status} for {method} {url}")
    if not body:
        return status, None
    try:
        return status, json.loads(body.decode("utf-8", "replace"))
    except json.JSONDecodeError as exc:
        raise GateError(f"invalid JSON from {method} {url}: {exc}") from exc


def gated_runs(repo: str, head_sha: str, branch: str, token: str,
               request: Callable[..., tuple] = http_request) -> list[dict]:
    """Только gated run'ы этого PR: точный SHA, точная bot-ветка, pull_request."""
    if not branch.startswith(BRANCH_PREFIX):
        raise GateError(f"ветка вне {BRANCH_PREFIX}*: {branch!r}")
    if not head_sha or len(head_sha) < 7:
        raise GateError(f"подозрительный head SHA: {head_sha!r}")
    if not repo or "/" not in repo:
        raise GateError(f"подозрительный repo: {repo!r}")
    url = f"{GITHUB_API}/repos/{repo}/actions/runs?head_sha={head_sha}&per_page=100"
    _status, data = request("GET", url, token)
    if not isinstance(data, dict):
        raise GateError(f"неожиданный ответ actions/runs для {head_sha}")
    runs = data.get("workflow_runs")
    if not isinstance(runs, list):
        raise GateError(f"workflow_runs отсутствуют в ответе для {head_sha}")
    found: list[dict] = []
    for run in runs:
        if not isinstance(run, dict):
            raise GateError("элемент workflow_runs не объект")
        if run.get("head_sha") != head_sha:
            raise GateError(
                f"actions/runs вернул чужой head_sha={run.get('head_sha')}, "
                f"ожидался {head_sha}")
        if run.get("event") not in GATED_EVENTS:
            continue
        if run.get("head_branch") != branch:
            continue
        if run.get("conclusion") != GATED_CONCLUSION:
            continue
        run_id = run.get("id")
        if not isinstance(run_id, int) or run_id <= 0:
            raise GateError(f"подозрительный id у gated run: {run_id!r}")
        found.append(run)
    return found


def clear_gated_runs(repo: str, head_sha: str, branch: str, token: str,
                     *,
                     timeout_s: float = 300.0,
                     poll_s: float = 10.0,
                     grace_s: float = 90.0,
                     request: Callable[..., tuple] = http_request,
                     clock: Callable[[], float] = time.monotonic,
                     sleep: Callable[[float], None] = time.sleep,
                     ) -> list[tuple[str, int]]:
    """Снимает gated run'ы до их исчезновения. Отказ/таймаут = GateError.

    Пустой первый опрос ещё не означает, что гасить нечего: GitHub заводит
    gated `pull_request` run асинхронно, и на быстром раннере мы успеваем
    спросить раньше, чем он появится. Ровно так и вышло в run 45820026991 —
    скрипт напечатал «none», волна включила auto-merge, после чего run
    всё-таки возник и навсегда оставил PR #69 в BLOCKED: observe-merge
    добросовестно прождал 90 минут и покрасил прогон. Поэтому «ничего нет»
    принимается только после grace_s ожидания; как только хоть один run
    снят, ждать больше нечего и выходим сразу.
    """
    deadline = clock() + timeout_s
    grace_deadline = clock() + grace_s
    handled: list[tuple[str, int]] = []
    while True:
        pending = gated_runs(repo, head_sha, branch, token, request=request)
        if not pending:
            if handled or clock() >= grace_deadline:
                return handled
        for run in pending:
            run_id = int(run["id"])
            base = f"{GITHUB_API}/repos/{repo}/actions/runs/{run_id}"
            try:
                request("POST", f"{base}/approve", token)
                handled.append(("approved", run_id))
                continue
            except GateError as approve_exc:
                try:
                    request("DELETE", base, token)
                except GateError as del_exc:
                    raise GateError(
                        f"gated run {run_id} не снят: approve={approve_exc}; "
                        f"delete={del_exc}") from del_exc
                handled.append(("deleted", run_id))
        if clock() >= deadline:
            raise GateError(
                f"таймаут {timeout_s:.0f}s: gated run'ы на {head_sha} не исчезли")
        sleep(poll_s)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="clear_gated_runs.py", description=__doc__)
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    ap.add_argument("--branch", required=True)
    ap.add_argument("--head-sha", required=True)
    ap.add_argument("--timeout-min", type=float, default=5.0)
    ap.add_argument("--poll-s", type=float, default=10.0)
    # Сколько ждать ПОЯВЛЕНИЯ gated run'а, прежде чем поверить, что его нет.
    ap.add_argument("--grace-s", type=float, default=90.0)
    args = ap.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("[GATED-FAIL] missing GITHUB_TOKEN", file=sys.stderr)
        return 3
    try:
        handled = clear_gated_runs(
            args.repo, args.head_sha, args.branch, token,
            timeout_s=args.timeout_min * 60, poll_s=args.poll_s,
            grace_s=args.grace_s)
    except GateError as exc:
        print(f"[GATED-FAIL] {exc}", file=sys.stderr)
        return 1
    if handled:
        for action, run_id in handled:
            print(f"gated run {run_id}: {action}")
    else:
        print(f"gated runs on {args.head_sha}: none "
              f"(после {args.grace_s:.0f}s ожидания)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
