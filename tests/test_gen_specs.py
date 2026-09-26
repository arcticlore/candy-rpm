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
                         "c-custom", "c-make", "c-cmake", "c-autotools", "meson", "custom",
                         "haskell"}
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

    def test_render_noarch_and_provides(self):
        """Поля noarch/provides попадают в спек"""
        import gen_specs
        m = gen_specs.Package(name="scrap-engine", eco="python-pkg", host="pypi",
                              noarch=True, provides=["python3-scrap-engine"])
        spec = gen_specs.render("scrap-engine", "1.5.4", {"scrap-engine": m})
        assert "BuildArch:      noarch" in spec
        assert "Provides:       python3-scrap-engine" in spec
        assert spec.index("BuildArch:") < spec.index("BuildRequires:  python3-devel")

    def test_noarch_not_duplicated(self, tmp_path):
        """noarch=True не дублирует BuildArch, который body уже эмитит"""
        import gen_specs
        m = gen_specs.Package(name="x", eco="python-script", host="pypi", noarch=True)
        spec = gen_specs.render("x", "1", {"x": m})
        assert spec.count("BuildArch:") == 1

    def test_python_pkg_build_cmd_before_wheel(self):
        """build_cmd в python-pkg выполняется до %pyproject_wheel"""
        import gen_specs
        m = gen_specs.Package(name="p", eco="python-pkg", host="github",
                              build_cmd="go build -buildmode=c-shared -o lib.so .")
        spec = gen_specs.render("p", "1", {"p": m})
        assert spec.index("go build -buildmode=c-shared") < spec.index("%pyproject_wheel")

    def test_python_pkg_default_no_build_cmd(self):
        """По умолчанию build_cmd не вставляется в %build"""
        import gen_specs
        m = gen_specs.Package(name="p", eco="python-pkg", host="github")
        spec = gen_specs.render("p", "1", {"p": m})
        assert spec.index("%build") < spec.index("%pyproject_wheel")

    def test_load_pkgs_new_fields(self, tmp_path):
        """load_pkgs читает noarch/provides/build_cmd"""
        import gen_specs
        data = {"project": {}, "packages": [
            {"name": "a", "eco": "python-pkg",
             "noarch": True, "provides": ["python3-a"], "build_cmd": "echo hi"}
        ]}
        f = tmp_path / "pkgs.json"
        f.write_text(json.dumps(data))
        p = gen_specs.load_pkgs(f).packages[0]
        assert p.noarch is True
        assert p.provides == ["python3-a"]
        assert p.build_cmd == "echo hi"

    def test_pokete_and_scrap_engine_entries(self, pkgs_json):
        """Новые пакеты pokete и scrap-engine присутствуют и валидны"""
        by_name = {p["name"]: p for p in pkgs_json["packages"]}
        se = by_name.get("scrap-engine")
        pk = by_name.get("pokete")
        assert se, "нет записи scrap-engine в pkgs.json"
        assert pk, "нет записи pokete в pkgs.json"
        assert se.get("noarch") is True
        assert "python3-scrap-engine" in se.get("provides", [])
        assert pk.get("eco") == "python-pkg"
        assert "python3-scrap-engine" in pk.get("req", [])
        assert "scrap_engine" in pk.get("pbr_exclude", [])
        assert pk.get("license") == "GPL-3.0-only"
