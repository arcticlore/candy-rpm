#!/usr/bin/env python3
"""update-plan.py + scheduled update.yml policy regressions (stdlib only).

Covers the bounded-autonomy contract for the daily scheduled COPR update:
  1. a scheduled workflow that submits to COPR is only update.yml;
  2. the scheduled path cannot enable full_rebuild / force;
  3. unchanged and same-version targets never enter the plan;
  4. max-wave is respected;
  5. missing/broken repodata is fail-closed, never an empty "successful" plan;
  6. an active build is never resubmitted;
  7. state sync accepts only exact all-chroots (8/8) published targets;
  8. a publish/publication failure is red (not swallowed);
  9. an identical/duplicate run creates no new PR;
 10. the scheduled workflow never writes to master.

Run remotely via:  python3 -m unittest -v tests/test_update_plan.py
"""

import importlib.util
import json
import pathlib
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "bin" / "update-plan.py"
UPDATE_YML = ROOT / ".github" / "workflows" / "update.yml"
WORKFLOWS = ROOT / ".github" / "workflows"

_spec = importlib.util.spec_from_file_location("update_plan", str(MODULE_PATH))
up = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader, "update-plan.py должен быть загружаем"
_spec.loader.exec_module(up)

CHROOTS = up.EXPECTED_CHROOTS
PKGS = [
    {"name": "alpha", "eco": "cargo"},
    {"name": "beta", "eco": "go"},
    {"name": "gamma", "eco": "c-cmake"},
    {"name": "delta", "eco": "script"},
    {"name": "epsilon", "eco": "cargo"},
    {"name": "zeta", "eco": "go"},
    {"name": "offpkg", "eco": "script", "enabled": False},
]


def published_all(names, version):
    """Every chroot publishes `names` at `version`."""
    return {cr: {n: {version} for n in names} for cr in CHROOTS}


class TestScheduleOnlyUpdateYml(unittest.TestCase):
    """Regression 1: only update.yml may be a scheduled COPR-submitting workflow."""

    def _text(self, p):
        return p.read_text(encoding="utf-8")

    def test_only_update_yml_schedules_copr_submit(self):
        offenders = []
        for p in sorted(WORKFLOWS.glob("*.yml")):
            text = self._text(p)
            submits = ("copr-cli build" in text
                       or "coprase-status.py submit" in text)
            scheduled = "schedule:" in text
            if submits and scheduled and p.name != "update.yml":
                offenders.append(p.name)
        self.assertEqual(offenders, [])

    def test_update_yml_is_scheduled_and_dispatchable(self):
        text = self._text(UPDATE_YML)
        self.assertIn("schedule:", text)
        self.assertIn("workflow_dispatch:", text)


class TestNoFullRebuildNoForceOnSchedule(unittest.TestCase):
    """Regression 2: scheduled path cannot enable full_rebuild / force."""

    def test_no_full_rebuild_input(self):
        text = UPDATE_YML.read_text(encoding="utf-8")
        self.assertNotIn("full_rebuild", text)

    def test_no_force_flag_string(self):
        text = UPDATE_YML.read_text(encoding="utf-8")
        self.assertNotIn("--force", text)

    def test_plan_only_dispatch_is_mandatory(self):
        text = UPDATE_YML.read_text(encoding="utf-8")
        self.assertIn("plan_only", text)
        self.assertIn("default: true", text)


class TestChangedOnlyPlan(unittest.TestCase):
    """Regression 3: unchanged / same-version targets never enter the plan."""

    def test_unchanged_excluded(self):
        upstream = {"alpha": "1.0.0", "beta": "2.0.0"}
        published = published_all(["alpha", "beta"], "1.0.0")
        for cr in CHROOTS:
            published[cr]["beta"] = {"2.0.0"}  # beta already published 8/8
        res = up.compute_changed_plan(
            {"alpha", "beta"}, ["alpha", "beta"], upstream, published,
            set(), CHROOTS, 5)
        self.assertEqual(res["plan"], [])
        self.assertEqual(set(res["unchanged"]), {"alpha", "beta"})

    def test_same_version_release_bump_excluded(self):
        upstream = {"alpha": "1.0.0-2"}  # release bump, base already published
        published = published_all(["alpha"], "1.0.0")
        res = up.compute_changed_plan(
            {"alpha"}, ["alpha"], upstream, published, set(), CHROOTS, 5)
        self.assertEqual(res["plan"], [])

    def test_triggered_repodata_date_churn_is_same_commit(self):
        upstream = {"alpha": "20260101.abcdef1"}
        published = published_all(["alpha"], "20251231.abcdef1")
        res = up.compute_changed_plan(
            {"alpha"}, ["alpha"], upstream, published, set(), CHROOTS, 5)
        self.assertEqual(res["plan"], [])

    def test_new_version_present_when_missing_from_one_chroot(self):
        upstream = {"alpha": "1.0.1"}
        published = published_all(["alpha"], "1.0.0")
        published[CHROOTS[3]]["alpha"] = {"1.0.0"}  # one chroot missing 1.0.1
        res = up.compute_changed_plan(
            {"alpha"}, ["alpha"], upstream, published, set(), CHROOTS, 5)
        self.assertEqual(res["plan"], ["alpha"])

    def test_upstream_unknown_deferred_not_submitted(self):
        upstream = {"alpha": "", "beta": "2.0.1"}
        published = published_all(["alpha", "beta"], "1.0.0")
        res = up.compute_changed_plan(
            {"alpha", "beta"}, ["alpha", "beta"], upstream, published,
            set(), CHROOTS, 5)
        self.assertEqual(res["plan"], ["beta"])
        self.assertEqual(res["upstream_failed"], ["alpha"])


class TestMaxWave(unittest.TestCase):
    """Regression 4: max-wave is respected, overflow deferred."""

    def test_max_wave_caps_plan(self):
        names = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]
        upstream = {n: "9.9.9" for n in names}
        published = published_all(names, "1.0.0")
        res = up.compute_changed_plan(
            set(names), names, upstream, published, set(), CHROOTS, 5)
        self.assertEqual(len(res["plan"]), 5)
        self.assertEqual(res["plan"], names[:5])
        self.assertEqual(res["overflow"], ["zeta"])

    def test_resolve_max_wave_bounds(self):
        self.assertEqual(up.resolve_max_wave(""), 5)
        self.assertEqual(up.resolve_max_wave("3"), 3)
        for bad in ("0", "6", "x", "-1"):
            with self.assertRaises(up.PlanError):
                up.resolve_max_wave(bad)


class TestFailClosedRepodata(unittest.TestCase):
    """Regression 5: uncertainty is never an empty successful plan."""

    def test_missing_repodata_is_not_published(self):
        published = published_all(["alpha"], "1.0.0")
        del published[CHROOTS[0]]["alpha"]
        self.assertFalse(
            up.is_fully_published("alpha", "1.0.1", published, CHROOTS))

    def test_plan_command_aborts_on_repodata_error(self):
        with mock.patch.object(up, "fetch_project_chroots",
                               return_value=CHROOTS), \
             mock.patch.object(up, "fetch_upstream",
                               return_value={"alpha": "1.0.1"}), \
             mock.patch.object(up, "fetch_all_published",
                               side_effect=up.PlanError("repodata unavailable")), \
             mock.patch.object(up, "fetch_active_builds", return_value=set()), \
             mock.patch.object(up, "load_pkgs", return_value=PKGS), \
             mock.patch.object(up, "load_state", return_value={}):
            rc = up.main(["update-plan.py", "plan"])
        self.assertNotEqual(rc, 0)

    def test_plan_command_aborts_on_upstream_error(self):
        with mock.patch.object(up, "fetch_upstream",
                               side_effect=up.PlanError("upstream empty")), \
             mock.patch.object(up, "load_pkgs", return_value=PKGS), \
             mock.patch.object(up, "load_state", return_value={}):
            rc = up.main(["update-plan.py", "plan"])
        self.assertNotEqual(rc, 0)


class TestActiveBuildNotResubmitted(unittest.TestCase):
    """Regression 6: an active build is resume/wait, never a new submit."""

    def test_active_excluded_from_plan(self):
        upstream = {"alpha": "1.0.1", "beta": "2.0.1"}
        published = published_all(["alpha", "beta"], "1.0.0")
        res = up.compute_changed_plan(
            {"alpha", "beta"}, ["alpha", "beta"], upstream, published,
            {"alpha"}, CHROOTS, 5)
        self.assertEqual(res["plan"], ["beta"])
        self.assertEqual(res["active"], ["alpha"])


class TestExactAllChrootsGate(unittest.TestCase):
    """Regression 7: state sync accepts only exact 8/8 published targets."""

    def test_to_revert_only_unpublished(self):
        published = published_all(["alpha", "beta"], "1.0.0")
        published[CHROOTS[2]]["beta"] = {"0.9.0"}  # beta not 8/8 for 1.0.0
        state = {"alpha": {"ver": "1.0.0"}, "beta": {"ver": "1.0.0"}}
        revert = up.to_revert(state, published, {"alpha", "beta"}, CHROOTS)
        self.assertEqual(revert, ["beta"])

    def test_fully_published_not_reverted(self):
        published = published_all(["alpha"], "1.0.0")
        state = {"alpha": {"ver": "1.0.0"}}
        self.assertEqual(up.to_revert(state, published, {"alpha"}, CHROOTS), [])


class TestPublicationFailureRed(unittest.TestCase):
    """Regression 8: publish failure must be red (fail-closed, not swallowed)."""

    def test_gate_error_nonzero(self):
        with mock.patch.object(up, "fetch_project_chroots",
                               return_value=CHROOTS), \
             mock.patch.object(up, "fetch_all_published",
                               side_effect=up.PlanError("repodata down")), \
             mock.patch.object(up, "load_pkgs", return_value=PKGS), \
             mock.patch.object(up, "load_state", return_value={}):
            rc = up.main(["update-plan.py", "gate-published"])
        self.assertEqual(rc, 3)

    def test_workflow_gate_is_fail_closed(self):
        text = UPDATE_YML.read_text(encoding="utf-8")
        self.assertIn("update-plan.py gate-published", text)
        self.assertIn("update-plan.py revert-unpublished", text)
        # the gate step must not be neutralised
        for line in text.splitlines():
            if "gate-published" in line or "revert-unpublished" in line:
                self.assertNotIn("|| true", line)
                self.assertNotIn("continue-on-error", line)


class TestNoDuplicatePr(unittest.TestCase):
    """Regression 9: an identical/duplicate run creates no new PR."""

    def test_no_pr_when_existing(self):
        self.assertFalse(up.should_open_pr([{"number": 1}], True))

    def test_no_pr_when_no_diff(self):
        self.assertFalse(up.should_open_pr([], False))

    def test_pr_when_single_and_diff(self):
        self.assertTrue(up.should_open_pr([], True))


class TestNoDirectMasterWrite(unittest.TestCase):
    """Regression 10: the scheduled workflow never writes to master."""

    def test_no_master_refs(self):
        text = UPDATE_YML.read_text(encoding="utf-8")
        self.assertNotIn("HEAD:master", text)
        self.assertNotIn("refs/heads/master", text)

    def test_push_targets_only_bot_or_state(self):
        for line in UPDATE_YML.read_text(encoding="utf-8").splitlines():
            if "git push" in line:
                self.assertTrue("bot/" in line or "state/" in line, line)

    def test_concurrency_no_cancel(self):
        text = UPDATE_YML.read_text(encoding="utf-8")
        self.assertIn("cancel-in-progress: false", text)


if __name__ == "__main__":
    unittest.main()
