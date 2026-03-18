from datetime import datetime, timedelta, timezone

import pytest

from app.models import SeriesItem, SourceSession, UserFeedback
from app.services.profile import build_profile_summary
from app.services.recommend import rank_series
from app.services.recommend import store_feedback


def test_rank_series_prefers_matching_recent_active_series() -> None:
    now = datetime(2026, 3, 17, 10, 0, 0)
    series_pool = [
        {
            "id": 1,
            "series_name": "Campus Hearts",
            "latest_update_time": now - timedelta(days=1),
            "update_count_7d": 3,
            "tags": ["romance", "school", "drama", "longform"],
            "authors": ["A"],
        },
        {
            "id": 2,
            "series_name": "Dark Dungeon",
            "latest_update_time": now - timedelta(days=10),
            "update_count_7d": 0,
            "tags": ["dark", "action", "explicit"],
            "authors": ["B"],
        },
        {
            "id": 3,
            "series_name": "Sky Tale",
            "latest_update_time": now - timedelta(days=2),
            "update_count_7d": 1,
            "tags": ["fantasy", "soft", "longform"],
            "authors": ["C"],
        },
    ]
    profile = {
        "liked_tags": ["drama", "longform", "school"],
        "disliked_tags": ["dark"],
        "derived_preferences": {"freshness_preference": "recent"},
        "feedback_liked_series": [
            {"series_id": 100, "tags": ["romance", "school", "drama"]}
        ],
        "feedback_disliked_series": [],
    }

    ranked = rank_series(series_pool, profile, top_k=3, reference_time=now)

    assert [item["series"]["id"] for item in ranked][:2] == [1, 3]
    assert ranked[0]["score_breakdown"]["final_score"] > ranked[1]["score_breakdown"]["final_score"]
    assert ranked[-1]["series"]["id"] == 2


def test_rank_series_handles_normalized_datetimes() -> None:
    now = datetime(2026, 3, 20, 12, 0, 0)
    series_pool = [
        {
            "id": 1,
            "series_name": "Alpha",
            "latest_update_time": datetime(2026, 3, 19, 12, 0, tzinfo=timezone.utc),
            "update_count_7d": 1,
            "tags": [],
            "authors": ["A"],
        }
    ]
    profile = {
        "liked_tags": [],
        "disliked_tags": [],
        "feedback_liked_series": [],
        "feedback_disliked_series": [],
    }

    ranked = rank_series(series_pool, profile, top_k=1, reference_time=now)

    assert ranked[0]["score_breakdown"]["freshness_score"] > 0


def test_store_feedback_rejects_series_from_other_session(db_session) -> None:
    session_a = SourceSession(source_url="demo://a", source_name="demo-a", source_type="demo", status="completed")
    session_b = SourceSession(source_url="demo://b", source_name="demo-b", source_type="demo", status="completed")
    db_session.add_all([session_a, session_b])
    db_session.commit()
    db_session.refresh(session_a)
    db_session.refresh(session_b)

    foreign_series = SeriesItem(session_id=session_b.id, series_name="Foreign Series")
    db_session.add(foreign_series)
    db_session.commit()
    db_session.refresh(foreign_series)

    with pytest.raises(ValueError, match="does not belong to session"):
        store_feedback(db_session, session_a.id, foreign_series.id, "like")


def test_build_profile_summary_ignores_feedback_for_foreign_series(db_session) -> None:
    session_a = SourceSession(source_url="demo://a", source_name="demo-a", source_type="demo", status="completed")
    session_b = SourceSession(source_url="demo://b", source_name="demo-b", source_type="demo", status="completed")
    db_session.add_all([session_a, session_b])
    db_session.commit()
    db_session.refresh(session_a)
    db_session.refresh(session_b)

    foreign_series = SeriesItem(
        session_id=session_b.id,
        series_name="Foreign Series",
        tags_json='["fantasy"]',
    )
    db_session.add(foreign_series)
    db_session.commit()
    db_session.refresh(foreign_series)

    db_session.add(
        UserFeedback(
            session_id=session_a.id,
            series_id=foreign_series.id,
            feedback_type="like",
        )
    )
    db_session.commit()

    summary = build_profile_summary(db_session, session_a.id)

    assert summary["feedback_liked_series"] == []
