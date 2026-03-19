# PornClaw Phase 2 Closeout Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the current Phase 2 work by restoring a trustworthy HTTP verification loop, landing the in-progress demo-local browsing UX, and finishing the remaining schema-level hardening at the ingest boundary.

**Architecture:** Treat the remaining work as four small slices. First isolate and stabilize the request-test baseline so HTTP-level verification is trustworthy again. Then land the existing demo UX changes as one self-contained slice, push the last ingest validation rules into the request/form boundary, and finish with one clean verification pass over the targeted suite. Preserve the current dirty-worktree intent; do not revert the in-progress demo UX changes.

**Tech Stack:** Python 3.11, FastAPI, Starlette, Pydantic, SQLAlchemy, SQLite, Jinja2, pytest, httpx, anyio

---

## Files and Responsibilities

- `docs/superpowers/plans/2026-03-18-pornclaw-phase2-closeout.md`
  - This execution plan.
- `pornclaw/tests/test_http_stack.py`
  - Minimal request-stack smoke test that separates repo-local HTTP client breakage from harness/runtime limitations.
- `pornclaw/tests/conftest.py`
  - Shared test helpers only if request-level tests need a stable client fixture or timeout-aware helper.
- `pornclaw/requirements.txt`
  - Request-stack dependency pinning only if the minimal smoke test proves a repo-local compatibility problem.
- `pornclaw/tests/test_source_phase2.py`
  - Phase 2 request-flow tests for demo-local links, post-feedback candidate filtering, and ingest boundary validation.
- `pornclaw/app/adapters/demo_source.py`
  - App-local demo dataset, local detail links, and helper lookup for demo detail pages.
- `pornclaw/app/routes/pages.py`
  - Home-page form flow, validated ingest payload construction, and demo detail page route.
- `pornclaw/app/services/recommend.py`
  - Candidate list filtering so already-rated series no longer reappear.
- `pornclaw/app/templates/candidate_feedback.html`
  - Candidate-page empty state once all visible series have feedback.
- `pornclaw/app/templates/demo_series_detail.html`
  - Demo detail page for local browsing.
- `pornclaw/app/static/demo/campus-hearts.svg`
  - Local demo cover asset.
- `pornclaw/app/static/demo/sky-tale.svg`
  - Local demo cover asset.
- `pornclaw/app/static/demo/dark-dungeon.svg`
  - Local demo cover asset.
- `pornclaw/app/static/styles.css`
  - Styling for the demo detail page and candidate empty state.
- `pornclaw/app/schemas/source.py`
  - Structured ingest request validation, including accepted `source_type` values and bounded `context.max_items`.
- `README.md`
  - Current-status wording and any demo-local navigation notes that must match the shipped behavior.

## Chunk 1: HTTP Verification Baseline

### Task 1: Prove whether the HTTP request-test problem is repo-local or environment-local

**Files:**
- Create: `pornclaw/tests/test_http_stack.py`
- Modify: `pornclaw/tests/conftest.py`
- Modify: `pornclaw/requirements.txt`
- Test: `pornclaw/tests/test_source_phase2.py`

- [ ] **Step 1: Write the failing minimal request smoke test**

Create `pornclaw/tests/test_http_stack.py` with a single-route FastAPI app and the current request-test path:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_minimal_fastapi_request_round_trip() -> None:
    app = FastAPI()

    @app.get("/")
    def read_root() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
```

- [ ] **Step 2: Run the smoke test with an explicit shell timeout**

Run:

```bash
cd /data/boom/Agent/PornClaw
timeout 20s pornclaw/.venv/bin/pytest pornclaw/tests/test_http_stack.py::test_minimal_fastapi_request_round_trip -vv -s
```

Expected:
- Healthy local stack: PASS within a few seconds.
- Current broken baseline: exit code `124` or a visible hang before the assertion line.

- [ ] **Step 3: Run one existing request test to confirm whether the failure shape matches the minimal smoke**

Run:

```bash
cd /data/boom/Agent/PornClaw
timeout 20s pornclaw/.venv/bin/pytest pornclaw/tests/test_source_phase2.py::test_source_ingest_api_accepts_phase2_payload -vv -s
```

Expected:
- If both the minimal smoke test and the existing Phase 2 request test hang, treat this as a request-stack blocker.
- If the minimal smoke test passes but the Phase 2 test fails, the blocker is in app code, not the stack.

- [ ] **Step 4: Apply the narrowest stable fix only if the failure is repo-local**

Use one of these two paths only after Step 2 and Step 3 make the problem clear:

```python
# Option A: keep TestClient and pin the known-good request stack in pornclaw/requirements.txt
fastapi==0.115.6
uvicorn[standard]==0.32.1
httpx==0.28.1
```

```python
# Option B: if client construction is the only unstable point, centralize it in pornclaw/tests/conftest.py
from fastapi.testclient import TestClient


def build_test_client(app):
    return TestClient(app)
```

Do not churn both dependency pins and test helpers unless one change is proven insufficient.

- [ ] **Step 5: Re-run the minimal smoke test and one Phase 2 request test**

Run:

```bash
cd /data/boom/Agent/PornClaw
timeout 20s pornclaw/.venv/bin/pytest \
  pornclaw/tests/test_http_stack.py::test_minimal_fastapi_request_round_trip \
  pornclaw/tests/test_source_phase2.py::test_source_ingest_api_accepts_phase2_payload \
  -vv -s
```

Expected: both tests PASS without hanging.

- [ ] **Step 6: Commit the request-baseline slice**

```bash
git add pornclaw/tests/test_http_stack.py pornclaw/tests/conftest.py pornclaw/requirements.txt
git commit -m "test: stabilize request-level verification baseline"
```

Commit only the files that actually changed.

## Chunk 2: Demo-Local Browsing Closeout

### Task 2: Lock the in-progress demo UX behavior in request tests

**Files:**
- Modify: `pornclaw/tests/test_source_phase2.py`

- [ ] **Step 1: Keep the two high-value demo request tests as the executable spec**

Make sure `pornclaw/tests/test_source_phase2.py` contains these behaviors:

```python
def test_recommendations_page_uses_app_local_demo_links(db_session) -> None:
    ...
    assert "https://demo.local" not in recommendations_response.text
    assert "/demo-source/series/" in recommendations_response.text


def test_candidate_feedback_page_hides_series_after_like(db_session) -> None:
    ...
    assert "Campus Hearts" not in feedback_response.text
    assert "Sky Tale" in feedback_response.text
```

- [ ] **Step 2: Run the two demo UX tests and confirm they currently fail or remain unverified until the implementation slice is complete**

Run:

```bash
cd /data/boom/Agent/PornClaw
timeout 20s pornclaw/.venv/bin/pytest \
  pornclaw/tests/test_source_phase2.py::test_recommendations_page_uses_app_local_demo_links \
  pornclaw/tests/test_source_phase2.py::test_candidate_feedback_page_hides_series_after_like \
  -vv -s
```

Expected:
- Before the slice is complete: FAIL for missing local links, missing demo detail route, or candidate-page filtering gaps.
- After Chunk 1 is fixed: no hang.

### Task 3: Finish the demo-local implementation and empty-state behavior

**Files:**
- Modify: `pornclaw/app/adapters/demo_source.py`
- Modify: `pornclaw/app/routes/pages.py`
- Modify: `pornclaw/app/services/recommend.py`
- Modify: `pornclaw/app/templates/candidate_feedback.html`
- Modify: `pornclaw/app/static/styles.css`
- Modify: `README.md`
- Create: `pornclaw/app/templates/demo_series_detail.html`
- Create: `pornclaw/app/static/demo/campus-hearts.svg`
- Create: `pornclaw/app/static/demo/sky-tale.svg`
- Create: `pornclaw/app/static/demo/dark-dungeon.svg`
- Test: `pornclaw/tests/test_source_phase2.py`

- [ ] **Step 1: Implement app-local demo URLs and demo item lookup**

Land the core demo data shape in `pornclaw/app/adapters/demo_source.py`:

```python
def _demo_item(..., series_slug: str, chapter_slug: str, ...) -> dict:
    return {
        ...
        "detail_url": f"/demo-source/series/{series_slug}/{chapter_slug}",
        "cover_url": f"/static/demo/{series_slug}.svg",
        ...
    }
```

Also add:

```python
def get_demo_item(series_slug: str, chapter_slug: str) -> dict | None:
    ...
```

- [ ] **Step 2: Add the local demo detail route**

In `pornclaw/app/routes/pages.py`, add:

```python
@router.get("/demo-source/series/{series_slug}/{chapter_slug}", response_class=HTMLResponse)
def demo_series_detail(series_slug: str, chapter_slug: str, request: Request) -> HTMLResponse:
    item = get_demo_item(series_slug, chapter_slug)
    if item is None:
        raise HTTPException(status_code=404, detail="Demo source item not found.")
    return templates.TemplateResponse(
        request,
        "demo_series_detail.html",
        {"item": item, "title": f"{item['title']} | PornClaw Demo Source"},
    )
```

- [ ] **Step 3: Hide already-rated series from the candidate page**

In `pornclaw/app/services/recommend.py`, make `load_candidate_series()` exclude `UserFeedback.series_id` values for the same `session_id`:

```python
feedback_series_ids = {
    series_id
    for series_id in db.scalars(select(UserFeedback.series_id).where(UserFeedback.session_id == session_id))
}
items = [_series_model_to_dict(row) for row in series_rows if row.id not in feedback_series_ids]
```

- [ ] **Step 4: Add the candidate-page empty state and demo detail template**

Update `pornclaw/app/templates/candidate_feedback.html`:

```html
{% if not candidates %}
<section class="panel">
  <p>这一轮候选系列都已经记录过反馈了，可以直接生成 Top 5 推荐。</p>
</section>
{% endif %}
```

Create `pornclaw/app/templates/demo_series_detail.html` with the item description, tags, author, publish date, and a local cover image.

- [ ] **Step 5: Add the local SVG demo assets and any matching CSS**

Create:

```text
pornclaw/app/static/demo/campus-hearts.svg
pornclaw/app/static/demo/sky-tale.svg
pornclaw/app/static/demo/dark-dungeon.svg
```

Update `pornclaw/app/static/styles.css` only as needed for the new detail-page layout and candidate empty state.

- [ ] **Step 6: Re-run the two demo UX tests until they pass**

Run:

```bash
cd /data/boom/Agent/PornClaw
timeout 20s pornclaw/.venv/bin/pytest \
  pornclaw/tests/test_source_phase2.py::test_recommendations_page_uses_app_local_demo_links \
  pornclaw/tests/test_source_phase2.py::test_candidate_feedback_page_hides_series_after_like \
  -vv -s
```

Expected: PASS.

- [ ] **Step 7: Commit the demo UX slice**

```bash
git add README.md pornclaw/app/adapters/demo_source.py pornclaw/app/routes/pages.py pornclaw/app/services/recommend.py pornclaw/app/templates/candidate_feedback.html pornclaw/app/templates/demo_series_detail.html pornclaw/app/static/styles.css pornclaw/app/static/demo pornclaw/tests/test_source_phase2.py
git commit -m "feat: polish demo local browsing flow"
```

## Chunk 3: Ingest Boundary Hardening Tail

### Task 4: Reject unsupported `source_type` values and invalid `context.max_items` at the request/form boundary

**Files:**
- Modify: `pornclaw/app/schemas/source.py`
- Modify: `pornclaw/app/routes/pages.py`
- Modify: `pornclaw/tests/test_source_phase2.py`
- Test: `pornclaw/tests/test_adapter.py`

- [ ] **Step 1: Add the failing ingest validation tests**

Extend `pornclaw/tests/test_source_phase2.py` with tests like:

```python
def test_source_ingest_rejects_unknown_source_type() -> None:
    client = TestClient(app)
    response = client.post(
        "/source/ingest",
        json={"source_url": "demo://seed", "source_type": "rss", "context": {}},
    )
    assert response.status_code == 422


def test_source_ingest_rejects_non_positive_max_items() -> None:
    client = TestClient(app)
    response = client.post(
        "/source/ingest",
        json={
            "source_url": "demo://seed",
            "source_type": "demo",
            "context": {"max_items": 0, "fetch_detail_pages": False},
        },
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run the new validation tests and confirm they fail for the intended reasons**

Run:

```bash
cd /data/boom/Agent/PornClaw
timeout 20s pornclaw/.venv/bin/pytest \
  pornclaw/tests/test_source_phase2.py::test_source_ingest_rejects_unknown_source_type \
  pornclaw/tests/test_source_phase2.py::test_source_ingest_rejects_non_positive_max_items \
  -vv -s
```

Expected: FAIL because `source_type` is still an unconstrained string and `context.max_items` is still only coerced later.

- [ ] **Step 3: Implement structured request models in `pornclaw/app/schemas/source.py`**

Replace the loose schema with a constrained one:

```python
from typing import Literal

from pydantic import BaseModel, Field


SourceType = Literal["auto", "demo", "generic_template", "pornhub", "telegram"]


class SourceContextPayload(BaseModel):
    credential_profile: str | None = None
    cookies_mode: str = "none"
    max_items: int = Field(default=20, ge=1, le=100)
    fetch_detail_pages: bool = True
    channel_or_feed_hint: str | None = None


class SourceIngestRequest(BaseModel):
    source_url: str
    source_type: SourceType = "auto"
    context: SourceContextPayload = Field(default_factory=SourceContextPayload)
```

- [ ] **Step 4: Make the HTML form flow use the same validated ingest payload**

In `pornclaw/app/routes/pages.py`, build a `SourceIngestRequest` before calling `ingest_source()`:

```python
payload = SourceIngestRequest(
    source_url=source_url,
    source_type=source_type,
    context={
        "credential_profile": credential_profile or None,
        "channel_or_feed_hint": channel_or_feed_hint or None,
        "max_items": max_items,
        "fetch_detail_pages": fetch_detail_pages,
    },
)
session = ingest_source(db, payload.source_url, payload.source_type, payload.context.model_dump())
```

Handle validation errors in the form flow with the same user-facing error template instead of letting raw exceptions leak.

- [ ] **Step 5: Re-run the validation tests plus the existing unsafe-source guardrail**

Run:

```bash
cd /data/boom/Agent/PornClaw
timeout 20s pornclaw/.venv/bin/pytest \
  pornclaw/tests/test_source_phase2.py::test_source_ingest_rejects_unknown_source_type \
  pornclaw/tests/test_source_phase2.py::test_source_ingest_rejects_non_positive_max_items \
  pornclaw/tests/test_source_phase2.py::test_source_ingest_rejects_unsafe_explicit_source \
  -vv -s
```

Expected: PASS.

- [ ] **Step 6: Commit the schema-hardening slice**

```bash
git add pornclaw/app/schemas/source.py pornclaw/app/routes/pages.py pornclaw/tests/test_source_phase2.py
git commit -m "fix: validate source ingest payloads at the boundary"
```

## Chunk 4: Final Verification and Closeout

### Task 5: Re-run the targeted suite and do one manual demo smoke

**Files:**
- Modify: `README.md`
- Test: `pornclaw/tests/test_adapter.py`
- Test: `pornclaw/tests/test_aggregate.py`
- Test: `pornclaw/tests/test_recommend.py`
- Test: `pornclaw/tests/test_source_phase2.py`
- Test: `pornclaw/tests/test_dev_entry.py`

- [ ] **Step 1: Run the targeted automated suite**

Run:

```bash
cd /data/boom/Agent/PornClaw
timeout 60s pornclaw/.venv/bin/pytest \
  pornclaw/tests/test_http_stack.py \
  pornclaw/tests/test_adapter.py \
  pornclaw/tests/test_aggregate.py \
  pornclaw/tests/test_recommend.py \
  pornclaw/tests/test_source_phase2.py \
  pornclaw/tests/test_dev_entry.py \
  -vv
```

Expected: all targeted tests PASS with no hangs.

- [ ] **Step 2: Run one manual application smoke through the supported developer entrypoint**

Run:

```bash
cd /data/boom/Agent/PornClaw
python dev.py --skip-playwright
```

Expected:
- `.venv` bootstrap is skipped if already ready.
- DB init still runs.
- Uvicorn starts.
- The home page loads with `demo://seed`.

- [ ] **Step 3: Manually verify the demo-local browsing path**

In the browser:

1. Open `/`
2. Start with `demo://seed`
3. Submit one like on the candidate page
4. Confirm the liked series disappears from the next candidate render
5. Open one recommendation detail link under `/demo-source/series/...`

Expected: all navigation stays inside the app; no `demo.local` links appear.

- [ ] **Step 4: Commit any final README cleanup only if documentation still changed during the slice**

```bash
git add README.md
git commit -m "docs: align phase2 closeout behavior"
```

Commit only if `README.md` changed after the earlier slices.
