from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.recommend import store_feedback


router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)) -> FeedbackResponse:
    try:
        summary = store_feedback(db, payload.session_id, payload.series_id, payload.feedback_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FeedbackResponse(ok=True, updated_profile_summary=summary)


@router.post("/feedback/form")
async def create_feedback_from_form(
    session_id: int = Form(...),
    series_id: int = Form(...),
    feedback_type: str = Form(...),
    next_path: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        store_feedback(db, session_id, series_id, feedback_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(next_path, status_code=303)
