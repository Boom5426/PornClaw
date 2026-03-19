from datetime import datetime
from html import escape
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.adapters.base import BaseAdapter, SourceContext
from app.config import settings


def _demo_item(
    source_id: str,
    *,
    title: str,
    series_slug: str,
    chapter_slug: str,
    publish_date: str,
    author_or_group: str,
    tags: list[str],
    description_raw: str,
    series_name_raw: str,
    chapter_or_episode_raw: str,
) -> dict:
    return {
        "source_id": source_id,
        "title": title,
        "detail_url": f"/demo-source/series/{series_slug}/{chapter_slug}",
        "cover_url": f"/static/demo/{series_slug}.svg",
        "publish_time": datetime.fromisoformat(publish_date),
        "author_or_group": author_or_group,
        "tags": tags,
        "description_raw": description_raw,
        "series_name_raw": series_name_raw,
        "chapter_or_episode_raw": chapter_or_episode_raw,
        "series_slug": series_slug,
        "chapter_slug": chapter_slug,
    }


DEMO_ITEMS = [
    _demo_item(
        "1",
        title="Campus Hearts Chapter 1",
        series_slug="campus-hearts",
        chapter_slug="ch1",
        publish_date="2026-03-16",
        author_or_group="Studio A",
        tags=["romance", "school", "drama", "longform"],
        description_raw="A school romance drama.",
        series_name_raw="Campus Hearts",
        chapter_or_episode_raw="Chapter 1",
    ),
    _demo_item(
        "2",
        title="Campus Hearts Chapter 2",
        series_slug="campus-hearts",
        chapter_slug="ch2",
        publish_date="2026-03-17",
        author_or_group="Studio A",
        tags=["romance", "school", "drama", "longform"],
        description_raw="The story continues.",
        series_name_raw="Campus Hearts",
        chapter_or_episode_raw="Chapter 2",
    ),
    _demo_item(
        "3",
        title="Sky Tale Episode 5",
        series_slug="sky-tale",
        chapter_slug="ch5",
        publish_date="2026-03-15",
        author_or_group="Studio B",
        tags=["fantasy", "soft", "longform"],
        description_raw="Fantasy road story.",
        series_name_raw="Sky Tale",
        chapter_or_episode_raw="Episode 5",
    ),
    _demo_item(
        "4",
        title="Dark Dungeon Chapter 9",
        series_slug="dark-dungeon",
        chapter_slug="ch9",
        publish_date="2026-03-02",
        author_or_group="Studio C",
        tags=["dark", "action", "explicit", "longform"],
        description_raw="Dark action arc.",
        series_name_raw="Dark Dungeon",
        chapter_or_episode_raw="Chapter 9",
    ),
]


def _build_demo_html(items: list[dict]) -> str:
    nodes: list[str] = ["<html><body>"]
    for item in items:
        nodes.append(
            """
<div class="item" data-id="{source_id}">
  <a class="title" href="{detail_url}">{title}</a>
  <img src="{cover_url}" />
  <span class="date">{publish_date}</span>
  <span class="author">{author_or_group}</span>
  <span class="tags">{tags}</span>
  <p class="desc">{description_raw}</p>
  <span class="series">{series_name_raw}</span>
  <span class="chapter">{chapter_or_episode_raw}</span>
</div>
""".format(
                source_id=escape(item["source_id"]),
                detail_url=escape(item["detail_url"]),
                title=escape(item["title"]),
                cover_url=escape(item["cover_url"]),
                publish_date=escape(item["publish_time"].date().isoformat()),
                author_or_group=escape(item["author_or_group"]),
                tags=escape(",".join(item["tags"])),
                description_raw=escape(item["description_raw"]),
                series_name_raw=escape(item["series_name_raw"]),
                chapter_or_episode_raw=escape(item["chapter_or_episode_raw"]),
            )
        )
    nodes.append("</body></html>")
    return "".join(nodes)


DEMO_HTML = _build_demo_html(DEMO_ITEMS)


def get_demo_item(series_slug: str, chapter_slug: str) -> dict | None:
    for item in DEMO_ITEMS:
        if item["series_slug"] == series_slug and item["chapter_slug"] == chapter_slug:
            return {
                **item,
                "tags_raw": ",".join(item["tags"]),
            }
    return None


class DemoSourceAdapter(BaseAdapter):
    name = "demo-source"

    def supports(self, url: str, source_type: str) -> bool:
        return url.startswith("demo://") or source_type == "demo"

    def validate_source(self, url: str, context: SourceContext) -> bool:
        return url.startswith("demo://")

    def detect_source_name(self, url: str, context: SourceContext | None = None) -> str:
        if url.startswith("demo://"):
            return "demo-source"
        return urlparse(url).netloc

    def fetch_recent_items(self, url: str, context: SourceContext) -> list[dict]:
        if not self.validate_source(url, context):
            raise ValueError("Invalid source URL")
        if url.startswith("demo://"):
            html = DEMO_HTML
        else:
            response = requests.get(
                url,
                timeout=settings.request_timeout_seconds,
                headers={"User-Agent": settings.adapter_user_agent},
            )
            response.raise_for_status()
            html = response.text
        return self._parse_html(html)[: context.max_items]

    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[dict] = []
        for node in soup.select(".item"):
            title_link = node.select_one(".title")
            date_text = (node.select_one(".date").get_text(strip=True) if node.select_one(".date") else "")
            items.append(
                {
                    "source_id": node.get("data-id") or title_link.get("href", ""),
                    "title": title_link.get_text(strip=True),
                    "detail_url": title_link.get("href", ""),
                    "cover_url": node.select_one("img").get("src", "") if node.select_one("img") else "",
                    "publish_time": datetime.fromisoformat(date_text) if date_text else None,
                    "author_or_group": node.select_one(".author").get_text(strip=True) if node.select_one(".author") else "",
                    "tags_raw": node.select_one(".tags").get_text(strip=True) if node.select_one(".tags") else "",
                    "description_raw": node.select_one(".desc").get_text(strip=True) if node.select_one(".desc") else "",
                    "series_name_raw": node.select_one(".series").get_text(strip=True) if node.select_one(".series") else "",
                    "chapter_or_episode_raw": node.select_one(".chapter").get_text(strip=True) if node.select_one(".chapter") else "",
                }
            )
        if not items:
            raise ValueError("No content items found from source")
        return items
