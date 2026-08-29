#!/usr/bin/env python3
"""conftest.py — общие fixtures для тестов candy-rpm."""
import os, sys, json, pytest, tempfile, shutil, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))


def load_module(name: str, path: str) -> object:
    """Load module by path with proper sys.modules registration."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def root_dir():
    return ROOT


@pytest.fixture
def pkgs_json():
    with open(os.path.join(ROOT, "pkgs.json")) as f:
        return json.load(f)


@pytest.fixture
def state_json():
    try:
        with open(os.path.join(ROOT, "state/state.json")) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
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
        "tags": ["terminal"],
    }
