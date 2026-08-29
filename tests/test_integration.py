#!/usr/bin/env python3
"""test_integration.py — интеграционные тесты пайплайна."""
import os, sys, json, pytest, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestIntegration:
    """Интеграционные тесты"""

    def test_bash_syntax_all_scripts(self):
        """Все bash скрипты проходят проверку синтаксиса"""
        scripts_dir = os.path.join(ROOT, "bin")
        errors = []
        for f in os.listdir(scripts_dir):
            if f.endswith('.sh'):
                path = os.path.join(scripts_dir, f)
                result = subprocess.run(
                    ['bash', '-n', path],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0:
                    errors.append(f"{f}: {result.stderr.strip()}")
        assert not errors, f"Ошибки синтаксиса:\n" + "\n".join(errors)

    def test_python_syntax_all_scripts(self):
        """Все Python скрипты проходят проверку синтаксиса"""
        errors = []
        for subdir in ['bin', 'tools']:
            scripts_dir = os.path.join(ROOT, subdir)
            if not os.path.exists(scripts_dir):
                continue
            for f in os.listdir(scripts_dir):
                if f.endswith('.py'):
                    path = os.path.join(scripts_dir, f)
                    result = subprocess.run(
                        [sys.executable, '-m', 'py_compile', path],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode != 0:
                        errors.append(f"{subdir}/{f}: {result.stderr.strip()}")
        assert not errors, f"Ошибки синтаксиса:\n" + "\n".join(errors)

    def test_pkgs_json_valid(self):
        """pkgs.json — валидный JSON"""
        path = os.path.join(ROOT, "pkgs.json")
        data = json.load(open(path))
        assert "packages" in data
        assert "project" in data
        assert isinstance(data["packages"], list)

    def test_state_json_valid(self):
        """state.json — валидный JSON"""
        path = os.path.join(ROOT, "state/state.json")
        if os.path.exists(path):
            data = json.load(open(path))
            assert isinstance(data, dict)

    def test_all_specs_generated(self):
        """Для каждого включённого пакета есть спек"""
        pkgs = json.load(open(os.path.join(ROOT, "pkgs.json")))
        specs_dir = os.path.join(ROOT, "SPECS")
        missing = []
        for pkg in pkgs["packages"]:
            if not pkg.get("enabled", True):
                continue
            spec_path = os.path.join(specs_dir, f"{pkg['name']}.spec")
            if not os.path.exists(spec_path):
                missing.append(pkg["name"])
        assert not missing, f"Нет спек для: {missing[:10]}..."

    def test_specs_have_changelog(self):
        """Все спеки имеют %changelog"""
        specs_dir = os.path.join(ROOT, "SPECS")
        missing = []
        for f in os.listdir(specs_dir):
            if f.endswith('.spec'):
                content = open(os.path.join(specs_dir, f)).read()
                if '%changelog' not in content:
                    missing.append(f)
        assert not missing, f"Спеки без %changelog: {missing[:10]}..."

    def test_specs_have_license(self):
        """Все спеки устанавливают лицензию"""
        specs_dir = os.path.join(ROOT, "SPECS")
        missing = []
        for f in os.listdir(specs_dir):
            if f.endswith('.spec'):
                content = open(os.path.join(specs_dir, f)).read()
                if '_licensedir' not in content and 'LICENSE' not in content:
                    missing.append(f)
        assert not missing, f"Спеки без лицензии: {missing[:10]}..."

    def test_no_source_urls_with_secrets(self):
        """Source URL не содержат секретов"""
        specs_dir = os.path.join(ROOT, "SPECS")
        for f in os.listdir(specs_dir):
            if f.endswith('.spec'):
                content = open(os.path.join(specs_dir, f)).read()
                assert "ghp_" not in content, f"Токен в {f}"
                assert "8878315859" not in content, f"TG токен в {f}"

    def test_status_script_syntax(self):
        """status.sh проходит проверку синтаксиса"""
        result = subprocess.run(
            ['bash', '-n', os.path.join(ROOT, 'bin/status.sh')],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0

    def test_dashboard_script_syntax(self):
        """dashboard.sh проходит проверку синтаксиса"""
        result = subprocess.run(
            ['bash', '-n', os.path.join(ROOT, 'bin/dashboard.sh')],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0

    def test_converge_script_syntax(self):
        """converge.sh проходит проверку синтаксиса"""
        result = subprocess.run(
            ['bash', '-n', os.path.join(ROOT, 'bin/converge.sh')],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0

    def test_auto_triage_script_syntax(self):
        """auto-triage.sh проходит проверку синтаксиса"""
        result = subprocess.run(
            ['bash', '-n', os.path.join(ROOT, 'bin/auto-triage.sh')],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0

    def test_update_check_script_syntax(self):
        """update-check.sh проходит проверку синтаксиса"""
        result = subprocess.run(
            ['bash', '-n', os.path.join(ROOT, 'bin/update-check.sh')],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0

    def test_push_script_syntax(self):
        """push.sh проходит проверку синтаксиса"""
        result = subprocess.run(
            ['bash', '-n', os.path.join(ROOT, 'bin/push.sh')],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
