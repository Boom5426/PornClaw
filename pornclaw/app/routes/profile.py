import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.profile import ProfileCreateRequest, ProfileCreateResponse
from app.services.profile import create_or_update_profile


router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("/create", response_model=ProfileCreateResponse)
async def create_profile(payload: ProfileCreateRequest, db: Session = Depends(get_db)) -> ProfileCreateResponse:
    profile = create_or_update_profile(
        db,
        payload.session_id,
        payload.liked_tags,
        payload.disliked_tags,
        payload.free_text_intent,
    )
    return ProfileCreateResponse(
        profile_id=profile.id,
        derived_preferences=json.loads(profile.derived_preferences_json),
    )
