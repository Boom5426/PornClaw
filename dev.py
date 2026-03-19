from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def app_root(root: Path | None = None) -> Path:
    return (root or repo_root()) / "pornclaw"


def venv_python(app_dir: Path) -> Path:
    if os.name == "nt":
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


def runtime_dependencies_ready(python_path: Path) -> bool:
    probe = subprocess.run(
        [
            str(python_path),
            "-c",
            "import fastapi,uvicorn,jinja2,sqlalchemy,requests,bs4,multipart",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return probe.returncode == 0


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


def run_checked(cmd: list[str], cwd: Path, label: str) -> None:
    print(label)
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main(argv: list[str] | None = None, root_dir: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start PornClaw development environment")
    parser.add_argument("--skip-playwright", action="store_true", help="Skip Playwright Chromium installation")
    args = parser.parse_args(argv)

    root = root_dir or repo_root()
    app_dir = app_root(root)

    if not (app_dir / ".venv").exists():
        run_checked([sys.executable, "-m", "venv", ".venv"], app_dir, "Ensuring virtual environment")

    python_path = venv_python(app_dir)

    if needs_requirements_install(app_dir):
        try:
            run_checked(
                [str(python_path), "-m", "pip", "install", "-r", "requirements.txt"],
                app_dir,
                "Installing Python dependencies",
            )
            write_requirements_marker(app_dir)
        except subprocess.CalledProcessError:
            if not runtime_dependencies_ready(python_path):
                raise
            print(
                "Warning: dependency install failed; continuing with existing core runtime only. "
                "Optional sources may be unavailable until pip install succeeds.",
                file=sys.stderr,
            )

    run_checked([str(python_path), "scripts/init_db.py"], app_dir, "Initializing database")

    if needs_playwright_install(app_dir, skip_playwright=args.skip_playwright):
        try:
            run_checked(
                [str(python_path), "-m", "playwright", "install", "chromium"],
                app_dir,
                "Ensuring Playwright Chromium",
            )
            mark_playwright_ready(app_dir)
        except subprocess.CalledProcessError:
            print(
                "Warning: Playwright Chromium install failed; browser-backed sources may be unavailable.",
                file=sys.stderr,
            )

    run_checked(
        [str(python_path), "-m", "uvicorn", "app.main:app", "--reload"],
        app_dir,
        "Starting development server",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
