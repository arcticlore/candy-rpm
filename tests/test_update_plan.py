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
import io
import json
import os
import pathlib
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
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


class TestImmutablePlanEntries(unittest.TestCase):
    """Exact `name@target` is preserved and reused by the workflow."""

    def test_parse_and_format_round_trip(self):
        entries = up.parse_plan_entries("alpha@1.0.1 beta@20260101.abcdef1")
        self.assertEqual(entries, [("alpha", "1.0.1"), ("beta", "20260101.abcdef1")])
        self.assertEqual(up.format_entry("alpha", "1.0.1"), "alpha@1.0.1")

    def test_malformed_entries_fail_closed(self):
        for bad in ("alpha", "alpha@", "@1.0.0", "alpha@1.0 1.0", "a b",
                    "alpha@1.0 alpha@2.0", "bad name@1.0"):
            with self.subTest(bad=bad), self.assertRaises(up.PlanError):
                up.parse_plan_entries(bad)

    def test_plan_carries_exact_targets(self):
        upstream = {"alpha": "1.0.1", "beta": "2.0.1"}
        published = published_all(["alpha", "beta"], "1.0.0")
        res = up.compute_changed_plan(
            {"alpha", "beta"}, ["alpha", "beta"], upstream, published,
            set(), CHROOTS, 5, state={})
        self.assertEqual(res["build_entries"], ["alpha@1.0.1", "beta@2.0.1"])
        self.assertEqual(res["targets"], {"alpha": "1.0.1", "beta": "2.0.1"})

    def test_plan_command_emits_name_at_target(self):
        published = published_all(["alpha"], "1.0.0")
        out = io.StringIO()
        with mock.patch.object(up, "fetch_upstream",
                               return_value={"alpha": "1.0.1"}), \
             mock.patch.object(up, "fetch_all_published", return_value=published), \
             mock.patch.object(up, "fetch_active_builds", return_value=set()), \
             mock.patch.object(up, "load_pkgs", return_value=PKGS), \
             mock.patch.object(up, "load_state", return_value={}):
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                rc = up.cmd_plan()
        self.assertEqual(rc, 0)
        text = out.getvalue()
        self.assertIn("BUILD_ENTRIES=alpha@1.0.1", text)
        self.assertIn("MODE=build", text)

    def test_workflow_builds_from_exact_planned_target(self):
        text = UPDATE_YML.read_text(encoding="utf-8")
        # SRPM строится по target из плана, а НЕ по state.json
        self.assertIn('name="${entry%%@*}"', text)
        self.assertIn('target="${entry##*@}"', text)
        self.assertIn('bin/make-srpm.sh "$name" "$target"', text)
        self.assertNotIn('jq -r --arg n "$name" \'.[$n].ver', text)
        # unbounded version refresh удалён
        self.assertNotIn("coprase-status.py versions", text)


class TestMaterializeReproducibility(unittest.TestCase):
    """Re-fetching upstream must never silently move a planned target."""

    def _run(self, entries, allowed, fresh, state):
        td = tempfile.mkdtemp()
        sp = os.path.join(td, "state.json")
        pathlib.Path(sp).write_text(json.dumps(state))
        env = {up.PLAN_ENTRIES_ENV: entries, up.ALLOWLIST_ENV: allowed,
               up.STATE_PATH_ENV: sp}
        with mock.patch.dict(os.environ, env, clear=False), \
             mock.patch.object(up, "fetch_upstream", return_value=fresh), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = up.cmd_materialize()
        return rc, json.loads(pathlib.Path(sp).read_text())

    def test_reproducible_target_is_pinned(self):
        rc, state = self._run("alpha@1.0.1", "alpha", {"alpha": "1.0.1"},
                              {"alpha": {"ver": "1.0.0"}})
        self.assertEqual(rc, 0)
        self.assertEqual(state["alpha"]["ver"], "1.0.1")

    def test_upstream_moved_between_plan_and_build_aborts(self):
        rc, state = self._run("alpha@1.0.1", "alpha", {"alpha": "1.0.2"},
                              {"alpha": {"ver": "1.0.0"}})
        self.assertEqual(rc, 3)
        self.assertEqual(state["alpha"]["ver"], "1.0.0")

    def test_empty_upstream_aborts(self):
        rc, _ = self._run("alpha@1.0.1", "alpha", {"alpha": ""},
                          {"alpha": {"ver": "1.0.0"}})
        self.assertEqual(rc, 3)

    def test_locked_package_in_plan_aborts(self):
        rc, state = self._run("alpha@1.0.1", "alpha", {"alpha": "1.0.1"},
                              {"alpha": {"ver": "1.0.0", "locked": True}})
        self.assertEqual(rc, 3)
        self.assertEqual(state["alpha"]["ver"], "1.0.0")

    def test_allowlist_mismatch_aborts(self):
        rc, _ = self._run("alpha@1.0.1", "beta", {"alpha": "1.0.1"},
                          {"alpha": {"ver": "1.0.0"}})
        self.assertEqual(rc, 3)

    def test_same_commit_date_churn_is_reproducible(self):
        rc, state = self._run("alpha@20260102.abcdef1", "alpha",
                              {"alpha": "20260101.abcdef1"},
                              {"alpha": {"ver": "20251231.abcdef1"}})
        self.assertEqual(rc, 0)


class TestLockedPackages(unittest.TestCase):
    """state.<name>.locked excludes the package from the autonomous plan."""

    def test_locked_excluded_from_plan(self):
        upstream = {"alpha": "1.0.1", "lockedpkg": "9.9.9"}
        published = published_all(["alpha", "lockedpkg"], "1.0.0")
        res = up.compute_changed_plan(
            {"alpha", "lockedpkg"}, ["alpha", "lockedpkg"], upstream,
            published, set(), CHROOTS, 5, locked={"lockedpkg"},
            state={"lockedpkg": {"ver": "1.0.0", "locked": True}})
        self.assertEqual(res["plan"], ["alpha"])
        self.assertEqual(res["locked"], ["lockedpkg"])
        self.assertNotIn("lockedpkg", res["targets"])

    def test_locked_names_helper(self):
        self.assertEqual(
            up.locked_names({"a": {"locked": True}, "b": {"ver": "1"},
                             "c": {"locked": False}}),
            {"a"})

    def test_real_state_oh_my_zsh_is_locked(self):
        state = json.loads((ROOT / "state" / "state.json").read_text())
        self.assertIn("oh-my-zsh", up.locked_names(state))

    def test_build_plan_excludes_locked(self):
        state = {"alpha": {"ver": "1.0.0"}, "beta": {"ver": "1.0.0", "locked": True}}
        upstream = {"alpha": "1.0.1", "beta": "2.0.1"}
        published = published_all(["alpha", "beta"], "1.0.0")
        res = up.build_plan(5, "", pkgs=PKGS, state=state, upstream=upstream,
                            published=published, active=set())
        self.assertIn("alpha", res["plan"])
        self.assertNotIn("beta", res["plan"])
        self.assertIn("beta", res["locked"])

    def test_allowlist_referencing_locked_fails(self):
        state = {"alpha": {"ver": "1.0.0", "locked": True}}
        with self.assertRaises(up.PlanError):
            up.build_plan(5, "alpha", pkgs=PKGS, state=state,
                          upstream={"alpha": "1.0.1"},
                          published=published_all(["alpha"], "1.0.0"),
                          active=set())


class TestStateOnlyReconcile(unittest.TestCase):
    """Published 8/8 but stale state → state-only, never a rebuild."""

    def test_published_stale_state_is_state_only(self):
        upstream = {"alpha": "1.0.1"}
        published = published_all(["alpha"], "1.0.1")  # already published
        state = {"alpha": {"ver": "1.0.0"}}            # stale
        res = up.compute_changed_plan(
            {"alpha"}, ["alpha"], upstream, published, set(), CHROOTS, 5,
            state=state)
        self.assertEqual(res["plan"], [])
        self.assertEqual(res["state_only"], ["alpha"])
        self.assertEqual(res["state_only_entries"], ["alpha@1.0.1"])

    def test_published_matching_state_is_unchanged(self):
        upstream = {"alpha": "1.0.1"}
        published = published_all(["alpha"], "1.0.1")
        state = {"alpha": {"ver": "1.0.1"}}
        res = up.compute_changed_plan(
            {"alpha"}, ["alpha"], upstream, published, set(), CHROOTS, 5,
            state=state)
        self.assertEqual(res["plan"], [])
        self.assertEqual(res["state_only"], [])
        self.assertEqual(res["unchanged"], ["alpha"])

    def test_workflow_state_only_has_no_build(self):
        text = UPDATE_YML.read_text(encoding="utf-8")
        # SRPM/COPR-submit жёстко привязаны к mode == 'build'
        srpm_gate = [ln for ln in text.splitlines() if "bin/make-srpm.sh" in ln]
        self.assertTrue(srpm_gate)
        self.assertIn("steps.plan.outputs.mode == 'build'", text)
        self.assertIn("STATE_ONLY_ENTRIES", text)


class TestOpenPrGuard(unittest.TestCase):
    """Fail-closed open bot-PR check before any COPR submit."""

    def _files(self, name, sha):
        return [{"filename": name, "sha": sha}]

    def test_empty_open_prs_proceed(self):
        res = up.evaluate_open_prs([], "", lambda n: [])
        self.assertEqual(res["decision"], "PROCEED")

    def test_same_diff_is_reused(self):
        files = self._files("state/state.json", "abc123")
        expected = up.pr_fingerprint(files)
        prs = [{"number": 7, "head": {"ref": "bot/state-sync-1-1", "sha": "x"}}]
        res = up.evaluate_open_prs(prs, expected, lambda n: files)
        self.assertEqual(res["decision"], "REUSE")
        self.assertEqual(res["reuse_pr"], 7)

    def test_different_diff_aborts(self):
        expected = up.pr_fingerprint(self._files("state/state.json", "aaa"))
        prs = [{"number": 7, "head": {"ref": "bot/state-sync-1-1"}}]
        res = up.evaluate_open_prs(prs, expected,
                                   lambda n: self._files("state/state.json", "bbb"))
        self.assertEqual(res["decision"], "ABORT")

    def test_unprovable_content_aborts(self):
        prs = [{"number": 7, "head": {"ref": "bot/state-sync-1-1"}}]
        res = up.evaluate_open_prs(prs, "", lambda n: [])
        self.assertEqual(res["decision"], "ABORT")

    def test_multiple_bot_prs_abort(self):
        prs = [{"number": 7, "head": {"ref": "bot/state-sync-a"}},
               {"number": 8, "head": {"ref": "bot/state-sync-b"}}]
        res = up.evaluate_open_prs(prs, "x", lambda n: [])
        self.assertEqual(res["decision"], "ABORT")

    def test_non_bot_prs_are_ignored(self):
        prs = [{"number": 9, "head": {"ref": "feat/thing"}}]
        res = up.evaluate_open_prs(prs, "", lambda n: [])
        self.assertEqual(res["decision"], "PROCEED")

    def test_malformed_open_pr_schema_raises(self):
        for prs in ([{"nope": 1}], [{"number": "7", "head": {"ref": "x"}}],
                    ["x"], {"not": "a list"}):
            with self.subTest(prs=prs), self.assertRaises(up.PlanError):
                up.evaluate_open_prs(prs, "x", lambda n: [])

    def test_pr_fingerprint_rejects_truncation(self):
        with self.assertRaises(up.PlanError):
            up.pr_fingerprint([{"filename": f"f{i}", "sha": "s"} for i in range(100)])

    def test_cmd_preflight_api_error_is_fail_closed(self):
        env = {up.PLAN_ENTRIES_ENV: "alpha@1.0.1",
               up.REPO_ENV: "o/r", "GITHUB_TOKEN": "t"}
        with mock.patch.dict(os.environ, env, clear=False), \
             mock.patch.object(up, "fetch_open_prs",
                               side_effect=up.PlanError("boom")), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = up.cmd_preflight()
        self.assertEqual(rc, 3)

    def test_cmd_preflight_empty_entries_proceeds(self):
        env = {up.PLAN_ENTRIES_ENV: "", up.REPO_ENV: "o/r", "GITHUB_TOKEN": "t"}
        out = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=False), \
             redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = up.cmd_preflight()
        self.assertEqual(rc, 0)
        self.assertIn("DECISION=PROCEED", out.getvalue())


class TestObserveUntilMerge(unittest.TestCase):
    """Observe the actual merge verdict; auto-merge enable is not completion."""

    def test_merged_verdict(self):
        self.assertEqual(up.merge_verdict({"merged": True}), "merged")

    def test_closed_unmerged_verdict(self):
        self.assertEqual(
            up.merge_verdict({"state": "closed", "merged": False}),
            "closed_unmerged")

    def test_conflict_verdict(self):
        self.assertEqual(
            up.merge_verdict({"state": "open", "merged": False, "mergeable": False}),
            "conflict")

    def test_failed_checks_verdict(self):
        pr = {"state": "open", "merged": False, "mergeable": True}
        checks = {"check_runs": [
            {"status": "completed", "conclusion": "failure"}]}
        self.assertEqual(up.merge_verdict(pr, checks), "checks_failed")

    def test_pending_then_merged(self):
        seq = [{"state": "open", "merged": False, "head": {"sha": "s"}},
               {"state": "open", "merged": True, "head": {"sha": "s"}}]
        calls = {"i": 0}

        def fetch(_n):
            v = seq[min(calls["i"], len(seq) - 1)]
            calls["i"] += 1
            return v

        status = up.observe_until(1, fetch, lambda s: {}, lambda: 0.0,
                                  lambda s: None, 100, 1)
        self.assertEqual(status, "merged")

    def test_timeout_is_not_success(self):
        clock = {"t": 0.0}

        def now():
            clock["t"] += 10
            return clock["t"]

        status = up.observe_until(
            1, lambda n: {"state": "open", "merged": False}, lambda s: {},
            now, lambda s: None, timeout=5, poll=1)
        self.assertEqual(status, "timeout")

    def test_api_errors_exhaust_to_api_error(self):
        status = up.observe_until(
            1, lambda n: (_ for _ in ()).throw(up.PlanError("x")),
            lambda s: {}, lambda: 0.0, lambda s: None, 100, 1, max_errors=3)
        self.assertEqual(status, "api_error")

    def test_merge_timeout_bounds(self):
        self.assertEqual(up.resolve_merge_timeout(""), up.MERGE_TIMEOUT_DEFAULT)
        for bad in ("0", "1", "999999999", "x"):
            with self.assertRaises(up.PlanError):
                up.resolve_merge_timeout(bad)


class TestWorkflowContainment(unittest.TestCase):
    """Bounded allowlist, max-wave and dispatch invariants in update.yml."""

    TEXT = UPDATE_YML.read_text(encoding="utf-8")

    def _blocks(self):
        parts = self.TEXT.split("      - name:")
        return [("      - name:" + p) for p in parts[1:]]

    def test_mutating_steps_carry_nonempty_allowlist(self):
        needles = ('bin/make-srpm.sh "$name" "$target"',
                   "coprase-status.py submit", "stage_state_sync.py",
                   "update-plan.py materialize",
                   "update-plan.py observe-merge")
        for blk in self._blocks():
            if any(n in blk for n in needles):
                self.assertIn("CANDY_PACKAGE_ALLOWLIST: ${{ steps.plan.outputs",
                              blk, msg=blk[:200])

    def test_max_wave_five(self):
        self.assertIn('CANDY_MAX_WAVE: "5"', self.TEXT)

    def test_no_force_no_full_rebuild(self):
        self.assertNotIn("full_rebuild", self.TEXT)
        self.assertNotIn("--force", self.TEXT)

    def test_manual_dispatch_plan_only_mandatory(self):
        self.assertIn("plan_only:", self.TEXT)
        self.assertIn("default: true", self.TEXT)
        # dispatch никогда не мутирует: MUTATE=true только для schedule
        self.assertIn('if [ "${{ github.event_name }}" = "schedule" ]; then',
                      self.TEXT)
        self.assertIn("plan_only=false запрещён", self.TEXT)

    def test_observe_merge_after_pr_commit(self):
        commit = self.TEXT.index("Ensure bounded state PR")
        observe = self.TEXT.index("observe-merge")
        self.assertLess(commit, observe)


if __name__ == "__main__":
    unittest.main()
