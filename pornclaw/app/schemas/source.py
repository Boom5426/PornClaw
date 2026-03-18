from typing import Any

from pydantic import BaseModel, Field


class SourceIngestRequest(BaseModel):
    source_url: str
    source_type: str = "auto"
    context: dict[str, Any] = Field(default_factory=dict)


class SourceIngestResponse(BaseModel):
    session_id: int
    status: str
    raw_items_count: int
    series_count: int
    source_type: str
    adapter_name: str | None = None
    error_message: str | None = None
