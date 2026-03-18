from collections import defaultdict
from datetime import datetime, timedelta

from app.utils.datetime import coerce_utc_naive
from app.utils.text import slugify_title


def aggregate_series(raw_items: list[dict], reference_time: datetime | None = None) -> list[dict]:
    now = coerce_utc_naive(reference_time or datetime.utcnow()) or datetime.utcnow()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in raw_items:
        key = item.get("series_name_raw") or item.get("series_name") or slugify_title(item.get("title", ""))
        grouped[key].append(item)

    aggregated: list[dict] = []
    recent_cutoff = now - timedelta(days=7)
    for key, items in grouped.items():
        latest_item = max(items, key=lambda entry: coerce_utc_naive(entry.get("publish_time")) or datetime.min)
        tags = sorted({tag for item in items for tag in item.get("normalized_tags", [])})
        authors = sorted({item.get("author_or_group") for item in items if item.get("author_or_group")})
        source_urls = [item.get("detail_url") for item in items if item.get("detail_url")]
        aggregated.append(
            {
                "series_name": items[0].get("series_name_raw") or items[0].get("series_name") or key,
                "representative_cover": latest_item.get("cover_url"),
                "latest_update_time": coerce_utc_naive(latest_item.get("publish_time")),
                "update_count_7d": sum(
                    1
                    for item in items
                    if (publish_time := coerce_utc_naive(item.get("publish_time"))) and publish_time >= recent_cutoff
                ),
                "tags": tags,
                "authors": authors,
                "source_urls": source_urls,
                "meta": {"raw_item_count": len(items)},
            }
        )
    aggregated.sort(
        key=lambda item: coerce_utc_naive(item.get("latest_update_time")) or datetime.min,
        reverse=True,
    )
    return aggregated
