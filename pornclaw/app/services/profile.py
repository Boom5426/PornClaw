import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SeriesItem, UserFeedback, UserProfile
from app.services.preference_parser import parse_free_text_intent


def create_or_update_profile(
    db: Session,
    session_id: int,
    liked_tags: list[str],
    disliked_tags: list[str],
    free_text_intent: str,
) -> UserProfile:
    profile = db.scalar(select(UserProfile).where(UserProfile.session_id == session_id))
    derived = parse_free_text_intent(free_text_intent)
    if profile is None:
        profile = UserProfile(
            session_id=session_id,
            liked_tags_json=json.dumps(sorted(set(liked_tags))),
            disliked_tags_json=json.dumps(sorted(set(disliked_tags))),
            free_text_intent=free_text_intent,
            derived_preferences_json=json.dumps(derived),
        )
        db.add(profile)
    else:
        profile.liked_tags_json = json.dumps(sorted(set(liked_tags)))
        profile.disliked_tags_json = json.dumps(sorted(set(disliked_tags)))
        profile.free_text_intent = free_text_intent
        profile.derived_preferences_json = json.dumps(derived)
    db.commit()
    db.refresh(profile)
    return profile


def build_profile_summary(db: Session, session_id: int) -> dict:
    profile = db.scalar(select(UserProfile).where(UserProfile.session_id == session_id))
    liked_series_ids = [
        feedback.series_id
        for feedback in db.scalars(
            select(UserFeedback).where(
                UserFeedback.session_id == session_id, UserFeedback.feedback_type.in_(["like", "more_like_this"])
            )
        )
    ]
    disliked_series_ids = [
        feedback.series_id
        for feedback in db.scalars(
            select(UserFeedback).where(
                UserFeedback.session_id == session_id, UserFeedback.feedback_type.in_(["dislike", "less_like_this"])
            )
        )
    ]
    liked_series = [
        entry
        for series_id in liked_series_ids
        if (entry := _series_to_profile_entry_for_session(db, session_id, series_id)) is not None
    ]
    disliked_series = [
        entry
        for series_id in disliked_series_ids
        if (entry := _series_to_profile_entry_for_session(db, session_id, series_id)) is not None
    ]
    return {
        "liked_tags": json.loads(profile.liked_tags_json) if profile else [],
        "disliked_tags": json.loads(profile.disliked_tags_json) if profile else [],
        "derived_preferences": json.loads(profile.derived_preferences_json) if profile else {},
        "feedback_liked_series": liked_series,
        "feedback_disliked_series": disliked_series,
    }


def _series_to_profile_entry(series: SeriesItem) -> dict:
    return {
        "series_id": series.id,
        "tags": json.loads(series.tags_json),
        "series_name": series.series_name,
    }


def _series_to_profile_entry_for_session(db: Session, session_id: int, series_id: int) -> dict | None:
    series = db.get(SeriesItem, series_id)
    if series is None or series.session_id != session_id:
        return None
    return _series_to_profile_entry(series)
