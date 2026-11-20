#!/usr/bin/env python3
"""changed_packages.py — контракт списка «что доказывать SRPM'ом» (офлайн)."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "changed_packages", ROOT / "bin" / "changed_packages.py")
cp = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(cp)


def doc(*pkgs) -> dict:
    return {"project": {"name": "candy"}, "packages": list(pkgs)}


def pkg(name, **over) -> dict:
    out = {"name": name, "eco": "cargo", "host": "github", "slug": f"x/{name}"}
    out.update(over)
    return out


class ChangedNamesTests(unittest.TestCase):
    def test_new_package_is_reported(self) -> None:
        self.assertEqual(
            cp.changed_names(doc(pkg("a")), doc(pkg("a"), pkg("b"))), ["b"])

    def test_modified_package_is_reported(self) -> None:
        self.assertEqual(
            cp.changed_names(doc(pkg("a", slug="x/a")), doc(pkg("a", slug="y/a"))),
            ["a"])

    def test_untouched_package_is_not_reported(self) -> None:
        self.assertEqual(cp.changed_names(doc(pkg("a")), doc(pkg("a"))), [])

    def test_key_order_is_not_a_change(self) -> None:
        a = {"name": "a", "eco": "cargo", "host": "github"}
        b = {"host": "github", "eco": "cargo", "name": "a"}
        self.assertEqual(cp.changed_names(doc(a), doc(b)), [])

    def test_disabled_package_is_skipped(self) -> None:
        self.assertEqual(
            cp.changed_names(doc(), doc(pkg("a", enabled=False))), [])

    def test_enabling_a_package_is_reported(self) -> None:
        self.assertEqual(
            cp.changed_names(doc(pkg("a", enabled=False)), doc(pkg("a", enabled=True))),
            ["a"])

    def test_removed_package_is_not_reported(self) -> None:
        self.assertEqual(cp.changed_names(doc(pkg("a"), pkg("b")), doc(pkg("a"))), [])

    def test_result_is_sorted(self) -> None:
        self.assertEqual(
            cp.changed_names(doc(), doc(pkg("z"), pkg("a"), pkg("m"))),
            ["a", "m", "z"])

    def test_broken_structures_are_fatal(self) -> None:
        for bad in ([], {"packages": {}}, {"packages": [[]]},
                    {"packages": [{"eco": "cargo"}]},
                    {"packages": [{"name": ""}]}):
            with self.assertRaises(cp.ChangedError):
                cp.changed_names(doc(), bad)

    def test_duplicate_names_are_fatal(self) -> None:
        with self.assertRaises(cp.ChangedError):
            cp.changed_names(doc(), doc(pkg("a"), pkg("a")))

    def test_missing_ref_is_fatal_not_empty(self) -> None:
        with self.assertRaises(cp.ChangedError):
            cp.git_show_json("refs/heads/definitely-missing-ref", "pkgs.json")

    def test_cli_reports_failure_with_nonzero(self) -> None:
        self.assertEqual(
            cp.main(["--base-ref", "refs/heads/definitely-missing-ref"]), 1)

    def test_real_pkgs_json_parses(self) -> None:
        head = json.loads((ROOT / "pkgs.json").read_text(encoding="utf-8"))
        self.assertEqual(cp.changed_names(head, head), [])


class SmokeWorkflowTests(unittest.TestCase):
    """Доказательство SRPM обязано быть подключено к PR, а не лежать в bin/."""

    WF = ROOT / ".github" / "workflows" / "srpm-smoke.yml"

    def test_workflow_exists(self) -> None:
        self.assertTrue(self.WF.is_file())

    def test_workflow_runs_on_pull_request_for_pkgs_json(self) -> None:
        import yaml
        doc_ = yaml.safe_load(self.WF.read_text(encoding="utf-8"))
        on = doc_.get(True) or doc_.get("on")
        self.assertIn("pull_request", on)
        self.assertIn("pkgs.json", on["pull_request"]["paths"])

    def test_workflow_never_submits_to_copr(self) -> None:
        text = self.WF.read_text(encoding="utf-8")
        self.assertNotIn("copr-cli", text)
        self.assertNotIn("coprase-status.py submit", text)
        self.assertNotIn("git push", text)

    def test_workflow_uses_the_changed_package_list(self) -> None:
        text = self.WF.read_text(encoding="utf-8")
        self.assertIn("bin/changed_packages.py", text)
        self.assertIn("bin/make-srpm.sh", text)

    def test_missing_srpm_is_fatal(self) -> None:
        text = self.WF.read_text(encoding="utf-8")
        self.assertIn("SRPM-SMOKE-FAIL", text)


if __name__ == "__main__":
    unittest.main()
