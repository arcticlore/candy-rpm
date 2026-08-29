#!/usr/bin/env python3
"""test_gen_pages.py — тесты генератора веб-дашборда."""
import os, sys, json, pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def gen_pages():
    from conftest import load_module

    return load_module("gen_pages_html", os.path.join(ROOT, "bin/gen-pages-html.py"))


class TestGenPages:
    """Тесты для gen-pages-html.py"""

    def test_import(self, gen_pages):
        """Модуль импортируется без ошибок"""
        assert hasattr(gen_pages, "fetch_builds")

    def test_state_color_mapping(self, gen_pages):
        """Цвета состояний определены для всех статусов"""
        expected_states = {
            "succeeded",
            "failed",
            "running",
            "starting",
            "pending",
            "importing",
            "waiting",
            "canceled",
        }
        for state in expected_states:
            color = gen_pages.state_color(state)
            assert color.startswith("#"), f"Цвет для {state} не hex: {color}"

    def test_bar_generation(self, gen_pages):
        """Генерация прогресс-бара"""
        bar = gen_pages.progress_bar(50, 100, "test")
        assert "▓" in bar
        assert "░" in bar
        assert "50%" in bar
        assert "test" in bar

    def test_bar_zero_total(self, gen_pages):
        """Прогресс-бар с нулевым тоталом"""
        bar = gen_pages.progress_bar(0, 0, "empty")
        assert "0%" in bar

    def test_html_structure(self, root_dir):
        """Сгенерированный HTML валиден"""
        html_path = os.path.join(root_dir, "docs/index.html")
        if os.path.exists(html_path):
            with open(html_path) as f:
                html = f.read()
            assert "<!doctype html>" in html.lower() or "<!DOCTYPE html>" in html
            assert "candy-rpm" in html
            assert "ПРОЕКТ ЗАМОРОЖЕН" in html

    def test_html_has_search(self, root_dir):
        """HTML содержит поле поиска"""
        html_path = os.path.join(root_dir, "docs/index.html")
        if os.path.exists(html_path):
            with open(html_path) as f:
                html = f.read()
            assert "search" in html.lower()
            assert "filterTable" in html

    def test_no_secrets_in_html(self, root_dir):
        """Нет секретов в сгенерированном HTML"""
        html_path = os.path.join(root_dir, "docs/index.html")
        if os.path.exists(html_path):
            with open(html_path) as f:
                html = f.read()
            assert "ghp_" not in html
            assert "8878315859" not in html
