#!/usr/bin/env python3
"""test_workflow_tools.py — узкие тесты tools/coprsnap.py и tools/tg-offset-save.sh.

Без сети: COPR curl подменяется фейковым runner'ом, git-сценарии идут
во временных репозиториях (bare origin + workspace).
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "tg-offset-save.sh"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


coprsnap = _load("coprsnap", ROOT / "tools" / "coprsnap.py")


class FakeRunner:
    """Подменяет subprocess.run для curl: отдаёт подготовленные ответы по порядку."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, cmd, capture_output=True, text=True):
        self.calls.append(cmd)
        out = cmd[cmd.index("-o") + 1]
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if outcome.get("body") is not None:
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(outcome["body"])
        return SimpleNamespace(
            returncode=outcome.get("rc", 0), stderr=outcome.get("stderr", "")
        )


def _run_snapshot(outcomes, attempts=3):
    """Запускает run_snapshot с фейковым curl; возвращает (rc, stdout, stderr, runner, slept, path)."""
    runner = FakeRunner(outcomes)
    slept = []
    out = tempfile.mktemp(prefix="snap-", suffix=".json")
    stdout, stderr = io.StringIO(), io.StringIO()
    rc = coprsnap.run_snapshot(
        "https://copr.test/build/list",
        out,
        attempts=attempts,
        runner=runner,
        sleep=slept.append,
        stdout=stdout,
        stderr=stderr,
    )
    return rc, stdout.getvalue(), stderr.getvalue(), runner, slept, out


class CoprsnapFetchTest(unittest.TestCase):
    """Пустой/HTML/5xx ответ COPR и retry до валидного JSON."""

    def tearDown(self):
        for name in os.listdir(tempfile.gettempdir()):
            if name.startswith("snap-") and name.endswith(".json"):
                try:
                    os.unlink(os.path.join(tempfile.gettempdir(), name))
                except OSError:
                    pass

    def _assert_clean_error(self, rc, out, err):
        """Понятный ::error, без JSONDecodeError и без ложного «No failed packages»."""
        self.assertEqual(rc, 1)
        self.assertIn("::error::", err)
        self.assertNotIn("Traceback", out + err)
        self.assertNotIn("JSONDecodeError", out + err)
        self.assertNotIn("No failed packages", out + err)

    def test_empty_response(self):
        """Пустое тело (curl rc=0) → ::error, а не падение json и не «No failed packages»."""
        rc, out, err, runner, _, _ = _run_snapshot([{"rc": 0, "body": ""}])
        self._assert_clean_error(rc, out, err)
        self.assertIn("JSON", err)

    def test_html_response(self):
        """HTML-страница ошибки вместо JSON → ::error, повторные попытки исчерпаны."""
        rc, out, err, runner, _, _ = _run_snapshot(
            [{"rc": 0, "body": "<html><body>502 Bad Gateway</body></html>"}]
        )
        self._assert_clean_error(rc, out, err)
        self.assertEqual(len(runner.calls), coprsnap.ATTEMPTS)

    def test_5xx_response(self):
        """HTTP 5xx: curl --fail-with-body выходит с 22, ретраи с backoff, затем ::error."""
        rc, out, err, runner, slept, _ = _run_snapshot(
            [{"rc": 22, "stderr": "curl: (22) The requested URL returned error: 503"}]
        )
        self._assert_clean_error(rc, out, err)
        self.assertIn("503", err)
        self.assertEqual(len(runner.calls), 3)
        self.assertEqual(slept, [2.0, 4.0])

    def test_retry_then_valid_json(self):
        """Два сетевых сбоя, затем валидный JSON → снапшот сохранён, отчёт напечатан."""
        body = json.dumps({"items": []})
        rc, out, err, runner, slept, path = _run_snapshot(
            [
                {"rc": 22, "stderr": "curl: (22) The requested URL returned error: 502"},
                {"rc": 18, "stderr": "curl: (18) transfer closed with data remaining"},
                {"rc": 0, "body": body},
            ]
        )
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(runner.calls), 3)
        self.assertEqual(slept, [2.0, 4.0])
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertIn("report", doc)
        self.assertIn("No current failed packages", out)


class CoprsnapAnalyzeTest(unittest.TestCase):
    """historical failed ≠ текущая проблема, null source_package.name не роняет."""

    def test_old_failed_newer_success(self):
        items = [
            {"id": 1, "state": "failed", "submitted_on": 100,
             "source_package": {"name": "pkg-a"}},
            {"id": 2, "state": "succeeded", "submitted_on": 200,
             "source_package": {"name": "pkg-a"}},
            {"id": 3, "state": "failed", "submitted_on": 150,
             "source_package": {"name": "pkg-b"}},
            {"id": 4, "state": "failed", "submitted_on": 300,
             "source_package": {"name": None}},
        ]
        rep = coprsnap.analyze(items)
        # pkg-a: старый failed перекрыт более новой успешной → не текущая проблема
        self.assertEqual(rep["current_failed"], ["pkg-b"])
        # счётчики по-прежнему показывают историю
        self.assertEqual(rep["counts"].get("failed"), 3)
        self.assertEqual(rep["unnamed"], 1)

    def test_report_sorting_tolerates_null_names(self):
        """Регресс исходного TypeError: sorted не падает на None-именах."""
        items = [
            {"id": 1, "state": "failed", "submitted_on": 1,
             "source_package": {"name": None}},
            {"id": 2, "state": "failed", "submitted_on": 2,
             "source_package": {"name": "zeta"}},
        ]
        rep = coprsnap.analyze(items)
        self.assertIn("FAILED: zeta", coprsnap.format_report(rep))


class CoprsnapTelegramTest(unittest.TestCase):
    """Telegram различает «есть актуальный failed» и «данные COPR недоступны»."""

    def _snapshot(self, tmp, current_failed):
        path = os.path.join(tmp, "coprsnap.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"report": {"current_failed": current_failed}}, fh)
        return path

    def test_data_unavailable(self):
        sent = []
        rc = coprsnap.run_telegram(
            "/nonexistent/coprsnap.json",
            chat_id="1", bot_token="t",
            sender=lambda c, t, m: sent.append(m),
            stdout=io.StringIO(),
        )
        self.assertEqual(rc, 0)
        self.assertEqual(len(sent), 1)
        self.assertIn("данные COPR недоступны", sent[0])

    def test_current_failed_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._snapshot(tmp, ["pkg-b"])
            sent = []
            coprsnap.run_telegram(path, chat_id="1", bot_token="t",
                                  sender=lambda c, t, m: sent.append(m),
                                  stdout=io.StringIO())
            self.assertEqual(len(sent), 1)
            self.assertIn("failed packages detected", sent[0])
            self.assertIn("• pkg-b", sent[0])

    def test_no_message_when_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._snapshot(tmp, [])
            sent = []
            coprsnap.run_telegram(path, chat_id="1", bot_token="t",
                                  sender=lambda c, t, m: sent.append(m),
                                  stdout=io.StringIO())
            self.assertEqual(sent, [])

    def test_snapshot_reused_for_report_and_telegram(self):
        """Один fetch: снапшот из run_snapshot используется и в telegram-шаге."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "coprsnap.json")
            body = json.dumps({"items": [
                {"id": 9, "state": "failed", "submitted_on": 500,
                 "source_package": {"name": "pkg-x"}},
            ]})
            runner = FakeRunner([{"rc": 0, "body": body}])
            rc = coprsnap.run_snapshot("https://copr.test/list", path,
                                       runner=runner, sleep=lambda s: None,
                                       stdout=io.StringIO(), stderr=io.StringIO())
            self.assertEqual(rc, 0)
            self.assertEqual(len(runner.calls), 1)
            sent = []
            coprsnap.run_telegram(path, chat_id="1", bot_token="t",
                                  sender=lambda c, t, m: sent.append(m),
                                  stdout=io.StringIO())
            self.assertIn("pkg-x", sent[0])


class TgOffsetSaveTest(unittest.TestCase):
    """tools/tg-offset-save.sh: fast-forward lineage, no-change, первоначальное создание."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bare = self.root / "origin.git"
        self.ws = self.root / "ws"
        self._git("init", "-q", "--bare", str(self.bare))
        self._git("init", "-q", "-b", "master", str(self.ws))
        self._git("config", "user.name", "test", cwd=self.ws)
        self._git("config", "user.email", "test@test", cwd=self.ws)
        (self.ws / "state").mkdir()
        (self.ws / "state" / "tg-offset.txt").write_text("100")
        (self.ws / "README.md").write_text("base")
        self._git("add", "-A", cwd=self.ws)
        self._git("commit", "-q", "-m", "base", cwd=self.ws)
        self._git("remote", "add", "origin", str(self.bare), cwd=self.ws)
        self._git("push", "-q", "origin", "master", cwd=self.ws)
        self.master_tip = self._git("rev-parse", "master", cwd=self.ws).stdout.strip()

    def tearDown(self):
        self.tmp.cleanup()

    def _git(self, *args, cwd=None, check=True):
        return subprocess.run(
            ["git", *args], cwd=str(cwd or self.root), check=check,
            capture_output=True, text=True,
        )

    def _create_remote_state_branch(self, content):
        """Ветка state/tg-offset на origin, как её видит CI после restore."""
        self._git("switch", "-q", "-c", "state/tg-offset", cwd=self.ws)
        (self.ws / "state" / "tg-offset.txt").write_text(content)
        self._git("add", "-A", cwd=self.ws)
        self._git("commit", "-q", "-m", f"offset {content}", cwd=self.ws)
        self._git("push", "-q", "origin", "HEAD:state/tg-offset", cwd=self.ws)
        tip = self._git("rev-parse", "HEAD", cwd=self.ws).stdout.strip()
        self._git("switch", "-q", "master", cwd=self.ws)
        return tip

    def _run_save(self, content):
        (self.ws / "state" / "tg-offset.txt").write_text(content)
        env = dict(os.environ, TG_OFFSET_PUSH_URL=str(self.bare))
        return subprocess.run(
            ["bash", str(SCRIPT), "state/tg-offset.txt"],
            cwd=self.ws, env=env, capture_output=True, text=True,
        )

    def _bare_tip(self):
        return self._git("rev-parse", "state/tg-offset", cwd=self.bare,
                         check=False)

    def test_fast_forward_lineage(self):
        """Дивергентная история: новый offset-коммит — поверх remote, push FF."""
        old_tip = self._create_remote_state_branch("101")
        proc = self._run_save("102")  # бот обновил offset
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        tip = self._bare_tip().stdout.strip()
        self.assertNotEqual(tip, old_tip)
        parent = self._git("rev-parse", f"{tip}^", cwd=self.bare).stdout.strip()
        # ключевая инварианта: parent = прежний remote-tip → push был fast-forward
        self.assertEqual(parent, old_tip)
        content = self._git("show", "state/tg-offset:state/tg-offset.txt",
                            cwd=self.bare).stdout.strip()
        self.assertEqual(content, "102")
        # master не тронут (runtime offset не пишется в master)
        bare_master = self._git("rev-parse", "master", cwd=self.bare).stdout.strip()
        self.assertEqual(bare_master, self.master_tip)

    def test_no_change_offset(self):
        """Offset не изменился → без коммита и без push, exit 0."""
        old_tip = self._create_remote_state_branch("101")
        proc = self._run_save("101")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("unchanged", proc.stdout)
        self.assertEqual(self._bare_tip().stdout.strip(), old_tip)

    def test_initial_branch_creation(self):
        """Ветки state/tg-offset ещё нет → она создаётся обычным push."""
        proc = self._run_save("105")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        tip = self._bare_tip().stdout.strip()
        parent = self._git("rev-parse", f"{tip}^", cwd=self.bare).stdout.strip()
        self.assertEqual(parent, self.master_tip)
        content = self._git("show", "state/tg-offset:state/tg-offset.txt",
                            cwd=self.bare).stdout.strip()
        self.assertEqual(content, "105")

    def test_missing_offset_file_is_noop(self):
        proc = subprocess.run(
            ["bash", str(SCRIPT), "state/nope.txt"],
            cwd=self.ws,
            env=dict(os.environ, TG_OFFSET_PUSH_URL=str(self.bare)),
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("нечего сохранять", proc.stdout)


if __name__ == "__main__":
    unittest.main()
