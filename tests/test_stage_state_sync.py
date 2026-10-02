#!/usr/bin/env python3
"""Bin/stage_state_sync.py: bounded-гейт staging state/SPECS для bot-PR.

Ключевое свойство: bounded-прогон с selection из 7 пакетов не может застейдить
132 specs — churn дат от gen_specs --all откатывается, staging ограничен
state.json + спеками selection (≤ 1+|selection| файлов).

Run remotely via:  python3 -m unittest -v tests/test_stage_state_sync.py
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELPER = ROOT / "bin" / "stage_state_sync.py"

SPEC_TPL = """Name:        {name}
Version:     {ver}
Release:     1%{{?dist}}
Summary:     test package

%description
test

%files

%changelog
* {date} candy-bot <candy@localhost> - {ver}-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
"""

OLD_DATE = "Tue Sep 22 2026"
NEW_DATE = "Fri Oct 02 2026"


def sh(repo: pathlib.Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True, check=True)
    return r.stdout


class StageStateSyncTest(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.repo = pathlib.Path(self._td.name)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=self.repo, check=True)
        self.pkgs = [f"p{i:03d}" for i in range(131)]
        (self.repo / "SPECS").mkdir()
        (self.repo / "state").mkdir()
        for n in self.pkgs:
            (self.repo / "SPECS" / f"{n}.spec").write_text(
                SPEC_TPL.format(name=n, ver="1.0.0", date=OLD_DATE))
        self._write_state({n: {"ver": "1.0.0", "ts": 1} for n in self.pkgs})
        (self.repo / "pkgs.json").write_text(
            json.dumps({"packages": [{"name": n} for n in self.pkgs]}))
        (self.repo / "README.md").write_text("x\n")
        subprocess.run(["git", "add", "-A"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.repo, check=True)

    # --- фикстуры ---

    def _write_state(self, st: dict):
        (self.repo / "state" / "state.json").write_text(
            json.dumps(st, ensure_ascii=False, indent=1))

    def _read_state(self) -> dict:
        return json.loads((self.repo / "state" / "state.json").read_text())

    def bump_state(self, names):
        st = self._read_state()
        for n in names:
            st[n] = {"ver": "1.0.1", "ts": 2}
        self._write_state(st)

    def bump_spec(self, names):
        for n in names:
            (self.repo / "SPECS" / f"{n}.spec").write_text(
                SPEC_TPL.format(name=n, ver="1.0.1", date=NEW_DATE))

    def churn_spec(self, names):
        for n in names:
            (self.repo / "SPECS" / f"{n}.spec").write_text(
                SPEC_TPL.format(name=n, ver="1.0.0", date=NEW_DATE))

    # --- запуск helper ---

    def run_helper(self, selection=None):
        env = dict(os.environ)
        if selection is None:
            env.pop("CANDY_PACKAGE_ALLOWLIST", None)
        else:
            env["CANDY_PACKAGE_ALLOWLIST"] = selection
        r = subprocess.run([sys.executable, str(HELPER)],
                           cwd=self.repo, env=env, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def staged(self) -> list:
        return sorted(sh(self.repo, "diff", "--cached", "--name-only").splitlines())

    def worktree_dirty(self) -> list:
        return sorted(sh(self.repo, "status", "--porcelain").splitlines())

    # --- тесты ---

    def test_bounded_131_specs_stage_only_selection(self):
        """132-spec guard: 7 selection-пакетов → ровно 8 staged, churn откат."""
        sel = self.pkgs[:7]
        churn = self.pkgs[7:]  # 124 спеки с date churn
        self.bump_state(sel)
        self.bump_spec(sel)
        self.churn_spec(churn)
        rc, out = self.run_helper(",".join(sel))
        self.assertEqual(rc, 0, out)
        expected = sorted(["state/state.json"] + [f"SPECS/{n}.spec" for n in sel])
        self.assertEqual(self.staged(), expected)
        self.assertEqual(len(self.staged()), 8)  # никогда 132
        # churn-спеки откачены к BASE — в status только 8 staged-файлов
        dirty = self.worktree_dirty()
        self.assertEqual(len(dirty), 8, dirty)
        joined = "".join(dirty)
        for i in range(7, 131):
            self.assertNotIn(f"p{i:03d}", joined, dirty)
        self.assertIn("REVERTED: SPECS/p130.spec", out)

    def test_bounded_entry_outside_selection_aborts(self):
        sel = self.pkgs[:7]
        self.bump_state(sel)
        self.bump_spec(sel)
        self.bump_state([self.pkgs[7]])  # 8-й entry вне selection
        rc, out = self.run_helper(",".join(sel))
        self.assertNotEqual(rc, 0)
        self.assertIn("вне bounded selection", out)
        self.assertEqual(self.staged(), [])

    def test_bounded_pkgs_json_change_aborts(self):
        sel = self.pkgs[:7]
        self.bump_state(sel)
        self.bump_spec(sel)
        (self.repo / "pkgs.json").write_text('{"packages": []}')
        rc, out = self.run_helper(",".join(sel))
        self.assertNotEqual(rc, 0)
        self.assertIn("pkgs.json", out)
        self.assertEqual(self.staged(), [])

    def test_bounded_unexpected_path_aborts(self):
        sel = self.pkgs[:7]
        self.bump_state(sel)
        self.bump_spec(sel)
        (self.repo / "README.md").write_text("tampered\n")
        rc, out = self.run_helper(",".join(sel))
        self.assertNotEqual(rc, 0)
        self.assertIn("посторонние", out)
        self.assertEqual(self.staged(), [])

    def test_bounded_stale_spec_aborts(self):
        """Цель сдвинулась, спека не перегенерирована → abort."""
        sel = self.pkgs[:7]
        self.bump_state(sel)
        self.bump_spec(sel[:6])  # у sel[6] спека осталась старой
        rc, out = self.run_helper(",".join(sel))
        self.assertNotEqual(rc, 0)
        self.assertIn("!= state ver", out)
        self.assertEqual(self.staged(), [])

    def test_bounded_spec_bump_without_state_aborts(self):
        sel = self.pkgs[:7]
        self.bump_state(sel)
        self.bump_spec(sel)
        self.bump_spec([self.pkgs[7]])  # спека вне state-двига — но она вне
        # selection → откат, не abort; abort нужен для selection-пакета:
        st = self._read_state()
        st[sel[0]] = {"ver": "1.0.0", "ts": 1}  # state sel[0] откатили
        self._write_state(st)
        rc, out = self.run_helper(",".join(sel))
        self.assertNotEqual(rc, 0)
        self.assertIn("без изменения state-цели", out)

    def test_unbounded_date_churn_reverts_nothing_staged(self):
        self.churn_spec(self.pkgs[:3])
        rc, out = self.run_helper(None)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.staged(), [])
        self.assertEqual(self.worktree_dirty(), [])

    def test_unbounded_catchup_spec_to_existing_state_kept(self):
        """Спека догоняет уже зафиксированную в state цель (drift-фикс)."""
        st = self._read_state()
        st[self.pkgs[0]] = {"ver": "1.0.1", "ts": 1}  # state уже впереди (BASE)
        self._write_state(st)
        subprocess.run(["git", "add", "-A"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "state ahead"], cwd=self.repo, check=True)
        # BASE: spec=1.0.0, state=1.0.1. Рабочее дерево: спека догоняет.
        self.bump_spec([self.pkgs[0]])
        rc, out = self.run_helper(None)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.staged(), [f"SPECS/{self.pkgs[0]}.spec"])

    def test_unbounded_spec_version_without_state_aborts(self):
        self.bump_spec([self.pkgs[0]])  # версия спеки ушла, state не двигался
        rc, out = self.run_helper(None)
        self.assertNotEqual(rc, 0)
        self.assertIn("без изменения state-цели", out)
        self.assertEqual(self.staged(), [])


if __name__ == "__main__":
    unittest.main()
