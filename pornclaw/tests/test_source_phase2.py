from fastapi.testclient import TestClient

from app.main import app
from app.schemas.source import SourceIngestRequest


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
