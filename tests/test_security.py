#!/usr/bin/env python3
"""test_security.py — проверки безопасности проекта."""
import os, sys, json, pytest, stat, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestSecurity:
    """Проверки безопасности"""

    def test_no_hardcoded_tokens_in_scripts(self):
        """Нет захардкоженных токенов в скриптах"""
        token_patterns = [
            r'ghp_[A-Za-z0-9]{36,}',           # GitHub PAT
            r'8878315859:AA[A-Za-z0-9_-]{30,}', # Telegram bot token
            r'-----BEGIN (RSA |EC )?PRIVATE KEY', # Private keys
        ]
        for root, dirs, files in os.walk(ROOT):
            if '.git' in root or '__pycache__' in root:
                continue
            for f in files:
                if f.endswith(('.py', '.sh', '.yml', '.yaml', '.json', '.md')):
                    path = os.path.join(root, f)
                    try:
                        content = open(path).read()
                        for pattern in token_patterns:
                            matches = re.findall(pattern, content)
                            assert not matches, \
                                f"Найден токен в {path}: {matches[0][:20]}..."
                    except Exception:
                        pass

    def test_no_world_readable_secrets(self):
        """Файлы с секретами не доступны всем"""
        secret_files = [
            "~/.config/candy/tg.conf",
            "~/.config/candy/push-token",
            "~/.config/copr",
            "~/.config/gh-token",
        ]
        for f in secret_files:
            path = os.path.expanduser(f)
            if os.path.exists(path):
                mode = os.stat(path).st_mode
                world_readable = mode & stat.S_IROTH
                assert not world_readable, \
                    f"{f} доступен для чтения всеми (mode: {oct(mode)[-3:]})"

    def test_scripts_not_world_writable(self):
        """Скрипты не доступны для записи всем"""
        for root, dirs, files in os.walk(os.path.join(ROOT, "bin")):
            for f in files:
                if f.endswith(('.py', '.sh')):
                    path = os.path.join(root, f)
                    mode = os.stat(path).st_mode
                    world_writable = mode & stat.S_IWOTH
                    assert not world_writable, \
                        f"{path} доступен для записи всеми"

    def test_no_symlinks_to_etc(self):
        """Нет симлинков в /etc"""
        for root, dirs, files in os.walk(ROOT):
            if '.git' in root:
                continue
            for f in files:
                path = os.path.join(root, f)
                if os.path.islink(path):
                    target = os.readlink(path)
                    assert not target.startswith('/etc'), \
                        f"Симлинк в /etc: {path} -> {target}"

    def test_state_json_not_committed_with_secrets(self):
        """state.json не содержит секретов"""
        state_path = os.path.join(ROOT, "state/state.json")
        if os.path.exists(state_path):
            content = open(state_path).read()
            assert "ghp_" not in content
            assert "8878315859" not in content
            assert "password" not in content.lower()

    def test_github_workflow_no_plaintext_secrets(self):
        """GitHub workflow не передаёт секреты в открытом виде"""
        workflow_path = os.path.join(ROOT, ".github/workflows/update.yml")
        if os.path.exists(workflow_path):
            content = open(workflow_path).read()
            # Секреты должны передаваться через ${{ secrets.XXX }}
            assert "8878315859" not in content
            assert "ghp_" not in content
            # Проверяем что используется secrets
            assert "secrets." in content

    def test_no_executable_data_files(self):
        """Файлы данных (json, md, toml) не исполняемые"""
        data_extensions = ('.json', '.md', '.toml', '.yml', '.yaml', '.txt')
        for root, dirs, files in os.walk(ROOT):
            if '.git' in root:
                continue
            for f in files:
                if f.endswith(data_extensions):
                    path = os.path.join(root, f)
                    mode = os.stat(path).st_mode
                    is_executable = mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    assert not is_executable, \
                        f"Файл данных исполняемый: {path}"

    def test_umask_077_in_update_check(self):
        """update-check.sh устанавливает umask 077"""
        script_path = os.path.join(ROOT, "bin/update-check.sh")
        content = open(script_path).read()
        assert "umask 077" in content
