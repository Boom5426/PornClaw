from datetime import datetime

import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Recommendation, SeriesItem, UserFeedback
from app.services.explain import build_recommendation_reason
from app.services.profile import build_profile_summary
from app.utils.datetime import coerce_utc_naive


def rank_series(
    series_pool: list[dict],
    profile: dict,
    top_k: int = 5,
    reference_time: datetime | None = None,
) -> list[dict]:
    now = coerce_utc_naive(reference_time or datetime.utcnow()) or datetime.utcnow()
    ranked = []
    prior_like_tags = {
        tag for entry in profile.get("feedback_liked_series", []) for tag in entry.get("tags", [])
    }
    prior_dislike_tags = {
        tag for entry in profile.get("feedback_disliked_series", []) for tag in entry.get("tags", [])
    }
    for series in series_pool:
        tags = set(series.get("tags", []))
        latest_update_time = coerce_utc_naive(series.get("latest_update_time"))
        freshness_days = (now - latest_update_time).days if latest_update_time else 999
        freshness_score = max(0.0, 5.0 - min(freshness_days, 10) * 0.5)
        positive_tag_score = len(tags & set(profile.get("liked_tags", []))) * 2.5
        negative_penalty = len(tags & set(profile.get("disliked_tags", []))) * -4.0
        feedback_similarity_score = len(tags & prior_like_tags) * 1.5 + len(tags & prior_dislike_tags) * -2.0
        series_activity_score = min(series.get("update_count_7d", 0), 5) * 0.8
        diversity_adjustment = -0.3 * max(0, len(tags & prior_like_tags) - 2)
        final_score = (
            freshness_score
            + positive_tag_score
            + negative_penalty
            + feedback_similarity_score
            + series_activity_score
            + diversity_adjustment
        )
        ranked.append(
            {
                "series": series,
                "score_breakdown": {
                    "freshness_score": round(freshness_score, 3),
                    "positive_tag_score": round(positive_tag_score, 3),
                    "negative_penalty": round(negative_penalty, 3),
                    "feedback_similarity_score": round(feedback_similarity_score, 3),
                    "series_activity_score": round(series_activity_score, 3),
                    "diversity_adjustment": round(diversity_adjustment, 3),
                    "final_score": round(final_score, 3),
                },
            }
        )
    ranked.sort(key=lambda item: item["score_breakdown"]["final_score"], reverse=True)
    return ranked[:top_k]


def load_candidate_series(db: Session, session_id: int) -> list[dict]:
    series_rows = db.scalars(select(SeriesItem).where(SeriesItem.session_id == session_id)).all()
    items = [_series_model_to_dict(row) for row in series_rows]
    items.sort(
        key=lambda item: (item["update_count_7d"], coerce_utc_naive(item["latest_update_time"]) or datetime.min),
        reverse=True,
    )
    return items[: max(settings.candidate_sample_size, 1)]


def store_feedback(db: Session, session_id: int, series_id: int, feedback_type: str) -> dict:
    db.add(UserFeedback(session_id=session_id, series_id=series_id, feedback_type=feedback_type))
    db.commit()
    return build_profile_summary(db, session_id)


def generate_recommendations(db: Session, session_id: int) -> list[dict]:
    series_rows = db.scalars(select(SeriesItem).where(SeriesItem.session_id == session_id)).all()
    if not series_rows:
        raise ValueError("该 session 下没有可推荐的系列。")
    series_pool = [_series_model_to_dict(row) for row in series_rows]
    profile = build_profile_summary(db, session_id)
    ranked = rank_series(series_pool, profile, top_k=settings.recommendation_limit)
    db.execute(delete(Recommendation).where(Recommendation.session_id == session_id))
    db.commit()
    persisted: list[dict] = []
    for index, item in enumerate(ranked, start=1):
        series = item["series"]
        reason = build_recommendation_reason(series, item["score_breakdown"], profile)
        record = Recommendation(
            session_id=session_id,
            series_id=series["id"],
            rank=index,
            score=item["score_breakdown"]["final_score"],
            score_breakdown_json=json.dumps(item["score_breakdown"]),
            reason_text=reason,
        )
        db.add(record)
        persisted.append(
            {
                "series_id": series["id"],
                "series_name": series["series_name"],
                "cover_url": series.get("representative_cover"),
                "tags": series.get("tags", []),
                "latest_update_time": series.get("latest_update_time"),
                "source_urls": series.get("source_urls", []),
                "score_breakdown": item["score_breakdown"],
                "reason_text": reason,
            }
        )
    db.commit()
    return persisted


def _series_model_to_dict(row: SeriesItem) -> dict:
    return {
        "id": row.id,
        "series_name": row.series_name,
        "representative_cover": row.representative_cover,
        "latest_update_time": coerce_utc_naive(row.latest_update_time),
        "update_count_7d": row.update_count_7d,
        "tags": json.loads(row.tags_json),
        "source_urls": json.loads(row.source_urls_json),
        "authors": json.loads(row.authors_json),
        "meta": json.loads(row.meta_json),
    }
