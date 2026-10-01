#!/usr/bin/env python3
"""Commit-fallback версии: дата коммита в api_ver.sh + hash-защита в cmd_versions.

Баг: fallback=commit собирал версию как «сегодняшняя дата + hash коммита» —
один и тот же HEAD выглядел как NEW при каждом прогоне. Фикс: дата берётся из
самого коммита (GitHub/GitLab/Codeberg), а cmd_versions не двигает цель, если
old/new — YYYYMMDD.<hash> с одинаковым hash.

Run remotely via:  python3 -m unittest -v tests/test_commit_ver.py
"""

import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "bin" / "coprase-status.py"

_spec = importlib.util.spec_from_file_location("coprase_status", str(MODULE_PATH))
cs = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader, "coprase-status.py должен быть загружаем"
_spec.loader.exec_module(cs)


class TestSameCommitVersion(unittest.TestCase):
    """same_commit_version: hash главнее даты, semver/mixed не затрагиваются."""

    def test_same_hash_diff_dates_unchanged(self):
        self.assertTrue(cs.same_commit_version("20260920.abc1234", "20260927.abc1234"))

    def test_new_hash_is_new(self):
        self.assertFalse(cs.same_commit_version("20260927.abc1234", "20260927.def5678"))

    def test_gitlab_8char_hash_real_case(self):
        self.assertTrue(cs.same_commit_version("20260922.19a71dc8", "20250522.19a71dc8"))
        self.assertFalse(cs.same_commit_version("20260922.19a71dc8", "20260922.19a71dc9"))

    def test_semver_untouched(self):
        self.assertFalse(cs.same_commit_version("1.2.3", "1.2.4"))
        self.assertFalse(cs.same_commit_version("2.0.1", "2.0.1"))
        self.assertFalse(cs.same_commit_version("2026.9.13", "20260913.abcdef0"))

    def test_mixed_and_empty_formats(self):
        self.assertFalse(cs.same_commit_version("20260920.abc1234", "1.2.3"))
        self.assertFalse(cs.same_commit_version("1.2.3", "20260927.abc1234"))
        self.assertFalse(cs.same_commit_version("", "20260927.abc1234"))
        self.assertFalse(cs.same_commit_version("20260920.abc1234", ""))


class TestCmdVersionsCommitGuard(unittest.TestCase):
    """cmd_versions: та же hash не трогает state.json, новый hash/memver обновляют."""

    PKGS = [
        {"name": "p_same", "eco": "script"},
        {"name": "p_new", "eco": "script"},
        {"name": "p_sem_same", "eco": "script"},
        {"name": "p_sem_new", "eco": "script"},
        {"name": "p_off", "eco": "script", "enabled": False},
    ]
    OLD = {
        "p_same": "20260920.abc1234",
        "p_new": "20260920.abc1234",
        "p_sem_same": "2.0.1",
        "p_sem_new": "2.0.1",
        "p_off": "20260920.abc1234",
    }
    UP = {
        "p_same": "20260927.abc1234",
        "p_new": "20260927.def5678",
        "p_sem_same": "2.0.1",
        "p_sem_new": "2.1.0",
        "p_off": "20260927.aaa9999",
    }

    def run_versions(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            (tmp / "state").mkdir()
            (tmp / "bin").mkdir()
            (tmp / "pkgs.json").write_text(json.dumps({"packages": self.PKGS}))
            (tmp / "state" / "state.json").write_text(
                json.dumps({k: {"ver": v, "ts": 123.0} for k, v in self.OLD.items()}))
            stub = tmp / "bin" / "api_ver.sh"
            cases = "\n".join(f'  {n}) echo "{v}" ;;' for n, v in self.UP.items())
            stub.write_text('#!/usr/bin/env bash\ncase "$1" in\n' + cases + '\n  *) ;;\nesac\n')
            stub.chmod(0o755)
            orig = os.getcwd()
            os.chdir(td)
            try:
                os.environ.pop("CANDY_PACKAGE_ALLOWLIST", None)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    cs.cmd_versions()
                state = json.loads((tmp / "state" / "state.json").read_text())
                out = buf.getvalue()
            finally:
                os.chdir(orig)
            return state, out

    def test_state_transitions_and_output(self):
        state, out = self.run_versions()
        self.assertEqual(state["p_same"]["ver"], "20260920.abc1234")
        self.assertEqual(state["p_same"]["ts"], 123.0)
        self.assertEqual(state["p_new"]["ver"], "20260927.def5678")
        self.assertNotEqual(state["p_new"]["ts"], 123.0)
        self.assertEqual(state["p_sem_same"]["ver"], "2.0.1")
        self.assertEqual(state["p_sem_same"]["ts"], 123.0)
        self.assertEqual(state["p_sem_new"]["ver"], "2.1.0")
        self.assertEqual(state["p_off"]["ver"], "20260920.abc1234")
        self.assertEqual(state["p_off"]["ts"], 123.0)
        self.assertIn("[SAME]  p_same", out)
        self.assertIn("[NEW]  p_new", out)
        self.assertIn("[NEW]  p_sem_new", out)
        self.assertNotIn("[NEW]  p_same", out)
        self.assertIn("Цели обновлены: 2, без изменений: 2, не проверилось: 0", out)


class TestApiVerCommitDate(unittest.TestCase):
    """api_ver.sh: версия из даты коммита, детерминированно на 3 хостах."""

    PKGS = [
        {"name": "fb-gh", "host": "github", "slug": "fb/gh-norepo", "fallback": "commit"},
        {"name": "fb-gh-author", "host": "github", "slug": "fb/gh-author", "fallback": "commit"},
        {"name": "fb-gh-tag", "host": "github", "slug": "fb/gh-tagged"},
        {"name": "fb-gl", "host": "gitlab", "slug": "grp/fb-gl", "fallback": "commit"},
        {"name": "fb-cb", "host": "codeberg", "slug": "grp/fb-cb", "fallback": "commit"},
        {"name": "fb-cb-author", "host": "codeberg", "slug": "grp/fb-cb-author", "fallback": "commit"},
    ]
    FIXTURES = {
        "github_committer.json": [{
            "sha": "1f0c3d2e9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d",
            "commit": {"committer": {"date": "2026-09-25T10:30:00Z"},
                       "author": {"date": "2026-09-24T08:00:00Z"}},
        }],
        "github_author.json": [{
            "sha": "aaaabbbbccccddddeeeeffff0000111122223333",
            "commit": {"author": {"date": "2026-08-01T23:59:59+02:00"}},
        }],
        "gitlab_committed.json": [{
            "short_id": "a1b2c3d4",
            "committed_date": "2026-09-24T23:10:00+02:00",
            "created_at": "2026-09-23T10:00:00+02:00",
        }],
        "codeberg_committer.json": [{
            "sha": "cba337b51234567890abcdef1234567890abcdef",
            "commit": {"committer": {"date": "2026-09-26T05:00:00-07:00"},
                       "author": {"date": "2026-09-25T01:00:00-07:00"}},
        }],
        "codeberg_author.json": [{
            "sha": "0123456789abcdef0123456789abcdef01234567",
            "commit": {"author": {"date": "2026-07-15T12:00:00+00:00"}},
        }],
    }
    EXPECTED = {
        "fb-gh": "20260925.1f0c3d2",
        "fb-gh-author": "20260801.aaaabbb",
        "fb-gl": "20260924.a1b2c3d4",
        "fb-cb": "20260926.cba337b",
        "fb-cb-author": "20260715.0123456",
        "fb-gh-tag": "1.2.3",
    }
    CURL_STUB = """#!/usr/bin/env bash
url=""
for a in "$@"; do
    case "$a" in http://*|https://*) url="$a" ;; esac
done
fx="${TEST_FIXTURES:?}"
case "$url" in
  *"/repos/fb/gh-norepo/releases/latest") echo '{}' ;;
  *"/repos/fb/gh-norepo/tags"*) echo '[]' ;;
  *"/repos/fb/gh-norepo/commits"*) cat "$fx/github_committer.json" ;;
  *"/repos/fb/gh-author/releases/latest") echo '{}' ;;
  *"/repos/fb/gh-author/tags"*) echo '[]' ;;
  *"/repos/fb/gh-author/commits"*) cat "$fx/github_author.json" ;;
  *"/repos/fb/gh-tagged/releases/latest") echo '{"tag_name":"v1.2.3"}' ;;
  *"projects/grp%2Ffb-gl/releases"*) echo '[]' ;;
  *"projects/grp%2Ffb-gl/repository/commits"*) cat "$fx/gitlab_committed.json" ;;
  *"/repos/grp/fb-cb/tags"*) echo '[]' ;;
  *"/repos/grp/fb-cb/commits"*) cat "$fx/codeberg_committer.json" ;;
  *"/repos/grp/fb-cb-author/tags"*) echo '[]' ;;
  *"/repos/grp/fb-cb-author/commits"*) cat "$fx/codeberg_author.json" ;;
  *) echo "curl-stub: unexpected URL: $url" >&2; exit 22 ;;
esac
exit 0
"""

    @classmethod
    def setUpClass(cls):
        cls._td = tempfile.TemporaryDirectory()
        cls.repo = pathlib.Path(cls._td.name)
        (cls.repo / "bin").mkdir()
        (cls.repo / "fx").mkdir()
        (cls.repo / "stub").mkdir()
        shutil.copy2(ROOT / "bin" / "api_ver.sh", cls.repo / "bin" / "api_ver.sh")
        (cls.repo / "bin" / "api_ver.sh").chmod(0o755)
        (cls.repo / "pkgs.json").write_text(json.dumps({"packages": cls.PKGS}))
        for fname, data in cls.FIXTURES.items():
            (cls.repo / "fx" / fname).write_text(json.dumps(data))
        curl = cls.repo / "stub" / "curl"
        curl.write_text(cls.CURL_STUB)
        curl.chmod(0o755)

    @classmethod
    def tearDownClass(cls):
        cls._td.cleanup()

    def run_pkg(self, name, tz="UTC"):
        env = dict(os.environ)
        env["PATH"] = f"{self.repo / 'stub'}:{env['PATH']}"
        env["TEST_FIXTURES"] = str(self.repo / "fx")
        env["TZ"] = tz
        env.pop("CANDY_PACKAGE_ALLOWLIST", None)
        r = subprocess.run([str(self.repo / "bin" / "api_ver.sh"), name],
                           cwd=self.repo, env=env, capture_output=True,
                           text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_expected_versions_all_hosts(self):
        for name, want in self.EXPECTED.items():
            with self.subTest(pkg=name):
                self.assertEqual(self.run_pkg(name), want)

    def test_deterministic_across_runs_and_timezones(self):
        for name, want in self.EXPECTED.items():
            with self.subTest(pkg=name):
                got = [self.run_pkg(name, tz=tz)
                       for tz in ("UTC", "America/New_York", "Pacific/Kiritimati")]
                self.assertEqual(got, [want] * 3)

    def test_wallclock_date_removed_from_script(self):
        src = (ROOT / "bin" / "api_ver.sh").read_text()
        self.assertNotIn("date -u +%Y%m%d", src)


if __name__ == "__main__":
    unittest.main()
