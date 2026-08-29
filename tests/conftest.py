#!/usr/bin/env python3
"""conftest.py — общие fixtures для тестов candy-rpm."""
import os, sys, json, pytest, tempfile, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))

@pytest.fixture
def root_dir():
    return ROOT

@pytest.fixture
def pkgs_json():
    return json.load(open(os.path.join(ROOT, "pkgs.json")))

@pytest.fixture
def state_json():
    try:
        return json.load(open(os.path.join(ROOT, "state/state.json")))
    except Exception:
        return {}

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)

@pytest.fixture
def sample_pkg():
    return {
        "name": "test-pkg",
        "eco": "cargo",
        "ver": "1.0.0",
        "enabled": True,
        "prio": 5,
        "br": ["gcc", "gcc-c++"],
        "src": "https://github.com/test/test/archive/refs/tags/1.0.0.tar.gz",
        "bins": ["test-pkg"],
        "tags": ["terminal"]
    }
