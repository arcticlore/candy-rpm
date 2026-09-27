#!/usr/bin/env python3
"""Unit tests for the update.yml fail-closed submit guard (force_resubmit plan).

Standard library only (unittest + importlib.util); no network, no subprocess,
no COPR mutation. The hyphenated module name is loaded safely by path.
Run remotely via:  python3 -m unittest -v tests/test_submit_guard.py
"""

import importlib.util
import io
import os
import pathlib
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "bin" / "coprase-status.py"

_spec = importlib.util.spec_from_file_location("coprase_status", str(MODULE_PATH))
cs = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader, "coprase-status.py должен быть загружаем"
_spec.loader.exec_module(cs)

# Fixture surface: enabled by default, one explicitly disabled package.
PKGS = [
    {"name": "diagon", "eco": "c-cmake"},
    {"name": "duf", "eco": "go"},
    {"name": "hexyl", "eco": "cargo", "enabled": True},
    {"name": "offpkg", "eco": "script", "enabled": False},
]

ALL_ENABLED = {"diagon", "duf", "hexyl"}


class TestFullRebuildFailClosed(unittest.TestCase):
    """full_rebuild=true must abort before any SRPM build or submit."""

    def test_full_rebuild_aborts_with_allowlist(self):
        with self.assertRaises(SystemExit):
            cs.compute_plan(True, False, "diagon", PKGS)

    def test_full_rebuild_aborts_even_with_force_and_allowlist(self):
        with self.assertRaises(SystemExit):
            cs.compute_plan(True, True, "diagon", PKGS)

    def test_full_rebuild_aborts_without_allowlist(self):
        with self.assertRaises(SystemExit):
            cs.compute_plan(True, False, "", PKGS)


class TestForceRequiresStrictBoundedAllowlist(unittest.TestCase):
    """force_resubmit=true: empty/invalid allowlist must fail (fail-closed)."""

    def test_force_with_empty_allowlist_fails(self):
        for raw in ("", "   "):
            with self.subTest(raw=raw), self.assertRaises(SystemExit):
                cs.compute_plan(False, True, raw, PKGS)

    def test_force_with_malformed_allowlist_fails(self):
        for raw in ("bad name", "-diagon", ",diagon", "diagon,,duf",
                    "diagon,diagon", "diagon,"):
            with self.subTest(raw=raw), self.assertRaises(SystemExit):
                cs.compute_plan(False, True, raw, PKGS)

    def test_force_with_unknown_package_fails(self):
        with self.assertRaises(SystemExit):
            cs.compute_plan(False, True, "no-such-package", PKGS)

    def test_force_with_disabled_package_fails(self):
        with self.assertRaises(SystemExit):
            cs.compute_plan(False, True, "offpkg", PKGS)


class TestForceBoundedExactScope(unittest.TestCase):
    """TO_SUBMIT is exactly the effective allowlist; force never widens it."""

    def test_force_single_package_is_exactly_that_package(self):
        plan = cs.compute_plan(False, True, "diagon", PKGS)
        self.assertEqual(plan, {"force": 1, "mode": "BOUNDED",
                                "to_submit": ["diagon"]})

    def test_force_cannot_widen_beyond_allowlist(self):
        plan = cs.compute_plan(False, True, "hexyl,diagon", PKGS)
        self.assertEqual(set(plan["to_submit"]), {"diagon", "hexyl"})
        # соседний enabled-пакет не подтягивается и весь набор не «расширяется»
        self.assertNotIn("duf", plan["to_submit"])
        self.assertFalse(set(plan["to_submit"]) - {"diagon", "hexyl"})

    def test_force_single_name_never_returns_all_enabled(self):
        plan = cs.compute_plan(False, True, "duf", PKGS)
        self.assertEqual(len(plan["to_submit"]), 1)
        self.assertNotEqual(set(plan["to_submit"]), ALL_ENABLED)


class TestNormalRunUnchanged(unittest.TestCase):
    """force_resubmit=false must keep the current dedup behavior."""

    def test_plain_run_keeps_check_based_deferral(self):
        plan = cs.compute_plan(False, False, "", PKGS)
        self.assertEqual(plan, {"force": 0, "mode": "ALL", "to_submit": []})

    def test_bounded_run_without_force_is_not_forced(self):
        plan = cs.compute_plan(False, False, "diagon", PKGS)
        self.assertEqual(plan["force"], 0)
        self.assertEqual(plan["mode"], "BOUNDED")
        # TO_SUBMIT остаётся за check-логикой workflow — дедуп не тронут
        self.assertEqual(plan["to_submit"], [])


class TestCmdPlanMachineOutput(unittest.TestCase):
    """update.yml читает ровно FORCE=/MODE=/TO_SUBMIT= из stdout guard-шага."""

    def _run(self, env):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env, clear=False):
            with redirect_stdout(out), redirect_stderr(err):
                cs.cmd_plan()
        return out.getvalue()

    def test_force_run_output(self):
        out = self._run({"PLAN_FULL_REBUILD": "false",
                         "PLAN_FORCE_RESUBMIT": "true",
                         "CANDY_PACKAGE_ALLOWLIST": "diagon"})
        lines = out.splitlines()
        self.assertIn("FORCE=1", lines)
        self.assertIn("MODE=BOUNDED", lines)
        self.assertIn("TO_SUBMIT=diagon", lines)
        self.assertEqual(len(lines), 3)

    def test_normal_run_output(self):
        out = self._run({"PLAN_FULL_REBUILD": "false",
                         "PLAN_FORCE_RESUBMIT": "false",
                         "CANDY_PACKAGE_ALLOWLIST": ""})
        lines = out.splitlines()
        self.assertIn("FORCE=0", lines)
        self.assertIn("MODE=ALL", lines)
        self.assertIn("TO_SUBMIT=", lines)

    def test_abort_is_nonzero_and_on_stderr_only(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"PLAN_FULL_REBUILD": "true",
                                          "PLAN_FORCE_RESUBMIT": "false",
                                          "CANDY_PACKAGE_ALLOWLIST": ""}):
            with redirect_stdout(out), redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    cs.cmd_plan()
        self.assertTrue(ctx.exception.code)
        self.assertNotEqual(ctx.exception.code, 0)
        self.assertIn("[GUARD-ABORT]", str(ctx.exception))
        self.assertEqual(out.getvalue(), "")  # машинных строк нет


class TestUpdateWorkflowStructure(unittest.TestCase):
    """Структура update.yml под политику guard-шага."""

    TEXT = (ROOT / ".github" / "workflows" / "update.yml").read_text(
        encoding="utf-8")

    def test_force_resubmit_input_exists_defaults_false(self):
        idx = self.TEXT.index("force_resubmit:")
        block = self.TEXT[idx:idx + 400]
        self.assertIn("type: boolean", block)
        self.assertIn("default: false", block)

    def test_guard_runs_before_srpm_and_submit(self):
        guard = self.TEXT.index("coprase-status.py plan")
        srpm = self.TEXT.index("Build SRPMs")
        submit = self.TEXT.index("Submit to COPR")
        self.assertLess(guard, srpm)
        self.assertLess(srpm, submit)

    def test_full_rebuild_only_reaches_the_guard_env(self):
        # inputs.full_rebuild используется ровно один раз — в guard-шаге;
        # SRPM/builddep/submit условия больше от него не зависят.
        self.assertEqual(self.TEXT.count("inputs.full_rebuild"), 1)
        self.assertNotIn("inputs.full_rebuild ==", self.TEXT)
        self.assertIn('PLAN_FULL_REBUILD="${{ inputs.full_rebuild }}"', self.TEXT)

    def test_force_flag_comes_from_plan_outputs(self):
        self.assertIn("${{ steps.plan.outputs.force == '1' && '--force' || '' }}",
                      self.TEXT)
        # форс-ветки SRPM/builddep используют ровно effective allowlist из plan
        self.assertEqual(self.TEXT.count('TO_SUBMIT="${{ steps.plan.outputs.to_submit }}"'), 2)

    def test_manual_only_no_schedule(self):
        head = self.TEXT.split("\n", 20)
        self.assertFalse(re.search(r"^\s*schedule:", "\n".join(head), re.M))


if __name__ == "__main__":
    unittest.main()
