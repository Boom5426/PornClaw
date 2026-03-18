from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

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
    assert payload.context["max_items"] == 3


def test_source_ingest_api_accepts_phase2_payload() -> None:
    client = TestClient(app)

    response = client.post(
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


def test_source_ingest_rejects_unsafe_explicit_source(monkeypatch) -> None:
    def fail_fetch(self, url, context):
        raise AssertionError("fetch_recent_items should not be called for an invalid source")

    monkeypatch.setattr(PornhubAdapter, "fetch_recent_items", fail_fetch)
    client = TestClient(app)

    response = client.post(
        "/source/ingest",
        json={
            "source_url": "https://evilpornhub.com/x",
            "source_type": "pornhub",
            "context": {},
        },
    )

    assert response.status_code == 400


def test_feedback_api_rejects_unknown_feedback_type() -> None:
    client = TestClient(app)

    response = client.post(
        "/feedback",
        json={
            "session_id": 1,
            "series_id": 1,
            "feedback_type": "boost",
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
