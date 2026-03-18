from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.services.ingest import AppError, ingest_source
from app.services.profile import create_or_update_profile


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
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
def start_flow(
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
        context = {
            "credential_profile": credential_profile or None,
            "channel_or_feed_hint": channel_or_feed_hint or None,
            "max_items": max_items,
            "fetch_detail_pages": fetch_detail_pages,
        }
        session = ingest_source(db, source_url, source_type, context)
        create_or_update_profile(db, session.id, liked_tags, disliked_tags, free_text_intent)
        return RedirectResponse(f"/candidate-feedback/{session.id}", status_code=303)
    except AppError as exc:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": str(exc), "back_path": "/"},
            status_code=400,
        )
