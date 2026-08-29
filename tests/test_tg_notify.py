#!/usr/bin/env python3
"""test_tg_notify.py — тесты Telegram-бота v5."""
import os, sys, json, pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def tg():
    from conftest import load_module

    return load_module("tg_notify", os.path.join(ROOT, "tools/tg-notify.py"))


class TestTgNotify:
    """Тесты для tg-notify.py v5"""

    def test_import(self, tg):
        """Модуль импортируется без ошибок"""
        assert hasattr(tg, "TRANSLATIONS")

    def test_translations_complete(self, tg):
        """Все ключи перевода есть в обоих языках"""
        ru_keys = set(tg.TRANSLATIONS["ru"].keys())
        en_keys = set(tg.TRANSLATIONS["en"].keys())
        assert ru_keys == en_keys, (
            f"Не совпадают ключи: ru={ru_keys - en_keys}, en={en_keys - ru_keys}"
        )

    def test_normalize_function(self, tg):
        """Нормализация текста работает корректно"""
        assert tg.normalize("Hello World") == "helloworld"
        assert tg.normalize("Привет Мир") == "приветмир"
        assert tg.normalize("test123!@#") == "test123"
        assert tg.normalize("") == ""

    def test_get_lang_default(self, tg):
        """Язык по умолчанию — ru"""
        assert tg.get_lang("nonexistent", {}) == "ru"

    def test_get_lang_custom(self, tg):
        """Пользовательский язык"""
        assert tg.get_lang("12345", {"12345": "en"}) == "en"

    def test_tr_function(self, tg):
        """Функция перевода возвращает строку"""
        result = tg.tr("12345", "hello", tg.TRANSLATIONS)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tr_fallback_to_ru(self, tg):
        """При отсутствии ключа — fallback на русский"""
        result = tg.tr("12345", "nonexistent_key", tg.TRANSLATIONS)
        assert result == tg.TRANSLATIONS["ru"].get("nonexistent_key", "nonexistent_key")

    def test_tr_english(self, tg):
        """Перевод на английский"""
        result = tg.tr("99999", "hello", {"99999": "en"})
        assert "Bot" in result or "arcticlore" in result

    def test_menu_keyboard_format(self, tg):
        """Формат клавиатуры меню"""
        kb = tg.MENU_KB
        assert "keyboard" in kb
        assert "resize_keyboard" in kb
        assert kb["resize_keyboard"] is True
        assert len(kb["keyboard"]) > 0

    def test_menu_keyboard_has_required_buttons(self, tg):
        """Клавиатура содержит все кнопки"""
        flat = [btn["text"] for row in tg.MENU_KB["keyboard"] for btn in row]
        assert "📊 Статус" in flat
        assert "📈 Прогресс" in flat
        assert "❌ Ошибки" in flat
        assert "🌅 Отчёт" in flat

    def test_no_secrets_in_source(self):
        """Нет захардкоженных токенов в исходниках"""
        with open(os.path.join(ROOT, "tools/tg-notify.py")) as f:
            source = f.read()
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

    def test_load_config_missing(self, tg):
        """load_config не падает при отсутствии конфига"""
        tg.load_config()  # Should not raise

    def test_load_langs_missing(self, tg):
        """load_langs возвращает пустой dict при отсутствии файла"""
        result = tg.load_langs()
        assert isinstance(result, dict)

    def test_load_mailmap_missing(self, tg):
        """load_mailmap возвращает пустой dict при отсутствии файла"""
        result = tg.load_mailmap()
        assert isinstance(result, dict)
