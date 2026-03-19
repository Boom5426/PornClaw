from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import subprocess

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


def test_first_run_bootstraps_and_starts_server(monkeypatch, tmp_path: Path) -> None:
    dev = _load_dev_module()
    main = _require_attr(dev, "main")

    repo_root = tmp_path
    app_dir = repo_root / "pornclaw"
    (app_dir / "scripts").mkdir(parents=True)
    (app_dir / "requirements.txt").write_text("fastapi==0.115.6\n", encoding="utf-8")

    calls: list[tuple[list[str], Path, str]] = []
    monkeypatch.setattr(
        dev,
        "run_checked",
        lambda cmd, cwd, label: calls.append((cmd, cwd, label)),
        raising=False,
    )

    main(["--skip-playwright"], root_dir=repo_root)

    venv_python = app_dir / ".venv" / "bin" / "python"
    assert calls == [
        ([dev.sys.executable, "-m", "venv", ".venv"], app_dir, "Ensuring virtual environment"),
        ([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"], app_dir, "Installing Python dependencies"),
        ([str(venv_python), "scripts/init_db.py"], app_dir, "Initializing database"),
        ([str(venv_python), "-m", "uvicorn", "app.main:app", "--reload"], app_dir, "Starting development server"),
    ]


def test_playwright_failure_warns_but_does_not_block_server_start(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    dev = _load_dev_module()
    main = _require_attr(dev, "main")

    repo_root = tmp_path
    app_dir = repo_root / "pornclaw"
    (app_dir / "scripts").mkdir(parents=True)
    (app_dir / "requirements.txt").write_text("fastapi==0.115.6\n", encoding="utf-8")
    (app_dir / ".venv" / "bin").mkdir(parents=True)
    (app_dir / ".venv" / "bin" / "python").write_text("", encoding="utf-8")

    calls: list[tuple[list[str], Path, str]] = []

    def fake_run_checked(cmd, cwd, label):
        calls.append((cmd, cwd, label))
        if label == "Ensuring Playwright Chromium":
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

    monkeypatch.setattr(dev, "run_checked", fake_run_checked, raising=False)

    main([], root_dir=repo_root)

    stderr = capsys.readouterr().err.lower()
    assert "warning" in stderr
    assert any(label == "Starting development server" for _, _, label in calls)


def test_reuses_existing_environment_without_reinstalling_everything(monkeypatch, tmp_path: Path) -> None:
    dev = _load_dev_module()
    main = _require_attr(dev, "main")

    repo_root = tmp_path
    app_dir = repo_root / "pornclaw"
    (app_dir / "scripts").mkdir(parents=True)
    (app_dir / "requirements.txt").write_text("fastapi==0.115.6\n", encoding="utf-8")
    (app_dir / ".venv" / "bin").mkdir(parents=True)
    (app_dir / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    (app_dir / ".dev-state").mkdir(parents=True)
    requirements_hash = hashlib.sha256((app_dir / "requirements.txt").read_bytes()).hexdigest()
    (app_dir / ".dev-state" / "requirements.sha256").write_text(requirements_hash, encoding="utf-8")
    (app_dir / ".dev-state" / "playwright-chromium.ok").write_text("ok\n", encoding="utf-8")

    calls: list[tuple[list[str], Path, str]] = []
    monkeypatch.setattr(
        dev,
        "run_checked",
        lambda cmd, cwd, label: calls.append((cmd, cwd, label)),
        raising=False,
    )

    main([], root_dir=repo_root)

    venv_python = app_dir / ".venv" / "bin" / "python"
    assert calls == [
        ([str(venv_python), "scripts/init_db.py"], app_dir, "Initializing database"),
        ([str(venv_python), "-m", "uvicorn", "app.main:app", "--reload"], app_dir, "Starting development server"),
    ]


def test_requirements_install_failure_warns_but_can_continue_with_existing_runtime(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    dev = _load_dev_module()
    main = _require_attr(dev, "main")

    repo_root = tmp_path
    app_dir = repo_root / "pornclaw"
    (app_dir / "scripts").mkdir(parents=True)
    (app_dir / "requirements.txt").write_text("fastapi==0.115.6\ntelethon==1.42.0\n", encoding="utf-8")
    (app_dir / ".venv" / "bin").mkdir(parents=True)
    (app_dir / ".venv" / "bin" / "python").write_text("", encoding="utf-8")

    calls: list[tuple[list[str], Path, str]] = []

    def fake_run_checked(cmd, cwd, label):
        calls.append((cmd, cwd, label))
        if label == "Installing Python dependencies":
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

    monkeypatch.setattr(dev, "run_checked", fake_run_checked, raising=False)
    monkeypatch.setattr(dev, "runtime_dependencies_ready", lambda python_path: True, raising=False)

    main(["--skip-playwright"], root_dir=repo_root)

    stderr = capsys.readouterr().err.lower()
    assert "warning" in stderr
    assert any(label == "Initializing database" for _, _, label in calls)
    assert any(label == "Starting development server" for _, _, label in calls)
