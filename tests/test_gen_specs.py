#!/usr/bin/env python3
"""test_gen_specs.py — тесты генератора RPM-спеков."""
import os, sys, json, pytest, tempfile, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))

class TestGenSpecs:
    """Тесты для gen_specs.py"""

    def test_import(self):
        """Модуль импортируется без ошибок"""
        import gen_specs
        assert hasattr(gen_specs, 'main') or hasattr(gen_specs, 'generate')

    def test_ecosystem_coverage(self, pkgs_json):
        """Все экосистемы в pkgs.json поддерживаются генератором"""
        supported_ecos = {"cargo", "go", "npm", "gem", "nim", "zig",
                         "python-pkg", "python-script", "script",
                         "c-custom", "c-make", "c-cmake", "c-autotools", "meson", "custom"}
        actual_ecos = set(p.get("eco", "") for p in pkgs_json["packages"])
        unsupported = actual_ecos - supported_ecos
        assert not unsupported, f"Неподдерживаемые экосистемы: {unsupported}"

    def test_all_packages_have_required_fields(self, pkgs_json):
        """Все пакеты имеют обязательные поля"""
        required = {"name", "eco"}
        for pkg in pkgs_json["packages"]:
            if not pkg.get("enabled", True):
                continue
            missing = required - set(pkg.keys())
            assert not missing, f"Пакет {pkg.get('name')}: нет полей {missing}"

    def test_no_duplicate_names(self, pkgs_json):
        """Нет дублирующихся имён пакетов"""
        names = [p["name"] for p in pkgs_json["packages"]]
        dupes = [n for n in names if names.count(n) > 1]
        assert not dupes, f"Дублирующиеся имена: {set(dupes)}"

    def test_versions_are_strings(self, pkgs_json):
        """Версии — строки (не числа)"""
        for pkg in pkgs_json["packages"]:
            if "ver" in pkg:
                assert isinstance(pkg["ver"], str), \
                    f"Пакет {pkg['name']}: ver={pkg['ver']!r} должен быть строкой"

    def test_br_is_list(self, pkgs_json):
        """BuildRequires — список"""
        for pkg in pkgs_json["packages"]:
            if "br" in pkg:
                assert isinstance(pkg["br"], list), \
                    f"Пакет {pkg['name']}: br должен быть списком"

    def test_no_empty_names(self, pkgs_json):
        """Нет пакетов с пустым именем"""
        for pkg in pkgs_json["packages"]:
            assert pkg.get("name"), "Пакет с пустым именем"

    def test_chroots_not_empty(self, pkgs_json):
        """Список чрутов не пуст"""
        chroots = pkgs_json.get("project", {}).get("chroots", [])
        assert len(chroots) > 0, "Нет чрутов в конфигурации"

    def test_copr_name_format(self, pkgs_json):
        """Имя COPR репо в правильном формате"""
        name = pkgs_json.get("project", {}).get("copr_name", "")
        assert "/" in name, f"COPR имя должно содержать '/': {name}"
        owner, project = name.split("/", 1)
        assert owner and project, f"Неполное COPR имя: {name}"
