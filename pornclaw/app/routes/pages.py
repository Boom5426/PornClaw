from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.adapters.demo_source import get_demo_item
from app.config import settings
from app.db import get_db
from app.schemas.source import SourceIngestRequest
from app.services.ingest import AppError, ingest_source
from app.services.profile import create_or_update_profile


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "tag_options": settings.standard_tags,
            "demo_url": "demo://seed",
            "source_types": settings.source_types,
            "default_source_type": settings.default_source_type,
        },
    )


@router.post("/start", response_class=HTMLResponse)
async def start_flow(
    request: Request,
    source_url: str = Form(...),
    source_type: str = Form(default="auto"),
    credential_profile: str = Form(default=""),
    channel_or_feed_hint: str = Form(default=""),
    max_items: int = Form(default=20),
    fetch_detail_pages: bool = Form(default=False),
    liked_tags: list[str] = Form(default=[]),
    disliked_tags: list[str] = Form(default=[]),
    free_text_intent: str = Form(default=""),
    db: Session = Depends(get_db),
):
    try:
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
        session = ingest_source(
            db,
            payload.source_url,
            payload.source_type,
            payload.context.model_dump(exclude_none=True),
        )
        create_or_update_profile(db, session.id, liked_tags, disliked_tags, free_text_intent)
        return RedirectResponse(f"/candidate-feedback/{session.id}", status_code=303)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": "数据源参数非法。", "back_path": "/"},
            status_code=400,
        )
    except AppError as exc:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": str(exc), "back_path": "/"},
            status_code=400,
        )


@router.get("/demo-source/series/{series_slug}/{chapter_slug}", response_class=HTMLResponse)
async def demo_series_detail(series_slug: str, chapter_slug: str, request: Request) -> HTMLResponse:
    item = get_demo_item(series_slug, chapter_slug)
    if item is None:
        raise HTTPException(status_code=404, detail="Demo source item not found.")
    return templates.TemplateResponse(
        request,
        "demo_series_detail.html",
        {
            "item": item,
            "title": f"{item['title']} | PornClaw Demo Source",
        },
    )
