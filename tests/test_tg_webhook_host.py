"""Инварианты боевого хоста бота: вебхук, а не long-poll.

Тесты читают файлы, а не сеть: проверяется то, что ломается тихо —
второй хост бота (409 Conflict), потерянная проверка секрета, открытый
для посторонних доступ к состоянию CI и расхождение команд между
питоновской и деноvской реализациями.
"""
from __future__ import annotations

import pathlib
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
TS = ROOT / "supabase" / "functions" / "tg" / "index.ts"
PY = ROOT / "vercel" / "api" / "telegram.py"
TELEGRAM_WF = ROOT / ".github" / "workflows" / "telegram.yml"
MONITOR_WF = ROOT / ".github" / "workflows" / "monitor.yml"


def wf(path: pathlib.Path) -> dict:
    # `on:` в YAML 1.1 парсится как булево True — поэтому читаем ключ как есть.
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class SingleHostTests(unittest.TestCase):
    """Бота держит ровно один процесс, иначе Telegram отдаёт 409."""

    def test_longpoll_workflow_has_no_schedule(self) -> None:
        triggers = wf(TELEGRAM_WF)[True]
        self.assertNotIn("schedule", triggers)
        self.assertIn("workflow_dispatch", triggers)

    def test_longpoll_refuses_to_start_while_a_webhook_is_bound(self) -> None:
        steps = wf(TELEGRAM_WF)["jobs"]["listen"]["steps"]
        guard = [s for s in steps if "webhook" in (s.get("name") or "").lower()]
        self.assertTrue(guard, "нет шага-предохранителя против 409")
        body = guard[0]["run"]
        self.assertIn("getWebhookInfo", body)
        self.assertIn("exit 1", body)
        self.assertEqual(steps.index(guard[0]), 1, "предохранитель должен быть до запуска бота")

    def test_monitor_keeps_the_function_awake(self) -> None:
        steps = wf(MONITOR_WF)["jobs"]["check"]["steps"]
        ping = [s for s in steps if "awake" in (s.get("name") or "").lower()]
        self.assertTrue(ping, "нет пинга вебхука — free-tier усыпит проект")
        self.assertIn("functions/v1/tg", ping[0]["run"])


class EdgeFunctionTests(unittest.TestCase):
    """Деноvский хендлер обязан повторять защитные свойства питоновского."""

    def setUp(self) -> None:
        self.src = TS.read_text(encoding="utf-8")

    def test_secret_header_is_required(self) -> None:
        self.assertIn("X-Telegram-Bot-Api-Secret-Token", self.src)
        self.assertIn('if (!want) return false;', self.src)

    def test_unknown_chats_get_no_answer(self) -> None:
        self.assertIn("ownerChats().size > 0 && !isOwner(chat)", self.src)

    def test_run_is_owner_only(self) -> None:
        self.assertIn('if (!isOwner(chatId)) return', self.src)

    def test_jwt_verification_is_off_in_docs(self) -> None:
        # verify_jwt=true отрезал бы Telegram: он не умеет слать Authorization.
        self.assertIn("verify_jwt", (ROOT / "supabase" / "README.md").read_text(encoding="utf-8"))


class ParityTests(unittest.TestCase):
    """Один и тот же набор команд в обеих реализациях."""

    def test_both_hosts_answer_the_same_commands(self) -> None:
        ts = TS.read_text(encoding="utf-8")
        py = PY.read_text(encoding="utf-8")
        for token in ("статус", "прогресс", "ошиб", "сборк", "status", "progress", "build"):
            self.assertIn(token, ts, f"в edge-функции нет команды {token}")
            self.assertIn(token, py, f"в vercel-функции нет команды {token}")

    def test_both_hosts_cut_the_reply_to_the_telegram_limit(self) -> None:
        self.assertIn("3800", TS.read_text(encoding="utf-8"))
        self.assertIn("3800", PY.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
