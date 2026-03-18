from datetime import datetime, timedelta, timezone

from app.services.recommend import rank_series


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
