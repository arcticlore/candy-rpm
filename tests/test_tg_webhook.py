#!/usr/bin/env python3
"""Маршрутизация вебхук-бота — офлайн, без сети и без Telegram."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "tg_webhook", ROOT / "vercel" / "api" / "telegram.py")
tg = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(tg)


class Headers(dict):
    def get(self, k, default=None):  # заголовки HTTP регистронезависимы
        for key, val in self.items():
            if key.lower() == k.lower():
                return val
        return default


class SecretTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = dict(tg.os.environ)

    def tearDown(self) -> None:
        tg.os.environ.clear()
        tg.os.environ.update(self._env)

    def test_missing_secret_config_rejects(self) -> None:
        tg.os.environ.pop("TG_SECRET", None)
        self.assertFalse(tg.secret_ok(Headers({"X-Telegram-Bot-Api-Secret-Token": "x"})))

    def test_wrong_secret_rejects(self) -> None:
        tg.os.environ["TG_SECRET"] = "right"
        self.assertFalse(tg.secret_ok(Headers({"X-Telegram-Bot-Api-Secret-Token": "wrong"})))

    def test_absent_header_rejects(self) -> None:
        tg.os.environ["TG_SECRET"] = "right"
        self.assertFalse(tg.secret_ok(Headers({})))

    def test_matching_secret_accepts(self) -> None:
        tg.os.environ["TG_SECRET"] = "right"
        self.assertTrue(tg.secret_ok(Headers({"X-Telegram-Bot-Api-Secret-Token": "right"})))


class RouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = dict(tg.os.environ)
        self.calls: list[str] = []
        self._orig = (tg.action_status, tg.action_progress, tg.action_errors,
                      tg.action_builds, tg.action_run)
        tg.action_status = lambda: self.calls.append("status") or "S"
        tg.action_progress = lambda: self.calls.append("progress") or "P"
        tg.action_errors = lambda: self.calls.append("errors") or "E"
        tg.action_builds = lambda: self.calls.append("builds") or "B"
        tg.action_run = lambda cid: self.calls.append("run:" + cid) or "R"

    def tearDown(self) -> None:
        (tg.action_status, tg.action_progress, tg.action_errors,
         tg.action_builds, tg.action_run) = self._orig
        tg.os.environ.clear()
        tg.os.environ.update(self._env)

    def test_buttons_and_commands_hit_the_same_actions(self) -> None:
        for text, want in (("📊 Статус", "status"), ("/status", "status"),
                           ("📈 Прогресс", "progress"), ("/progress", "progress"),
                           ("❌ Ошибки", "errors"), ("/errors", "errors"),
                           ("📦 Сборки", "builds"), ("/builds", "builds")):
            self.calls.clear()
            tg.route(text, "1")
            self.assertEqual(self.calls, [want], text)

    def test_start_and_empty_show_help_without_network(self) -> None:
        for text in ("/start", "/help", ""):
            self.calls.clear()
            self.assertIn("candy-rpm", tg.route(text, "1"))
            self.assertEqual(self.calls, [])

    def test_unknown_text_asks_for_a_button(self) -> None:
        self.assertIn("Не понял", tg.route("погода в Бурсе", "1"))
        self.assertEqual(self.calls, [])

    def test_run_passes_the_chat_id_through(self) -> None:
        tg.route("/run", "4242")
        self.assertEqual(self.calls, ["run:4242"])


class WriteGuardTests(unittest.TestCase):
    """Запуск workflow — только владельцу и только с токеном."""

    def setUp(self) -> None:
        self._env = dict(tg.os.environ)

    def tearDown(self) -> None:
        tg.os.environ.clear()
        tg.os.environ.update(self._env)

    def test_stranger_cannot_dispatch(self) -> None:
        tg.os.environ["TG_OWNER_CHAT"] = "111"
        tg.os.environ["GH_TOKEN"] = "t"
        self.assertIn("владельцу", tg.action_run("222"))

    def test_owner_without_token_gets_a_clear_refusal(self) -> None:
        tg.os.environ["TG_OWNER_CHAT"] = "111"
        tg.os.environ.pop("GH_TOKEN", None)
        self.assertIn("GH_TOKEN", tg.action_run("111"))

    def test_unset_owner_blocks_everyone(self) -> None:
        tg.os.environ.pop("TG_OWNER_CHAT", None)
        self.assertIn("владельцу", tg.action_run("111"))


class UpdateShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sent: list[dict] = []
        self._orig_call, self._orig_route = tg.tg_call, tg.route
        tg.tg_call = lambda method, **kw: self.sent.append({"m": method, **kw}) or {}
        tg.route = lambda text, chat="": f"ответ:{text}"

    def tearDown(self) -> None:
        tg.tg_call, tg.route = self._orig_call, self._orig_route

    def test_plain_message_is_answered_in_its_chat(self) -> None:
        tg.handle_update({"message": {"chat": {"id": 7}, "text": "привет"}})
        self.assertEqual(self.sent[0]["chat_id"], 7)
        self.assertEqual(self.sent[0]["text"], "ответ:привет")

    def test_callback_query_is_answered_too(self) -> None:
        tg.handle_update({"callback_query": {"data": "/status",
                                             "message": {"chat": {"id": 9}}}})
        self.assertEqual(self.sent[0]["chat_id"], 9)

    def test_update_without_chat_is_ignored(self) -> None:
        self.assertIsNone(tg.handle_update({"my_chat_member": {}}))
        self.assertEqual(self.sent, [])

    def test_reply_is_truncated_to_telegram_limit(self) -> None:
        tg.route = lambda text, chat="": "я" * 5000
        tg.handle_update({"message": {"chat": {"id": 1}, "text": "x"}})
        self.assertLessEqual(len(self.sent[0]["text"]), tg.LIMIT)


if __name__ == "__main__":
    unittest.main()
