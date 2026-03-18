from __future__ import annotations

import hashlib
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def app_root(root: Path | None = None) -> Path:
    return (root or repo_root()) / "pornclaw"


def venv_python(app_dir: Path) -> Path:
    if Path().anchor == "\\":
        return app_dir / ".venv" / "Scripts" / "python.exe"
    return app_dir / ".venv" / "bin" / "python"


def state_dir(app_dir: Path) -> Path:
    return app_dir / ".dev-state"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def requirements_marker_path(app_dir: Path) -> Path:
    return state_dir(app_dir) / "requirements.sha256"


def playwright_marker_path(app_dir: Path) -> Path:
    return state_dir(app_dir) / "playwright-chromium.ok"


def needs_requirements_install(app_dir: Path) -> bool:
    marker = requirements_marker_path(app_dir)
    requirements = app_dir / "requirements.txt"
    if not marker.exists():
        return True
    return marker.read_text(encoding="utf-8").strip() != file_sha256(requirements)


def write_requirements_marker(app_dir: Path) -> None:
    state_dir(app_dir).mkdir(parents=True, exist_ok=True)
    requirements_marker_path(app_dir).write_text(
        file_sha256(app_dir / "requirements.txt"),
        encoding="utf-8",
    )


def needs_playwright_install(app_dir: Path, skip_playwright: bool) -> bool:
    if skip_playwright:
        return False
    return not playwright_marker_path(app_dir).exists()


def mark_playwright_ready(app_dir: Path) -> None:
    state_dir(app_dir).mkdir(parents=True, exist_ok=True)
    playwright_marker_path(app_dir).write_text("ok\n", encoding="utf-8")
