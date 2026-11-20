#!/usr/bin/env python3
"""Инварианты зачистки: мёртвое не возвращается, master не пишется напрямую."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# тот же набор, что дозор containment применяет к workflow
PUSH_REFS = re.compile(r"HEAD\s*:\s*master|HEAD\s*->\s*master|refs/heads/master")
SCAN_DIRS = ("bin", "tools", ".github/workflows")
DEAD_PACKAGES = {"chucknorris", "hack", "cli-visualizer", "lifecycler", "fireworks"}


# сам дозор содержит искомые шаблоны как регулярные выражения — он себя не судит
SELF_EXEMPT = {"validate.yml", "test_stale_sweep.py"}


def scanned_files() -> list[Path]:
    out: list[Path] = []
    for d in SCAN_DIRS:
        for p in sorted((ROOT / d).rglob("*")):
            if p.is_file() and p.suffix in (".sh", ".py", ".yml", ".yaml") \
                    and p.name not in SELF_EXEMPT:
                out.append(p)
    return out


class NoDirectMasterWrite(unittest.TestCase):
    """Запись в master идёт только через PR — в скриптах тоже, не только в workflow."""

    def test_no_explicit_master_ref_push(self) -> None:
        bad = []
        for p in scanned_files():
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if PUSH_REFS.search(line):
                    bad.append(f"{p.relative_to(ROOT)}:{i}")
        self.assertEqual(bad, [])

    def test_no_git_push_master_on_one_line(self) -> None:
        bad = []
        for p in scanned_files():
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if re.search(r"\bgit push\b", line) and re.search(r"\bmaster\b", line):
                    bad.append(f"{p.relative_to(ROOT)}:{i}")
        self.assertEqual(bad, [])

    def test_removed_laptop_scripts_stay_removed(self) -> None:
        for name in ("bin/push.sh", "bin/auto-issue.sh"):
            self.assertFalse((ROOT / name).exists(), name)

    def test_nothing_references_the_removed_scripts(self) -> None:
        bad = []
        for p in scanned_files():
            text = p.read_text(encoding="utf-8", errors="ignore")
            for name in ("bin/push.sh", "bin/auto-issue.sh"):
                if name in text:
                    bad.append(f"{p.relative_to(ROOT)} -> {name}")
        self.assertEqual(bad, [])


class LogrotateIsReal(unittest.TestCase):
    """Ротация обязана что-то менять в источнике, а не в копии раннера."""

    WF = ROOT / ".github" / "workflows" / "logrotate.yml"

    def setUp(self) -> None:
        self.text = self.WF.read_text(encoding="utf-8")

    def test_selects_by_commit_date_not_mtime(self) -> None:
        # в свежем checkout'е mtime == время клона, -mtime отобрал бы пустоту
        self.assertIn("--format=%cs", self.text)
        self.assertNotIn("-mtime", self.text)

    def test_removal_lands_through_a_bot_branch_pr(self) -> None:
        self.assertIn("bot/logrotate-", self.text)
        self.assertIn("gh pr create", self.text)

    def test_it_can_actually_write(self) -> None:
        import yaml
        doc = yaml.safe_load(self.text)
        self.assertEqual(doc["permissions"]["contents"], "write")
        self.assertEqual(doc["permissions"]["pull-requests"], "write")

    def test_it_is_not_scheduled(self) -> None:
        # scheduled-мутации разрешены только update.yml
        import yaml
        doc = yaml.safe_load(self.text)
        on = doc.get(True) or doc.get("on")
        self.assertNotIn("schedule", on)


class DeadPackagesAreGone(unittest.TestCase):
    def setUp(self) -> None:
        self.pkgs = json.loads((ROOT / "pkgs.json").read_text(encoding="utf-8"))["packages"]

    def test_entries_removed(self) -> None:
        names = {p["name"] for p in self.pkgs}
        self.assertEqual(names & DEAD_PACKAGES, set())

    def test_specs_removed(self) -> None:
        for name in DEAD_PACKAGES:
            self.assertFalse((ROOT / "SPECS" / f"{name}.spec").exists(), name)

    def test_catalog_does_not_list_them(self) -> None:
        text = (ROOT / "PACKAGES.md").read_text(encoding="utf-8")
        for name in DEAD_PACKAGES:
            self.assertNotIn(f"~~{name}~~", text)

    def test_every_enabled_package_still_has_a_spec(self) -> None:
        missing = [p["name"] for p in self.pkgs
                   if p.get("enabled", True) and not (ROOT / "SPECS" / f"{p['name']}.spec").exists()]
        self.assertEqual(missing, [])

    def test_no_orphan_specs(self) -> None:
        names = {p["name"] for p in self.pkgs}
        orphans = sorted(s.stem for s in (ROOT / "SPECS").glob("*.spec") if s.stem not in names)
        self.assertEqual(orphans, [])


class BotKeepsNoWritePath(unittest.TestCase):
    def test_tg_notify_no_longer_pushes_anything(self) -> None:
        text = (ROOT / "tools" / "tg-notify.py").read_text(encoding="utf-8")
        self.assertNotIn("push_offset", text)
        self.assertNotIn("git push", text)

    def test_offset_persistence_still_exists_in_the_right_place(self) -> None:
        saver = (ROOT / "tools" / "tg-offset-save.sh").read_text(encoding="utf-8")
        self.assertIn("state/tg-offset", saver)


if __name__ == "__main__":
    unittest.main()
