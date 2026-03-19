from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.recommendation import RecommendRequest, RecommendResponse, RecommendationItem
from app.services.recommend import generate_recommendations, load_candidate_series


router = APIRouter(tags=["recommend"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/candidate-feedback/{session_id}", response_class=HTMLResponse)
async def candidate_feedback_page(session_id: int, request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    candidates = load_candidate_series(db, session_id)
    return templates.TemplateResponse(
        request,
        "candidate_feedback.html",
        {"session_id": session_id, "candidates": candidates},
    )


@router.get("/recommendations/{session_id}", response_class=HTMLResponse)
async def recommendations_page(session_id: int, request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    recommendations = generate_recommendations(db, session_id)
    return templates.TemplateResponse(
        request,
        "recommendations.html",
        {"session_id": session_id, "recommendations": recommendations},
    )


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(payload: RecommendRequest, db: Session = Depends(get_db)) -> RecommendResponse:
    try:
        top = generate_recommendations(db, payload.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    items = [
        RecommendationItem(
            series_id=item["series_id"],
            series_name=item["series_name"],
            score_breakdown=item["score_breakdown"],
            reason_text=item["reason_text"],
        )
        for item in top
    ]
    return RecommendResponse(
        top_5=items,
        score_breakdowns=[item.score_breakdown for item in items],
        reasons=[item.reason_text for item in items],
    )
