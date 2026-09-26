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
        """load_pkgs читает noarch/provides/build_cmd/cmake_args"""
        import gen_specs
        data = {"project": {}, "packages": [
            {"name": "a", "eco": "python-pkg",
             "noarch": True, "provides": ["python3-a"], "build_cmd": "echo hi"},
            {"name": "b", "eco": "c-cmake",
             "cmake_args": "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"}
        ]}
        f = tmp_path / "pkgs.json"
        f.write_text(json.dumps(data))
        pkgs = gen_specs.load_pkgs(f).packages
        assert pkgs[0].noarch is True
        assert pkgs[0].provides == ["python3-a"]
        assert pkgs[0].build_cmd == "echo hi"
        assert pkgs[1].cmake_args == "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"

    def test_cmake_args_rendered_in_c_cmake(self):
        """cmake_args попадает в строку %cmake eco c-cmake"""
        import gen_specs
        m = gen_specs.Package(name="d", eco="c-cmake", host="github",
                              cmake_args="-DCMAKE_POLICY_VERSION_MINIMUM=3.5")
        spec = gen_specs.render("d", "1", {"d": m})
        assert "%cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5\n" in spec
        m2 = gen_specs.Package(name="d", eco="c-cmake", host="github")
        spec2 = gen_specs.render("d", "1", {"d": m2})
        assert "\n%cmake\n" in spec2

    def test_diagon_reenabled_cmake_policy(self, pkgs_json):
        """diagon: включён, git-core, cmake policy fix, antlr source override"""
        by_name = {p["name"]: p for p in pkgs_json["packages"]}
        d = by_name.get("diagon")
        assert d, "нет записи diagon"
        assert d.get("enabled") not in (False, "false")
        assert "git-core" in d.get("br", [])
        assert "curl" in d.get("br", [])
        assert "CMAKE_POLICY_VERSION_MINIMUM" in d.get("cmake_args", "")
        assert "FETCHCONTENT_SOURCE_DIR_ANTLR" in d.get("cmake_args", "")
        pe = d.get("prep_extra", "")
        assert "archive/1cb4669f84cea5b59661fd44b0f80509fdacd3f9.tar.gz" in pe
        assert "antlr4-1cb4669f84cea5b59661fd44b0f80509fdacd3f9/runtime/Cpp/CMakeLists.txt" in pe
        assert "CMAKE_POLICY" in pe and "OLD" in pe
        assert d.get("topdir") == "Diagon-1.1.158"
        assert d.get("eco") == "c-cmake"
        assert d.get("license") == "MIT"

    def test_diagon_spec_content(self):
        """Сгенерированный спек diagon содержит git-core, policy fix, antlr override"""
        import gen_specs
        pkgs = gen_specs.load_pkgs(gen_specs.Path(gen_specs.__file__).resolve().parent.parent / "pkgs.json")
        meta = {p.name: p for p in pkgs.packages}
        spec = gen_specs.render("diagon", "1.1.158", meta)
        assert "BuildRequires:  git-core" in spec
        assert "%cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DFETCHCONTENT_SOURCE_DIR_ANTLR=" in spec
        assert "curl -sL https://github.com/antlr/antlr4/archive/" in spec
        assert "sed -i -E '/CMAKE_POLICY" in spec

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
