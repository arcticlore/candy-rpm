#!/usr/bin/env python3
"""Pure unit tests for bin/coprase-status.py selection policy.

Standard library only (unittest + importlib.util); no network, no subprocess,
no COPR mutation. The hyphenated module name is loaded safely by path.
Run remotely via:  python3 -m unittest -v tests/test_coprase_status.py
"""

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "bin" / "coprase-status.py"

_spec = importlib.util.spec_from_file_location("coprase_status", str(MODULE_PATH))
cs = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader, "coprase-status.py должен быть загружаем"
_spec.loader.exec_module(cs)

# Fixture surface reproduces the real pkgs.json shapes, including the
# historical buggy `diagon`: `"enabled": "false"` (a string).
PKGS = [
    {"name": "mise", "eco": "cargo", "enabled": True},
    {"name": "ttysvr", "eco": "cargo"},                     # missing enabled -> enabled
    {"name": "termusic", "eco": "cargo", "enabled": True},
    {"name": "diagon", "eco": "c-cmake", "enabled": "false"},  # legacy string-false bug
    {"name": "pinned", "eco": "script", "enabled": False},
    {"name": "strtrue", "eco": "script", "enabled": "true"},   # ordinary string -> enabled
]

ENABLED_ONLY = {"mise", "ttysvr", "termusic", "strtrue"}


class TestEnabledSemantics(unittest.TestCase):
    """B1: robust enabled policy, compatible with gen_specs.Package.is_enabled()."""

    def test_missing_and_booleans(self):
        self.assertTrue(cs.is_package_enabled(None))     # missing -> enabled
        self.assertTrue(cs.is_package_enabled(True))     # bool true  -> enabled
        self.assertFalse(cs.is_package_enabled(False))   # bool false -> disabled

    def test_legacy_strings_disabled(self):
        self.assertFalse(cs.is_package_enabled("false"))
        self.assertFalse(cs.is_package_enabled("0"))

    def test_other_strings_enabled(self):
        for s in ("true", "1", "yes", "garbage"):        # прочие строки -> enabled
            self.assertTrue(cs.is_package_enabled(s))


class TestAllowlistParsing(unittest.TestCase):
    """B2: fail-closed comma-separated allowlist parser."""

    def test_empty_and_whitespace(self):
        self.assertEqual(cs.parse_package_allowlist(""), [])
        self.assertEqual(cs.parse_package_allowlist("   "), [])
        self.assertEqual(cs.parse_package_allowlist(" , , "), [])   # comma-only == empty

    def test_trim_and_order(self):
        self.assertEqual(cs.parse_package_allowlist(" mise , ttysvr "),
                         ["mise", "ttysvr"])

    def test_duplicates_normalized(self):
        self.assertEqual(cs.parse_package_allowlist("mise,mise,ttysvr,mise"),
                         ["mise", "ttysvr"])

    def test_malformed_name_rejected(self):
        for bad in ("mise;ttysvr", "mis e", "mi!se", "-bad", "a..b", "a/b"):
            with self.assertRaises(SystemExit, msg=bad):
                cs.parse_package_allowlist(bad)


class TestEffectiveSelection(unittest.TestCase):
    """B1+B2: fail-closed effective set policy."""

    def test_empty_allowlist_returns_only_enabled(self):
        self.assertEqual(cs.select_effective(PKGS, ""), ENABLED_ONLY)

    def test_diagon_string_false_excluded(self):
        eff = cs.select_effective(PKGS, "")
        self.assertNotIn("diagon", eff)
        self.assertNotIn("pinned", eff)

    def test_exact_subset_preserved(self):
        eff = cs.select_effective(PKGS, "mise,ttysvr,termusic")
        self.assertEqual(eff, {"mise", "ttysvr", "termusic"})

    def test_comma_only_matches_empty(self):
        self.assertEqual(cs.select_effective(PKGS, " ,, "), ENABLED_ONLY)

    def test_unknown_rejected(self):
        with self.assertRaises(SystemExit):
            cs.select_effective(PKGS, "not-a-real-pkg")

    def test_disabled_requested_rejected(self):
        with self.assertRaises(SystemExit):
            cs.select_effective(PKGS, "pinned")
        with self.assertRaises(SystemExit):
            cs.select_effective(PKGS, "diagon")


class TestSubmitCandidates(unittest.TestCase):
    """B2 (force cannot widen) + existing needs_submission behavior."""

    def test_force_cannot_widen_bounded_set(self):
        eff = cs.select_effective(PKGS, "mise,termusic")
        cands = cs.submit_candidates(eff, history={}, versions={}, force=True)
        self.assertEqual(set(cands), {"mise", "termusic"})

    def test_no_builds_needs_submission(self):
        self.assertTrue(cs.needs_submission("mise", "1.0", []))

    def test_no_succeeded_needs_submission(self):
        hist = [("failed", "1.0-1", 111), ("canceled", "0.9-1", 110)]
        self.assertTrue(cs.needs_submission("mise", "1.0", hist))

    def test_succeeded_current_version_done(self):
        hist = [("failed", "0.9-1", 110), ("succeeded", "1.0-1", 111)]
        self.assertFalse(cs.needs_submission("mise", "1.0", hist))

    def test_succeeded_older_version_rerun(self):
        hist = [("succeeded", "0.9-1", 111)]
        self.assertTrue(cs.needs_submission("mise", "1.0", hist))


if __name__ == "__main__":
    unittest.main()