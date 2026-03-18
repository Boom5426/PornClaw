from datetime import datetime, timedelta, timezone

from app.services.aggregate import aggregate_series


def test_aggregate_series_groups_by_series_name_and_combines_fields() -> None:
    now = datetime(2026, 3, 17, 10, 0, 0)
    raw_items = [
        {
            "title": "Magic Academy Chapter 1",
            "detail_url": "https://example.com/a1",
            "cover_url": "https://img.example.com/a1.jpg",
            "publish_time": now - timedelta(days=1),
            "author_or_group": "Circle A",
            "normalized_tags": ["fantasy", "school"],
            "series_name_raw": "Magic Academy",
        },
        {
            "title": "Magic Academy Chapter 2",
            "detail_url": "https://example.com/a2",
            "cover_url": "https://img.example.com/a2.jpg",
            "publish_time": now,
            "author_or_group": "Circle A",
            "normalized_tags": ["fantasy", "drama"],
            "series_name_raw": "Magic Academy",
        },
    ]

    series = aggregate_series(raw_items, reference_time=now)

    assert len(series) == 1
    assert series[0]["series_name"] == "Magic Academy"
    assert series[0]["latest_update_time"] == now
    assert series[0]["update_count_7d"] == 2
    assert set(series[0]["tags"]) == {"fantasy", "school", "drama"}
    assert series[0]["authors"] == ["Circle A"]
    assert len(series[0]["source_urls"]) == 2


def test_aggregate_series_handles_timezone_aware_inputs() -> None:
    raw_items = [
        {
            "title": "Alpha Chapter 1",
            "detail_url": "https://example.com/a1",
            "cover_url": "https://img.example.com/a1.jpg",
            "publish_time": datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            "author_or_group": "Circle A",
            "normalized_tags": ["fantasy"],
            "series_name_raw": "Alpha",
        },
        {
            "title": "Alpha Chapter 2",
            "detail_url": "https://example.com/a2",
            "cover_url": "https://img.example.com/a2.jpg",
            "publish_time": datetime(2026, 3, 19, 9, 0, tzinfo=timezone.utc),
            "author_or_group": "Circle A",
            "normalized_tags": ["fantasy", "drama"],
            "series_name_raw": "Alpha",
        },
    ]

    series = aggregate_series(raw_items, reference_time=datetime(2026, 3, 20, 9, 0, 0))

    assert len(series) == 1
    assert series[0]["update_count_7d"] == 2
    assert series[0]["latest_update_time"].tzinfo is None
