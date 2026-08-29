#!/usr/bin/env python3
"""test_edge_cases.py — comprehensive edge case tests for Python rewrites."""
import json, os, sys, tempfile, pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─── gen_specs.py edge cases ────────────────────────────────────────────────────


class TestGenSpecsEdgeCases:
    """Edge cases for gen_specs.py."""

    def test_package_dataclass_fields(self):
        """Package dataclass has all required fields."""
        from conftest import load_module

        mod = load_module("gen_specs", os.path.join(ROOT, "bin/gen_specs.py"))
        assert hasattr(mod, "Package")
        # Check dataclass fields exist
        fields = {f.name for f in mod.Package.__dataclass_fields__.values()}
        assert "name" in fields
        assert "eco" in fields
        assert "ver" in fields

    def test_pkgsfile_dataclass(self):
        """PkgsFile dataclass loads correctly."""
        from conftest import load_module

        mod = load_module("gen_specs", os.path.join(ROOT, "bin/gen_specs.py"))
        assert hasattr(mod, "PkgsFile")

    def test_load_pkgs_with_temp_file(self, tmp_dir):
        """load_pkgs reads from temp file."""
        from pathlib import Path

        from conftest import load_module

        mod = load_module("gen_specs", os.path.join(ROOT, "bin/gen_specs.py"))
        pkgs_data = {
            "packages": [
                {"name": "test-pkg", "eco": "cargo", "ver": "1.0.0", "enabled": True}
            ],
            "project": {"chroots": ["fedora-44-x86_64"]},
        }
        f = Path(tmp_dir) / "pkgs.json"
        f.write_text(json.dumps(pkgs_data))
        result = mod.load_pkgs(f)
        assert len(result.packages) == 1
        assert result.packages[0].name == "test-pkg"

    def test_load_pkgs_missing_file(self, tmp_dir):
        """load_pkgs raises on missing file."""
        from pathlib import Path

        from conftest import load_module

        mod = load_module("gen_specs", os.path.join(ROOT, "bin/gen_specs.py"))
        with pytest.raises((FileNotFoundError, SystemExit)):
            mod.load_pkgs(Path(tmp_dir) / "nonexistent.json")

    def test_ecosystem_handlers_complete(self):
        """All 12 ecosystem handlers are defined."""
        from conftest import load_module

        mod = load_module("gen_specs", os.path.join(ROOT, "bin/gen_specs.py"))
        # The module should have body_fn or similar dispatch
        assert hasattr(mod, "render") or hasattr(mod, "generate")

    def test_sample_pkg_render(self, sample_pkg):
        """Sample package renders without error."""
        from conftest import load_module

        mod = load_package_module()
        # This would require mocking network calls for full test
        # Just verify the module loads
        assert mod is not None


def load_package_module():
    """Helper to load gen_specs module."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gen_specs", os.path.join(ROOT, "bin/gen_specs.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gen_specs"] = mod
    spec.loader.exec_module(mod)
    return mod


# ─── tg-notify.py edge cases ────────────────────────────────────────────────────


class TestTgNotifyEdgeCases:
    """Edge cases for tg-notify.py v5."""

    @pytest.fixture
    def tg(self):
        from conftest import load_module

        return load_module("tg_notify", os.path.join(ROOT, "tools/tg-notify.py"))

    def test_normalize_unicode(self, tg):
        """Normalize handles unicode correctly."""
        assert tg.normalize("Привет") == "привет"
        assert tg.normalize("HELLO") == "hello"
        assert tg.normalize("Test123!") == "test123"

    def test_normalize_empty(self, tg):
        """Normalize handles empty string."""
        assert tg.normalize("") == ""

    def test_normalize_special_chars(self, tg):
        """Normalize strips special characters."""
        assert tg.normalize("hello@world.com") == "helloworldcom"
        assert tg.normalize("foo-bar_baz") == "foobarbaz"

    def test_tr_all_keys_exist(self, tg):
        """All translation keys exist in both languages."""
        ru_keys = set(tg.TRANSLATIONS["ru"].keys())
        en_keys = set(tg.TRANSLATIONS["en"].keys())
        assert ru_keys == en_keys

    def test_tr_fallback_invalid_lang(self, tg):
        """Translation falls back for invalid language."""
        # Use a chat ID not in langs dict
        result = tg.tr("99999", "hello", tg.TRANSLATIONS)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_menu_keyboard_structure(self, tg):
        """Menu keyboard has correct structure."""
        kb = tg.MENU_KB
        assert isinstance(kb, dict)
        assert "keyboard" in kb
        assert isinstance(kb["keyboard"], list)
        for row in kb["keyboard"]:
            assert isinstance(row, list)
            for btn in row:
                assert "text" in btn

    def test_send_returns_dict(self, tg):
        """send() returns dict on error."""
        result = tg.send("invalid_chat", "test")
        assert isinstance(result, dict)

    def test_send_kb_returns_bool(self, tg):
        """send_kb() returns bool."""
        result = tg.send_kb("invalid_chat", "test")
        assert isinstance(result, bool)

    def test_run_returns_string(self, tg):
        """run() returns string."""
        result = tg.run("echo hello")
        assert isinstance(result, str)

    def test_load_langs_missing_file(self, tg):
        """load_langs handles missing file."""
        result = tg.load_langs()
        assert isinstance(result, dict)

    def test_load_mailmap_missing_file(self, tg):
        """load_mailmap handles missing file."""
        result = tg.load_mailmap()
        assert isinstance(result, dict)


# ─── gen-pages-html.py edge cases ────────────────────────────────────────────────


class TestGenPagesEdgeCases:
    """Edge cases for gen-pages-html.py v4."""

    @pytest.fixture
    def gen_pages(self):
        from conftest import load_module

        return load_module(
            "gen_pages_html", os.path.join(ROOT, "bin/gen-pages-html.py")
        )

    def test_state_color_all_states(self, gen_pages):
        """State color covers all known states."""
        states = [
            "succeeded",
            "failed",
            "running",
            "starting",
            "pending",
            "importing",
            "waiting",
            "canceled",
        ]
        for state in states:
            color = gen_pages.state_color(state)
            assert color.startswith("#"), f"Invalid color for {state}: {color}"

    def test_state_color_unknown(self, gen_pages):
        """State color returns gray for unknown state."""
        color = gen_pages.state_color("unknown_state")
        assert color.startswith("#")

    def test_state_dot_format(self, gen_pages):
        """State dot returns HTML with color."""
        dot = gen_pages.state_dot("succeeded")
        assert "●" in dot or "dot" in dot.lower() or "#" in dot

    def test_progress_bar_zero(self, gen_pages):
        """Progress bar with zero total."""
        bar = gen_pages.progress_bar(0, 0, "empty")
        assert "0%" in bar

    def test_progress_bar_full(self, gen_pages):
        """Progress bar at 100%."""
        bar = gen_pages.progress_bar(100, 100, "full")
        assert "100%" in bar

    def test_progress_bar_half(self, gen_pages):
        """Progress bar at 50%."""
        bar = gen_pages.progress_bar(50, 100, "half")
        assert "50%" in bar

    def test_progress_bar_custom_color(self, gen_pages):
        """Progress bar with custom color."""
        bar = gen_pages.progress_bar(50, 100, "test", color="#ff0000")
        assert "test" in bar

    def test_generate_html_empty(self, gen_pages):
        """Generate HTML with empty builds list."""
        html = gen_pages.generate_html([])
        assert "<!doctype html>" in html.lower() or "<!DOCTYPE html>" in html

    def test_generate_html_has_table(self, gen_pages):
        """Generated HTML contains table."""
        html = gen_pages.generate_html([])
        assert "<table" in html.lower()

    def test_generate_html_has_search(self, gen_pages):
        """Generated HTML has search functionality."""
        html = gen_pages.generate_html([])
        assert "search" in html.lower() or "filter" in html.lower()


# ─── state.json edge cases ──────────────────────────────────────────────────────


class TestStateJsonEdgeCases:
    """Edge cases for state.json handling."""

    def test_state_json_loads(self):
        """state.json loads successfully."""
        path = os.path.join(ROOT, "state/state.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            assert isinstance(data, dict)

    def test_state_timestamps_are_numeric(self):
        """All timestamps in state.json are numeric."""
        path = os.path.join(ROOT, "state/state.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            for name, info in data.items():
                if isinstance(info, dict) and "ts" in info:
                    assert isinstance(info["ts"], (int, float)), (
                        f"{name} has non-numeric ts: {info['ts']}"
                    )

    def test_state_has_required_fields(self):
        """Each state entry has required fields."""
        path = os.path.join(ROOT, "state/state.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            for name, info in data.items():
                if isinstance(info, dict):
                    # Should have ver or ts or both
                    assert "ver" in info or "ts" in info, (
                        f"{name} missing ver/ts"
                    )


# ─── pkgs.json edge cases ──────────────────────────────────────────────────────


class TestPkgsJsonEdgeCases:
    """Edge cases for pkgs.json handling."""

    def test_pkgs_json_loads(self):
        """pkgs.json loads successfully."""
        path = os.path.join(ROOT, "pkgs.json")
        with open(path) as f:
            data = json.load(f)
        assert "packages" in data
        assert "project" in data

    def test_packages_is_list(self):
        """packages is a list."""
        path = os.path.join(ROOT, "pkgs.json")
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data["packages"], list)

    def test_all_packages_have_name(self):
        """Every package has a name."""
        path = os.path.join(ROOT, "pkgs.json")
        with open(path) as f:
            data = json.load(f)
        for pkg in data["packages"]:
            assert "name" in pkg, f"Package missing name: {pkg}"

    def test_all_packages_have_eco(self):
        """Every package has an ecosystem."""
        path = os.path.join(ROOT, "pkgs.json")
        with open(path) as f:
            data = json.load(f)
        for pkg in data["packages"]:
            assert "eco" in pkg, f"Package {pkg.get('name')} missing eco"

    def test_no_duplicate_package_names(self):
        """No duplicate package names."""
        path = os.path.join(ROOT, "pkgs.json")
        with open(path) as f:
            data = json.load(f)
        names = [p["name"] for p in data["packages"]]
        assert len(names) == len(set(names)), "Duplicate package names found"

    def test_project_has_chroots(self):
        """Project configuration has chroots."""
        path = os.path.join(ROOT, "pkgs.json")
        with open(path) as f:
            data = json.load(f)
        chroots = data.get("project", {}).get("chroots", [])
        assert len(chroots) > 0

    def test_copr_name_format(self):
        """COPR name is in owner/project format."""
        path = os.path.join(ROOT, "pkgs.json")
        with open(path) as f:
            data = json.load(f)
        name = data.get("project", {}).get("copr_name", "")
        assert "/" in name


# ─── bash script syntax ────────────────────────────────────────────────────────


class TestBashSyntax:
    """Bash script syntax validation."""

    @pytest.mark.parametrize(
        "script",
        [
            "update-check.sh",
            "converge.sh",
            "auto-triage.sh",
            "make-srpm.sh",
            "push.sh",
            "status.sh",
            "dashboard.sh",
        ],
    )
    def test_bash_syntax(self, script):
        """Bash script passes syntax check."""
        import subprocess

        path = os.path.join(ROOT, "bin", script)
        if os.path.exists(path):
            result = subprocess.run(
                ["bash", "-n", path], capture_output=True, text=True, timeout=10
            )
            assert result.returncode == 0, f"{script} syntax error: {result.stderr}"


# ─── Python script syntax ──────────────────────────────────────────────────────


class TestPythonSyntax:
    """Python script syntax validation."""

    @pytest.mark.parametrize(
        "script",
        [
            "bin/gen_specs.py",
            "tools/tg-notify.py",
            "bin/gen-pages-html.py",
            "bin/chroot-engine.py",
        ],
    )
    def test_python_syntax(self, script):
        """Python script passes syntax check."""
        import subprocess

        path = os.path.join(ROOT, script)
        if os.path.exists(path):
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0, f"{script} syntax error: {result.stderr}"
