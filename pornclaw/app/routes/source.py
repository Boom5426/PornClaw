from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.source import SourceIngestRequest, SourceIngestResponse
from app.services.ingest import AppError, ingest_source


router = APIRouter(prefix="/source", tags=["source"])


@router.post("/ingest", response_model=SourceIngestResponse)
def ingest(payload: SourceIngestRequest, db: Session = Depends(get_db)) -> SourceIngestResponse:
    try:
        session = ingest_source(db, payload.source_url, payload.source_type, payload.context)
    except AppError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SourceIngestResponse(
        session_id=session.id,
        status=session.status,
        raw_items_count=session.raw_items_count,
        series_count=session.series_count,
        source_type=session.source_type,
        adapter_name=session.adapter_name,
        error_message=session.error_message,
    )
