from __future__ import annotations

from datetime import datetime
from typing import Callable
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.adapters.base import BaseAdapter, SourceContext
from app.config import settings


class PornhubAdapter(BaseAdapter):
    name = "pornhub"

    def __init__(self, fetcher: Callable[[str], str] | None = None) -> None:
        self.fetcher = fetcher

    def supports(self, url: str, source_type: str) -> bool:
        return self._matches_supported_host(url) and source_type in {"auto", "pornhub"}

    def validate_source(self, url: str, context: SourceContext) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and self._matches_supported_host(url)

    def detect_source_name(self, url: str, context: SourceContext | None = None) -> str:
        return "pornhub"

    def fetch_recent_items(self, url: str, context: SourceContext) -> list[dict]:
        if not self.validate_source(url, context):
            raise ValueError("Invalid Pornhub source URL")
        html = self.fetcher(url) if self.fetcher else self._fetch_html(url)
        items = self._parse_listing_html(html, url)
        if not items:
            raise ValueError("No Pornhub items found from source")
        return items[: context.max_items]

    def _fetch_html(self, url: str) -> str:
        if self.fetcher:
            return self.fetcher(url)
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=settings.playwright_headless)
                page = browser.new_page(user_agent=settings.adapter_user_agent)
                page.goto(url, wait_until="networkidle", timeout=settings.request_timeout_seconds * 1000)
                html = page.content()
                browser.close()
                return html
        except Exception:
            response = requests.get(
                url,
                timeout=settings.request_timeout_seconds,
                headers={"User-Agent": settings.adapter_user_agent},
            )
            response.raise_for_status()
            return response.text

    def _parse_listing_html(self, html: str, base_url: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        nodes = soup.select("li.pcVideoListItem, li.videoBox, li[data-video-vkey]")
        items = []
        for node in nodes:
            thumb_link = node.select_one("a.linkVideoThumb, a")
            href = thumb_link.get("href", "") if thumb_link else ""
            detail_url = urljoin(base_url, href)
            title_link = node.select_one(".title a, span.title a, a[title]")
            title = ""
            if title_link:
                title = title_link.get("title", "") or title_link.get_text(" ", strip=True)
            source_id = node.get("data-video-vkey") or self._extract_viewkey(href) or detail_url
            img_node = node.select_one("img")
            author_node = node.select_one(".usernameWrap a, .username a, .usernameWrap")
            items.append(
                {
                    "source_id": source_id,
                    "title": title,
                    "detail_url": detail_url,
                    "cover_url": img_node.get("data-mediumthumb", "") or img_node.get("src", "") if img_node else "",
                    "publish_time": None,
                    "author_or_group": author_node.get_text(" ", strip=True) if author_node else "",
                    "tags_raw": [],
                    "description_raw": "",
                    "series_name_raw": "",
                    "chapter_or_episode_raw": "",
                }
            )
        return [item for item in items if item["title"] and item["detail_url"]]

    def _extract_viewkey(self, href: str) -> str:
        query = parse_qs(urlparse(href).query)
        return query.get("viewkey", [""])[0]

    def _matches_supported_host(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return host == "pornhub.com" or host.endswith(".pornhub.com")
