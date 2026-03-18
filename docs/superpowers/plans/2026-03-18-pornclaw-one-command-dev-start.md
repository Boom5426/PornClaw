# PornClaw One-Command Dev Start Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repo-root `python dev.py` entrypoint that bootstraps the local development environment on first run, reuses it on later runs, and starts the FastAPI app with a single command.

**Architecture:** Keep the current FastAPI app and `pornclaw/` layout unchanged. Add a thin root-level `dev.py` coordinator that resolves paths, manages `pornclaw/.venv`, tracks lightweight bootstrap state in `pornclaw/.dev-state/`, invokes `scripts/init_db.py`, optionally installs Playwright Chromium, and finally starts `uvicorn app.main:app --reload`. Make the coordinator function-based so tests can validate orchestration without creating real virtualenvs or installing browsers.

**Tech Stack:** Python 3.11, argparse, subprocess, pathlib, hashlib, JSON/text state files, pytest, monkeypatch

---

## Files and Responsibilities

- `dev.py`
  - Repo-root one-command development entrypoint.
  - Resolves repository paths, parses CLI flags, and orchestrates setup/startup.
- `.gitignore`
  - Ignore the new repo-local bootstrap state directory.
- `pornclaw/tests/conftest.py`
  - Ensure tests can import the repo-root `dev.py`.
- `pornclaw/tests/test_dev_entry.py`
  - Unit tests for dependency hash checks, Playwright behavior, and startup command orchestration.
- `README.md`
  - Replace the multi-command startup path with `python dev.py` as the primary recommendation.
- `pornclaw/README.md`
  - Mirror the same single-command dev-start guidance and keep the manual fallback path.

## Chunk 1: Test Harness and Bootstrap State

### Task 1: Make the root entry testable and define bootstrap state

**Files:**
- Modify: `.gitignore`
- Modify: `pornclaw/tests/conftest.py`
- Create: `pornclaw/tests/test_dev_entry.py`

- [ ] **Step 1: Ignore the bootstrap state directory**

Add a repo-local ignore entry for the new state directory:

```gitignore
pornclaw/.dev-state/
```

- [ ] **Step 2: Extend the test import path to include the repo root**

Update `pornclaw/tests/conftest.py` so tests can import `dev.py` from the repository root, not just from `pornclaw/`.

- [ ] **Step 3: Write failing tests for bootstrap-state decisions**

Add tests like:

```python
def test_requirements_install_needed_when_hash_file_missing(tmp_path):
    state_dir = tmp_path / ".dev-state"
    assert needs_requirements_install(requirements_file, state_dir) is True


def test_requirements_install_skipped_when_hash_matches(tmp_path):
    write_hash_marker(...)
    assert needs_requirements_install(requirements_file, state_dir) is False
```

Also add a test that `--skip-playwright` disables the Playwright install branch.

- [ ] **Step 4: Run the new test module and confirm it fails for the intended reasons**

Run:

```bash
cd /data/boom/Agent/PornClaw/pornclaw
pytest tests/test_dev_entry.py -v
```

Expected: failures show that `dev.py` and its helper functions do not exist yet.

- [ ] **Step 5: Commit only if the scaffolding itself needs a standalone commit**

```bash
git add .gitignore pornclaw/tests/conftest.py pornclaw/tests/test_dev_entry.py
git commit -m "test: add scaffolding for dev entrypoint"
```

Only commit here if the team prefers test harness changes separated from implementation.

## Chunk 2: Core Coordinator and Orchestration

### Task 2: Implement the root `dev.py` helper functions

**Files:**
- Create: `dev.py`
- Test: `pornclaw/tests/test_dev_entry.py`

- [ ] **Step 1: Implement path and interpreter helpers**

Add small functions such as:

```python
def repo_root() -> Path: ...
def app_root() -> Path: ...
def venv_python(app_dir: Path) -> Path: ...
def state_dir(app_dir: Path) -> Path: ...
```

- [ ] **Step 2: Implement requirement-hash state helpers**

Use a stable file under `pornclaw/.dev-state/`, for example:

```text
pornclaw/.dev-state/requirements.sha256
```

Implement helpers such as:

```python
def file_sha256(path: Path) -> str: ...
def requirements_marker_path(app_dir: Path) -> Path: ...
def needs_requirements_install(app_dir: Path) -> bool: ...
def write_requirements_marker(app_dir: Path) -> None: ...
```

- [ ] **Step 3: Implement the Playwright marker helpers**

Use a marker file such as:

```text
pornclaw/.dev-state/playwright-chromium.ok
```

Implement helpers such as:

```python
def playwright_marker_path(app_dir: Path) -> Path: ...
def needs_playwright_install(app_dir: Path, skip_playwright: bool) -> bool: ...
def mark_playwright_ready(app_dir: Path) -> None: ...
```

- [ ] **Step 4: Re-run the focused helper tests**

Run:

```bash
cd /data/boom/Agent/PornClaw/pornclaw
pytest tests/test_dev_entry.py -v
```

Expected: helper-oriented tests now pass, but orchestration tests should still fail if they were added up front.

- [ ] **Step 5: Commit the helper slice**

```bash
git add dev.py pornclaw/tests/test_dev_entry.py .gitignore pornclaw/tests/conftest.py
git commit -m "feat: add dev bootstrap state helpers"
```

### Task 3: Add failing orchestration tests for environment setup and startup flow

**Files:**
- Modify: `pornclaw/tests/test_dev_entry.py`

- [ ] **Step 1: Write a failing test for first-run orchestration**

Add a test like:

```python
def test_first_run_bootstraps_and_starts_server(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(dev, "run_checked", lambda cmd, cwd=None, label=None: calls.append((cmd, cwd, label)))
    dev.main(["--skip-playwright"], repo_root=tmp_path)
    assert calls == [
        ([sys.executable, "-m", "venv", ".venv"], app_dir, "Ensuring virtual environment"),
        ([venv_python, "-m", "pip", "install", "-r", "requirements.txt"], app_dir, "Installing Python dependencies"),
        ([venv_python, "scripts/init_db.py"], app_dir, "Initializing database"),
        ([venv_python, "-m", "uvicorn", "app.main:app", "--reload"], app_dir, "Starting development server"),
    ]
```

- [ ] **Step 2: Write a failing test for Playwright install failure softening**

Add a test like:

```python
def test_playwright_failure_warns_but_does_not_block_server_start(monkeypatch, capsys, tmp_path):
    ...
    assert "warning" in capsys.readouterr().err.lower()
    assert uvicorn_call_was_still_made
```

- [ ] **Step 3: Write a failing test for reusing an existing environment**

Add a test that verifies:

- existing `.venv` skips venv creation
- matching requirements hash skips `pip install`
- existing Playwright marker skips browser install

- [ ] **Step 4: Run the orchestration tests and confirm they fail**

Run:

```bash
cd /data/boom/Agent/PornClaw/pornclaw
pytest tests/test_dev_entry.py -v
```

Expected: failures point to missing orchestration behavior, not import errors.

## Chunk 3: Startup Flow and Documentation

### Task 4: Implement the full `dev.py` startup sequence

**Files:**
- Modify: `dev.py`
- Test: `pornclaw/tests/test_dev_entry.py`

- [ ] **Step 1: Add a small command runner wrapper**

Implement a wrapper such as:

```python
def run_checked(cmd: list[str], cwd: Path, label: str) -> None:
    print(label)
    subprocess.run(cmd, cwd=str(cwd), check=True)
```

Keep it narrow so tests can monkeypatch it easily.

- [ ] **Step 2: Implement the venv bootstrap logic**

The startup flow should:

- create `pornclaw/.venv` only when missing
- use the venv’s Python for all later commands
- ensure `pornclaw/.dev-state/` exists before writing markers

- [ ] **Step 3: Implement dependency installation with hash invalidation**

Behavior:

- if requirements hash marker is missing or stale, run:

```bash
<venv-python> -m pip install -r requirements.txt
```

- then write the current hash marker

- [ ] **Step 4: Implement database initialization**

Always run:

```bash
<venv-python> scripts/init_db.py
```

This keeps the command simple and avoids stale-schema assumptions.

- [ ] **Step 5: Implement Playwright handling**

Behavior:

- if `--skip-playwright` is present, skip immediately
- otherwise, if the Playwright marker is missing, run:

```bash
<venv-python> -m playwright install chromium
```

- on success, write the Playwright marker
- on failure, print a warning and continue to server start

- [ ] **Step 6: Start the development server**

Run:

```bash
<venv-python> -m uvicorn app.main:app --reload
```

Use `cwd=/data/boom/Agent/PornClaw/pornclaw` so existing import paths and DB defaults continue to work.

- [ ] **Step 7: Re-run the new dev-entry tests until they pass**

Run:

```bash
cd /data/boom/Agent/PornClaw/pornclaw
pytest tests/test_dev_entry.py -v
```

Expected: all new `test_dev_entry.py` tests pass.

- [ ] **Step 8: Commit the orchestration slice**

```bash
git add dev.py pornclaw/tests/test_dev_entry.py
git commit -m "feat: add one-command development entrypoint"
```

### Task 5: Update README guidance and verify the final behavior

**Files:**
- Modify: `README.md`
- Modify: `pornclaw/README.md`

- [ ] **Step 1: Replace the primary startup instructions with the new command**

Update both READMEs so the main path becomes:

```bash
python dev.py
```

Explain that the first run:

- creates `pornclaw/.venv`
- installs Python dependencies
- initializes the DB
- attempts to install Chromium unless `--skip-playwright` is used

- [ ] **Step 2: Keep the manual setup path as fallback troubleshooting**

Retain the longer manual command block in a secondary section such as `手动模式` or `Manual fallback`.

- [ ] **Step 3: Run the full test suite**

Run:

```bash
cd /data/boom/Agent/PornClaw/pornclaw
pytest -v
```

Expected: the existing suite plus `tests/test_dev_entry.py` all pass.

- [ ] **Step 4: Run import/startup verification for the new entrypoint**

Run:

```bash
cd /data/boom/Agent/PornClaw
python3 -m compileall dev.py pornclaw/app pornclaw/tests pornclaw/scripts
python3 - <<'PY'
import dev
print(dev.__file__)
PY
```

Expected:

- `compileall` succeeds
- the inline script prints the path to `dev.py`

- [ ] **Step 5: Do one dry verification of command construction**

If a lightweight `--skip-playwright` or test-only helper exists, use it to confirm the entrypoint reaches the startup phase without raising.

- [ ] **Step 6: Commit the docs and verification slice**

```bash
git add README.md pornclaw/README.md
git commit -m "docs: simplify local startup to one command"
```
