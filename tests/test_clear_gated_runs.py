#!/usr/bin/env python3
"""clear_gated_runs.py — контракт снятия gated run'а на bot-PR (офлайн).

GitHub заводит на PR, созданный GITHUB_TOKEN, пустой `pull_request` run и
гасит его как action_required. Check'ов он не даёт (их приносит явный
dispatch), но merge box остаётся BLOCKED и auto-merge не наступает. Тесты
фиксируют: выборка строго по этому PR, approve с фолбэком на DELETE,
fail-closed на любом отказе и таймауте, и что шаг реально включён в волну.
"""
from __future__ import annotations

import importlib.util
import itertools
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "clear_gated_runs", ROOT / "bin" / "clear_gated_runs.py")
cg = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(cg)

SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
BRANCH = "bot/state-sync-44742332105-1"
REPO = "arcticlore/candy-rpm"


def run_payload(**over) -> dict:
    data = {
        "id": 44738315930,
        "event": "pull_request",
        "status": "completed",
        "conclusion": "action_required",
        "head_sha": SHA,
        "head_branch": BRANCH,
    }
    data.update(over)
    return data


class FakeAPI:
    """Крошечный фейковый GitHub: список run'ов + политика DELETE/approve."""

    def __init__(self, runs, *, allow_delete=True, allow_approve=True,
                 resurrect=False):
        self.runs = [dict(r) for r in runs]
        self.allow_delete = allow_delete
        self.allow_approve = allow_approve
        self.resurrect = resurrect
        self.calls: list[tuple[str, str]] = []

    def __call__(self, method, url, token, timeout=60):
        self.calls.append((method, url))
        if token != "tok":
            raise cg.GateError("HTTP 401")
        if method == "GET" and "/actions/runs?head_sha=" in url:
            return 200, {"workflow_runs": [dict(r) for r in self.runs]}
        if method == "DELETE" and "/actions/runs/" in url:
            if not self.allow_delete:
                raise cg.GateError("HTTP 403 for DELETE")
            rid = int(url.rsplit("/", 1)[1])
            self.runs = [r for r in self.runs if r["id"] != rid]
            return 204, None
        if method == "POST" and url.endswith("/approve"):
            if not self.allow_approve:
                raise cg.GateError("HTTP 403 for approve")
            rid = int(url.rsplit("/", 2)[1])
            for r in self.runs:
                if r["id"] == rid:
                    r["conclusion"] = None
                    r["status"] = "queued"
            return 200, {}
        raise cg.GateError(f"unexpected {method} {url}")


class SelectionTests(unittest.TestCase):
    def test_only_the_gated_run_of_this_pr_is_selected(self) -> None:
        api = FakeAPI([
            run_payload(),
            run_payload(id=2, event="workflow_dispatch", conclusion="success"),
            run_payload(id=3, conclusion="success"),
            run_payload(id=4, head_branch="bot/state-sync-other"),
            run_payload(id=5, event="push"),
        ])
        found = cg.gated_runs(REPO, SHA, BRANCH, "tok", request=api)
        self.assertEqual([r["id"] for r in found], [44738315930])

    def test_foreign_head_sha_is_fatal(self) -> None:
        api = FakeAPI([run_payload(head_sha="0" * 40)])
        with self.assertRaises(cg.GateError):
            cg.gated_runs(REPO, SHA, BRANCH, "tok", request=api)

    def test_branch_must_be_a_bot_state_sync_branch(self) -> None:
        api = FakeAPI([run_payload()])
        for bad in ("master", "fix/x", "bot/other", "", "../bot/state-sync-1"):
            with self.assertRaises(cg.GateError):
                cg.gated_runs(REPO, SHA, bad, "tok", request=api)

    def test_short_sha_and_bad_repo_are_refused(self) -> None:
        api = FakeAPI([run_payload()])
        with self.assertRaises(cg.GateError):
            cg.gated_runs(REPO, "abc", BRANCH, "tok", request=api)
        with self.assertRaises(cg.GateError):
            cg.gated_runs("not-a-repo", SHA, BRANCH, "tok", request=api)

    def test_malformed_payloads_are_fatal(self) -> None:
        with self.assertRaises(cg.GateError):
            cg.gated_runs(REPO, SHA, BRANCH, "tok",
                          request=lambda *a, **k: (200, {"workflow_runs": "nope"}))
        with self.assertRaises(cg.GateError):
            cg.gated_runs(REPO, SHA, BRANCH, "tok",
                          request=lambda *a, **k: (200, ["not", "a", "dict"]))
        with self.assertRaises(cg.GateError):
            cg.gated_runs(REPO, SHA, BRANCH, "tok",
                          request=lambda *a, **k: (200, {"workflow_runs": [
                              {"event": "pull_request", "head_sha": SHA,
                               "head_branch": BRANCH,
                               "conclusion": "action_required", "id": "x"}]}))


class ClearTests(unittest.TestCase):
    def test_approve_is_the_primary_path(self) -> None:
        # DELETE уносит контексты вместе с прогоном: candy-opensuse #89 остался
        # BLOCKED с пустым statusCheckRollup. Approve даёт прогону отчитаться.
        api = FakeAPI([run_payload()])
        handled = cg.clear_gated_runs(REPO, SHA, BRANCH, "tok", request=api,
                                      sleep=lambda _s: None)
        self.assertEqual(handled, [("approved", 44738315930)])
        self.assertEqual(cg.gated_runs(REPO, SHA, BRANCH, "tok", request=api), [])
        self.assertTrue(any(m == "POST" and u.endswith("/approve") for m, u in api.calls))
        self.assertFalse(any(m == "DELETE" for m, _u in api.calls))

    def test_delete_is_the_fallback(self) -> None:
        api = FakeAPI([run_payload()], allow_approve=False)
        handled = cg.clear_gated_runs(REPO, SHA, BRANCH, "tok", request=api,
                                      sleep=lambda _s: None)
        self.assertEqual(handled, [("deleted", 44738315930)])
        self.assertEqual(cg.gated_runs(REPO, SHA, BRANCH, "tok", request=api), [])

    def test_fail_closed_when_both_paths_are_denied(self) -> None:
        api = FakeAPI([run_payload()], allow_delete=False, allow_approve=False)
        with self.assertRaises(cg.GateError) as ctx:
            cg.clear_gated_runs(REPO, SHA, BRANCH, "tok", request=api,
                                sleep=lambda _s: None)
        self.assertIn("не снят", str(ctx.exception))

    def test_noop_when_nothing_is_gated(self) -> None:
        # grace_s=0: проверяем именно «гасить нечего», без окна ожидания
        # появления gated run'а (его смысл проверяет AppearsLateTests).
        api = FakeAPI([run_payload(conclusion="success")])
        self.assertEqual(
            cg.clear_gated_runs(REPO, SHA, BRANCH, "tok", request=api,
                                grace_s=0, sleep=lambda _s: None), [])
        self.assertFalse(any(m in ("DELETE", "POST") for m, _u in api.calls))

    def test_timeout_is_fail_closed(self) -> None:
        api = FakeAPI([run_payload()], allow_delete=False)

        def readd(_s: float) -> None:
            api.runs = [run_payload()]

        ticks = iter([0.0, 1.0, 400.0, 401.0, 402.0])
        with self.assertRaises(cg.GateError) as ctx:
            cg.clear_gated_runs(REPO, SHA, BRANCH, "tok", request=api,
                                timeout_s=300.0, sleep=readd,
                                clock=lambda: next(ticks))
        self.assertIn("таймаут", str(ctx.exception))

    def test_cli_without_token_is_not_silent(self) -> None:
        import os
        saved = os.environ.pop("GITHUB_TOKEN", None)
        try:
            rc = cg.main(["--repo", REPO, "--branch", BRANCH, "--head-sha", SHA])
        finally:
            if saved is not None:
                os.environ["GITHUB_TOKEN"] = saved
        self.assertEqual(rc, 3)


class WorkflowWiringTests(unittest.TestCase):
    TEXT = (ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8")

    def test_update_yml_calls_the_gate(self) -> None:
        self.assertIn("bin/clear_gated_runs.py", self.TEXT)

    def test_gate_runs_after_dispatch_and_before_auto_merge(self) -> None:
        dispatch = self.TEXT.index("validate.yml/dispatches")
        gate = self.TEXT.index("bin/clear_gated_runs.py")
        auto = self.TEXT.index("enablePullRequestAutoMerge")
        self.assertLess(dispatch, gate)
        self.assertLess(gate, auto)

    def test_gate_is_bound_to_exact_branch_and_head(self) -> None:
        idx = self.TEXT.index("bin/clear_gated_runs.py")
        window = self.TEXT[idx:idx + 300]
        self.assertIn("--branch", window)
        self.assertIn("--head-sha", window)

    def test_gate_failure_is_fatal(self) -> None:
        idx = self.TEXT.index("bin/clear_gated_runs.py")
        window = self.TEXT[idx - 200:idx + 400]
        self.assertNotIn("|| true", window)
        self.assertIn("exit 1", window)


if __name__ == "__main__":
    unittest.main()


class AppearsLateTests(unittest.TestCase):
    """Пустой первый опрос — ещё не повод считать, что гасить нечего.

    GitHub заводит gated `pull_request` run асинхронно. В run 45820026991
    скрипт успел спросить раньше, напечатал «none», волна включила
    auto-merge — а run появился следом и навсегда оставил PR #69 в
    BLOCKED. observe-merge честно прождал 90 минут и покрасил прогон.
    """

    def test_run_that_appears_after_the_first_poll_is_still_cleared(self):
        api = FakeAPI([])
        polls = {"n": 0}
        real_call = api.__call__

        def spy(method, url, token, timeout=60):
            if method == "GET" and "/actions/runs?head_sha=" in url:
                polls["n"] += 1
                if polls["n"] == 3:          # GitHub «догнал» на третьем опросе
                    api.runs = [run_payload()]
            return real_call(method, url, token, timeout)

        handled = cg.clear_gated_runs(REPO, SHA, BRANCH, "tok", request=spy,
                                      clock=itertools.count(0.0, 5.0).__next__,
                                      sleep=lambda _s: None)
        self.assertEqual([a for a, _ in handled], ["approved"])
        self.assertEqual(cg.gated_runs(REPO, SHA, BRANCH, "tok", request=api), [])

    def test_grace_window_is_bounded_when_nothing_ever_appears(self):
        api = FakeAPI([])
        ticks = itertools.count(0.0, 50.0)     # 0, 50, 100, ... — окно 90s истечёт
        handled = cg.clear_gated_runs(REPO, SHA, BRANCH, "tok", request=api,
                                      clock=lambda: next(ticks),
                                      sleep=lambda _s: None)
        self.assertEqual(handled, [])
        self.assertFalse(any(m in ("DELETE", "POST") for m, _u in api.calls))
