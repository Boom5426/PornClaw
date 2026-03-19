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


class SourceIngestResponse(BaseModel):
    session_id: int
    status: str
    raw_items_count: int
    series_count: int
    source_type: str
    adapter_name: str | None = None
    error_message: str | None = None
