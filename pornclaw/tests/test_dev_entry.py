from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_dev_module():
    dev_path = _repo_root() / "dev.py"
    if not dev_path.exists():
        pytest.fail(f"Expected repo-root dev entrypoint at {dev_path}")

    spec = importlib.util.spec_from_file_location("dev", dev_path)
    if spec is None or spec.loader is None:
        pytest.fail(f"Could not load dev module from {dev_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _require_attr(module, name: str):
    if not hasattr(module, name):
        pytest.fail(f"Expected dev.py to define {name}()")
    return getattr(module, name)


def test_requirements_install_needed_when_hash_file_missing(tmp_path: Path) -> None:
    dev = _load_dev_module()
    needs_requirements_install = _require_attr(dev, "needs_requirements_install")

    app_dir = tmp_path / "pornclaw"
    app_dir.mkdir()
    (app_dir / "requirements.txt").write_text("fastapi==0.115.6\n", encoding="utf-8")

    assert needs_requirements_install(app_dir) is True


def test_requirements_install_skipped_when_hash_matches(tmp_path: Path) -> None:
    dev = _load_dev_module()
    needs_requirements_install = _require_attr(dev, "needs_requirements_install")
    requirements_marker_path = _require_attr(dev, "requirements_marker_path")
    state_dir = _require_attr(dev, "state_dir")

    app_dir = tmp_path / "pornclaw"
    app_dir.mkdir()
    requirements = app_dir / "requirements.txt"
    contents = "fastapi==0.115.6\n"
    requirements.write_text(contents, encoding="utf-8")

    state_dir(app_dir).mkdir(parents=True, exist_ok=True)
    requirements_marker_path(app_dir).write_text(
        hashlib.sha256(contents.encode("utf-8")).hexdigest(),
        encoding="utf-8",
    )

    assert needs_requirements_install(app_dir) is False


def test_skip_playwright_disables_browser_install_branch(tmp_path: Path) -> None:
    dev = _load_dev_module()
    needs_playwright_install = _require_attr(dev, "needs_playwright_install")

    app_dir = tmp_path / "pornclaw"
    app_dir.mkdir()

    assert needs_playwright_install(app_dir, skip_playwright=True) is False
