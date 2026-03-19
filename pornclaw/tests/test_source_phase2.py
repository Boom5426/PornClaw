import pytest
from sqlalchemy import select

from app.db import get_db
from app.adapters.pornhub import PornhubAdapter
from app.main import app
from app.models import RawItem, SeriesItem, SourceSession
from app.schemas.source import SourceIngestRequest
from app.services.ingest import AppError, ingest_source


def test_source_ingest_request_supports_source_type_and_context() -> None:
    payload = SourceIngestRequest(
        source_url="demo://seed",
        source_type="demo",
        context={"max_items": 3, "fetch_detail_pages": False},
    )

    assert payload.source_type == "demo"
    context = payload.context.model_dump() if hasattr(payload.context, "model_dump") else payload.context
    assert context["max_items"] == 3


@pytest.mark.anyio
async def test_source_ingest_api_accepts_phase2_payload(async_client) -> None:
    response = await async_client.post(
        "/source/ingest",
        json={
            "source_url": "demo://seed",
            "source_type": "demo",
            "context": {"max_items": 2, "fetch_detail_pages": False},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["raw_items_count"] >= 1
    assert body["adapter_name"] == "demo-source"


@pytest.mark.anyio
async def test_recommendations_page_uses_app_local_demo_links(db_session, async_client) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        ingest_response = await async_client.post(
            "/source/ingest",
            json={
                "source_url": "demo://seed",
                "source_type": "demo",
                "context": {"max_items": 4, "fetch_detail_pages": False},
            },
        )

        assert ingest_response.status_code == 200
        session_id = ingest_response.json()["session_id"]

        recommendations_response = await async_client.get(f"/recommendations/{session_id}")

        assert recommendations_response.status_code == 200
        assert "https://demo.local" not in recommendations_response.text
        assert "/demo-source/series/" in recommendations_response.text

        detail_response = await async_client.get("/demo-source/series/dark-dungeon/ch9")

        assert detail_response.status_code == 200
        assert "Dark Dungeon" in detail_response.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_candidate_feedback_page_hides_series_after_like(db_session, async_client) -> None:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        ingest_response = await async_client.post(
            "/source/ingest",
            json={
                "source_url": "demo://seed",
                "source_type": "demo",
                "context": {"max_items": 4, "fetch_detail_pages": False},
            },
        )

        assert ingest_response.status_code == 200
        session_id = ingest_response.json()["session_id"]

        first_page = await async_client.get(f"/candidate-feedback/{session_id}")

        assert first_page.status_code == 200
        assert "Campus Hearts" in first_page.text

        feedback_response = await async_client.post(
            "/feedback/form",
            data={
                "session_id": session_id,
                "series_id": 1,
                "feedback_type": "like",
                "next_path": f"/candidate-feedback/{session_id}",
            },
        )

        assert feedback_response.status_code == 200
        assert "Campus Hearts" not in feedback_response.text
        assert "Sky Tale" in feedback_response.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_source_ingest_rejects_unsafe_explicit_source(monkeypatch, async_client) -> None:
    def fail_fetch(self, url, context):
        raise AssertionError("fetch_recent_items should not be called for an invalid source")

    monkeypatch.setattr(PornhubAdapter, "fetch_recent_items", fail_fetch)

    response = await async_client.post(
        "/source/ingest",
        json={
            "source_url": "https://evilpornhub.com/x",
            "source_type": "pornhub",
            "context": {},
        },
    )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_feedback_api_rejects_unknown_feedback_type(async_client) -> None:
    response = await async_client.post(
        "/feedback",
        json={
            "session_id": 1,
            "series_id": 1,
            "feedback_type": "boost",
        },
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_source_ingest_rejects_unknown_source_type(async_client) -> None:
    response = await async_client.post(
        "/source/ingest",
        json={
            "source_url": "demo://seed",
            "source_type": "rss",
            "context": {},
        },
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_source_ingest_rejects_non_positive_max_items(async_client) -> None:
    response = await async_client.post(
        "/source/ingest",
        json={
            "source_url": "demo://seed",
            "source_type": "demo",
            "context": {"max_items": 0, "fetch_detail_pages": False},
        },
    )

    assert response.status_code == 422


def test_ingest_failure_rolls_back_partial_rows(db_session, monkeypatch) -> None:
    class FakeAdapter:
        name = "fake-adapter"

        def validate_source(self, url, context):
            return True

        def detect_source_name(self, url, context=None):
            return "fake-source"

        def fetch_recent_items(self, url, context):
            return [
                {
                    "source_id": "item-1",
                    "title": "Alpha Chapter 1",
                    "detail_url": "https://example.com/a1",
                    "cover_url": "https://img.example.com/a1.jpg",
                    "publish_time": None,
                    "author_or_group": "Circle A",
                    "tags_raw": ["fantasy"],
                    "description_raw": "desc",
                    "series_name_raw": "Alpha",
                    "chapter_or_episode_raw": "Chapter 1",
                }
            ]

    monkeypatch.setattr("app.services.ingest.get_adapter_for_source", lambda url, context: FakeAdapter())
    monkeypatch.setattr("app.services.ingest.aggregate_series", lambda raw_items: (_ for _ in ()).throw(ValueError("boom")))

    with pytest.raises(AppError, match="boom"):
        ingest_source(
            db_session,
            "demo://seed",
            "demo",
            {"fetch_detail_pages": False},
        )

    session = db_session.scalar(select(SourceSession).order_by(SourceSession.id.desc()))
    assert session is not None
    assert session.status == "failed"
    assert session.raw_items_count == 0
    assert session.series_count == 0
    assert session.error_message == "boom"
    assert db_session.scalar(select(RawItem).where(RawItem.session_id == session.id)) is None
    assert db_session.scalar(select(SeriesItem).where(SeriesItem.session_id == session.id)) is None
