from __future__ import annotations

from datetime import datetime
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from app.adapters.base import BaseAdapter, SourceContext
from app.config import settings
from app.utils.datetime import coerce_utc_naive


class GenericTemplateAdapter(BaseAdapter):
    name = "generic-template"

    def __init__(self, fetcher: Callable[[str], str] | None = None) -> None:
        self.fetcher = fetcher or self._default_fetch

    def supports(self, url: str, source_type: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if source_type == "generic_template":
            return True
        host = parsed.netloc.lower()
        return source_type == "auto" and "pornhub.com" not in host and host not in {"t.me", "telegram.me"}

    def validate_source(self, url: str, context: SourceContext) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def detect_source_name(self, url: str, context: SourceContext | None = None) -> str:
        return urlparse(url).netloc

    def fetch_recent_items(self, url: str, context: SourceContext) -> list[dict]:
        if not self.validate_source(url, context):
            raise ValueError("Invalid source URL")
        listing_html = self.fetcher(url)
        items = self._parse_listing_html(listing_html, url)
        if not items:
            raise ValueError("No content items found from source")
        if context.fetch_detail_pages:
            items = [self._enrich_item_from_detail(item, context) for item in items]
        return items[: context.max_items]

    def _default_fetch(self, url: str) -> str:
        response = requests.get(
            url,
            timeout=settings.request_timeout_seconds,
            headers={"User-Agent": settings.adapter_user_agent},
        )
        response.raise_for_status()
        return response.text

    def _parse_listing_html(self, html: str, base_url: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        nodes = self._find_candidate_nodes(soup)
        items = [item for node in nodes if (item := self._parse_node(node, base_url))]
        return items

    def _find_candidate_nodes(self, soup: BeautifulSoup) -> list[Tag]:
        selector_groups = [
            "article",
            ".card",
            ".item",
            "li.post",
            "li.article",
            "li",
            ".post",
        ]
        best_nodes: list[Tag] = []
        best_score = -1
        for selector in selector_groups:
            nodes = soup.select(selector)
            score = sum(1 for node in nodes if self._find_title_link(node) is not None)
            if score > best_score:
                best_score = score
                best_nodes = nodes
        return best_nodes

    def _parse_node(self, node: Tag, base_url: str) -> dict | None:
        title_link = self._find_title_link(node)
        if title_link is None:
            return None
        title = title_link.get_text(" ", strip=True) or title_link.get("title", "").strip()
        detail_url = urljoin(base_url, title_link.get("href", ""))
        if not title or not detail_url:
            return None
        time_node = node.select_one("time")
        date_node = node.select_one(".date")
        publish_time = self._parse_publish_time(
            time_node.get("datetime", "") if time_node else (date_node.get_text(strip=True) if date_node else "")
        )
        tags = [
            tag.get_text(" ", strip=True)
            for tag in node.select(".tags a, .tag a, .tags .tag, .tag")
            if tag.get_text(strip=True)
        ]
        description_node = node.select_one(".summary, .description, .desc, p")
        author_node = node.select_one(".author, .username, .postedBy, .usernameWrap a")
        series_node = node.select_one(".series, .series-name")
        img_node = node.select_one("img")
        return {
            "source_id": node.get("data-id") or detail_url,
            "title": title,
            "detail_url": detail_url,
            "cover_url": self._image_src(img_node, base_url),
            "publish_time": publish_time,
            "author_or_group": author_node.get_text(" ", strip=True) if author_node else "",
            "tags_raw": tags,
            "description_raw": description_node.get_text(" ", strip=True) if description_node else "",
            "series_name_raw": series_node.get_text(" ", strip=True) if series_node else "",
            "chapter_or_episode_raw": "",
        }

    def _enrich_item_from_detail(self, item: dict, context: SourceContext) -> dict:
        missing_fields = [
            not item.get("cover_url"),
            not item.get("author_or_group"),
            not item.get("tags_raw"),
            not item.get("description_raw"),
            not item.get("series_name_raw"),
        ]
        if not any(missing_fields):
            return item
        detail_html = self.fetcher(item["detail_url"])
        soup = BeautifulSoup(detail_html, "html.parser")
        img_node = soup.select_one(".cover, .featured-image img, img")
        author_node = soup.select_one(".author, .username, .postedBy, .usernameWrap a")
        description_node = soup.select_one(".description, .summary, .desc, p")
        series_node = soup.select_one(".series-name, .series")
        tags = [
            tag.get_text(" ", strip=True)
            for tag in soup.select(".tags a, .tag a, .tags .tag, .tag")
            if tag.get_text(strip=True)
        ]
        enriched = dict(item)
        enriched["cover_url"] = item.get("cover_url") or self._image_src(img_node, item["detail_url"])
        enriched["author_or_group"] = item.get("author_or_group") or (author_node.get_text(" ", strip=True) if author_node else "")
        enriched["description_raw"] = item.get("description_raw") or (
            description_node.get_text(" ", strip=True) if description_node else ""
        )
        enriched["series_name_raw"] = item.get("series_name_raw") or (
            series_node.get_text(" ", strip=True) if series_node else self._derive_series_name_from_title(item["title"])
        )
        enriched["tags_raw"] = item.get("tags_raw") or tags
        return enriched

    def _find_title_link(self, node: Tag) -> Tag | None:
        selectors = [".title", "h1 a", "h2 a", "h3 a", "a[title]", "a"]
        for selector in selectors:
            element = node.select_one(selector)
            if element and element.get("href"):
                return element
        return None

    def _image_src(self, img_node: Tag | None, base_url: str) -> str:
        if img_node is None:
            return ""
        return urljoin(
            base_url,
            img_node.get("src")
            or img_node.get("data-src")
            or img_node.get("data-original")
            or img_node.get("data-mediumthumb")
            or "",
        )

    def _parse_publish_time(self, raw: str) -> datetime | None:
        cleaned = (raw or "").strip().replace("Z", "+00:00")
        if not cleaned:
            return None
        try:
            return coerce_utc_naive(datetime.fromisoformat(cleaned))
        except ValueError:
            return None

    def _derive_series_name_from_title(self, title: str) -> str:
        for marker in [" Chapter ", " Episode ", " Part "]:
            if marker in title:
                return title.split(marker, 1)[0].strip()
        return title
