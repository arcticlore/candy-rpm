#!/usr/bin/env python3
"""test_tg_notify.py — тесты Telegram-бота."""
import os, sys, json, pytest, importlib.util, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

@pytest.fixture
def tg():
    return load_module_from_path("tg_notify", os.path.join(ROOT, "tools/tg-notify.py"))

class TestTgNotify:
    """Тесты для tg-notify.py"""

    def test_import(self, tg):
        """Модуль импортируется без ошибок"""
        assert hasattr(tg, 'T')

    def test_translations_complete(self, tg):
        """Все ключи перевода есть в обоих языках"""
        ru_keys = set(tg.T["ru"].keys())
        en_keys = set(tg.T["en"].keys())
        assert ru_keys == en_keys, f"Не совпадают ключи: ru={ru_keys-en_keys}, en={en_keys-ru_keys}"

    def test_norm_function(self, tg):
        """Нормализация текста работает корректно"""
        assert tg.norm("Hello World") == "helloworld"
        assert tg.norm("Привет Мир") == "приветмир"
        assert tg.norm("test123!@#") == "test123"
        assert tg.norm("") == ""

    def test_lang_detection(self, tg):
        """Определение языка по chat_id"""
        assert tg.L("nonexistent") == "ru"

    def test_tr_function(self, tg):
        """Функция перевода возвращает строку"""
        result = tg.tr("12345", "hello")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tr_fallback_to_ru(self, tg):
        """При отсутствии ключа — fallback на русский"""
        result = tg.tr("12345", "nonexistent_key")
        assert result == tg.T["ru"].get("nonexistent_key", "nonexistent_key")

    def test_menu_keyboard_format(self, tg):
        """Формат клавиатуры меню"""
        kb = tg.MENU_KB
        assert "keyboard" in kb
        assert "resize_keyboard" in kb
        assert kb["resize_keyboard"] is True
        assert len(kb["keyboard"]) > 0

    def test_no_secrets_in_source(self):
        """Нет захардкоженных токенов в исходниках"""
        source = open(os.path.join(ROOT, "tools/tg-notify.py")).read()
        assert "8878315859" not in source, "Токен бота захардкожен в исходниках!"
        assert "ghp_" not in source, "GitHub токен захардкожен в исходниках!"

    def test_run_function(self, tg):
        """run() выполняет команды"""
        result = tg.run("echo test123")
        assert "test123" in result

    def test_run_function_empty(self, tg):
        """run() возвращает '(пусто)' для пустого вывода"""
        result = tg.run("echo -n")
        assert result == "(пусто)" or result == ""
