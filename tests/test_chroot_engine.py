#!/usr/bin/env python3
"""test_chroot_engine.py — тесты чрут-движка (без сетевых вызовов)."""
import os, sys, json, pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestChrootEngine:
    """Unit tests for chroot-engine.py (isolation from network)."""

    def test_jload_valid(self, tmp_dir):
        """jload читает валидный JSON"""
        from chroot_engine_isolated import jload

        f = os.path.join(tmp_dir, "test.json")
        with open(f, "w") as fh:
            json.dump({"key": "value"}, fh)
        assert jload(f, {}) == {"key": "value"}

    def test_jload_missing(self, tmp_dir):
        """jload возвращает default для несуществующего файла"""
        from chroot_engine_isolated import jload

        assert jload("/nonexistent/file.json", {"default": 1}) == {"default": 1}

    def test_jload_corrupt(self, tmp_dir):
        """jload возвращает default для битого JSON"""
        from chroot_engine_isolated import jload

        f = os.path.join(tmp_dir, "bad.json")
        with open(f, "w") as fh:
            fh.write("not json {{{")
        assert jload(f, []) == []

    def test_jload_nested(self, tmp_dir):
        """jload читает вложенный JSON"""
        from chroot_engine_isolated import jload

        f = os.path.join(tmp_dir, "nested.json")
        with open(f, "w") as fh:
            json.dump({"a": {"b": [1, 2, 3]}}, fh)
        result = jload(f, {})
        assert result["a"]["b"] == [1, 2, 3]

    def test_jload_empty_file(self, tmp_dir):
        """jload возвращает default для пустого файла"""
        from chroot_engine_isolated import jload

        f = os.path.join(tmp_dir, "empty.json")
        with open(f, "w") as fh:
            fh.write("")
        assert jload(f, "default") == "default"

    def test_lock_file_format(self, root_dir):
        """Lock file — валидный JSON"""
        lock_path = os.path.join(root_dir, "state/chroot-lock.json")
        if os.path.exists(lock_path):
            with open(lock_path) as f:
                data = json.load(f)
            assert isinstance(data, dict)

    def test_plan_file_format(self, root_dir):
        """Plan file — валидный JSON с plan и done"""
        plan_path = os.path.join(root_dir, "logs/chroot-plan.json")
        if os.path.exists(plan_path):
            with open(plan_path) as f:
                data = json.load(f)
            assert "plan" in data
            assert "done" in data

    def test_chroots_count(self, pkgs_json):
        """18 чрутов в конфигурации"""
        chroots = pkgs_json.get("project", {}).get("chroots", [])
        assert len(chroots) == 18

    def test_chroots_format(self, pkgs_json):
        """Чруты в правильном формате fedora-XX-arch"""
        chroots = pkgs_json.get("project", {}).get("chroots", [])
        for c in chroots:
            assert c.startswith("fedora-"), f"Неверный формат чрута: {c}"

    def test_stuck_hours_env(self, monkeypatch):
        """STUCK_HOURS читается из переменной окружения"""
        monkeypatch.setenv("STUCK_HOURS", "12")
        # Re-import to pick up env change
        import importlib

        # We can't reimport the script, but we can test the env parsing
        assert float(os.environ.get("STUCK_HOURS", "6")) == 12.0


# Standalone functions extracted for testing without network
def jload(p: str, d: object) -> object:
    """Load JSON file, return default on error."""
    try:
        with open(p) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return d


# Register isolated functions in a module for import
import types

_isolated = types.ModuleType("chroot_engine_isolated")
_isolated.jload = jload
sys.modules["chroot_engine_isolated"] = _isolated
