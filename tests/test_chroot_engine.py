#!/usr/bin/env python3
"""test_chroot_engine.py — тесты чрут-движка."""
import os, sys, json, pytest, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_module_from_path(name, path):
    """Загружает модуль по пути (для файлов с дефисами)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

@pytest.fixture
def engine():
    return load_module_from_path("chroot_engine", os.path.join(ROOT, "bin/chroot-engine.py"))

class TestChrootEngine:
    """Тесты для chroot-engine.py"""

    def test_import(self, engine):
        """Модуль импортируется без ошибок"""
        assert hasattr(engine, 'jload')

    def test_jload_valid(self, engine, tmp_dir):
        """jload читает валидный JSON"""
        f = os.path.join(tmp_dir, "test.json")
        json.dump({"key": "value"}, open(f, "w"))
        assert engine.jload(f, {}) == {"key": "value"}

    def test_jload_missing(self, engine, tmp_dir):
        """jload возвращает default для несуществующего файла"""
        assert engine.jload("/nonexistent/file.json", {"default": 1}) == {"default": 1}

    def test_jload_corrupt(self, engine, tmp_dir):
        """jload возвращает default для битого JSON"""
        f = os.path.join(tmp_dir, "bad.json")
        open(f, "w").write("not json {{{")
        assert engine.jload(f, []) == []

    def test_http_text_timeout(self, engine):
        """http_text возвращает пустую строку при таймауте"""
        result = engine.http_text("https://192.0.2.1/nonexistent")
        assert result == ""

    def test_lock_file_format(self, engine, root_dir):
        """Lock file — валидный JSON"""
        lock_path = os.path.join(root_dir, "state/chroot-lock.json")
        if os.path.exists(lock_path):
            data = json.load(open(lock_path))
            assert isinstance(data, dict)

    def test_plan_file_format(self, engine, root_dir):
        """Plan file — валидный JSON с plan и done"""
        plan_path = os.path.join(root_dir, "logs/chroot-plan.json")
        if os.path.exists(plan_path):
            data = json.load(open(plan_path))
            assert "plan" in data
            assert "done" in data

    def test_stuck_hours_default(self, engine):
        """STUCK_HOURS по умолчанию = 6"""
        assert engine.STUCK_HOURS == 6.0

    def test_chroots_from_pkgs(self, engine, pkgs_json):
        """Чруты берутся из pkgs.json"""
        expected = pkgs_json.get("project", {}).get("chroots", [])
        assert engine.CHROOTS == expected
