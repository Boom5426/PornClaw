from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.adapters.base import BaseAdapter, SourceContext
from app.config import settings


DEMO_HTML = """
<html><body>
<div class="item" data-id="1">
  <a class="title" href="https://demo.local/series/campus-hearts/ch1">Campus Hearts Chapter 1</a>
  <img src="https://img.demo.local/campus1.jpg" />
  <span class="date">2026-03-16</span>
  <span class="author">Studio A</span>
  <span class="tags">romance,school,drama,longform</span>
  <p class="desc">A school romance drama.</p>
  <span class="series">Campus Hearts</span>
  <span class="chapter">Chapter 1</span>
</div>
<div class="item" data-id="2">
  <a class="title" href="https://demo.local/series/campus-hearts/ch2">Campus Hearts Chapter 2</a>
  <img src="https://img.demo.local/campus2.jpg" />
  <span class="date">2026-03-17</span>
  <span class="author">Studio A</span>
  <span class="tags">romance,school,drama,longform</span>
  <p class="desc">The story continues.</p>
  <span class="series">Campus Hearts</span>
  <span class="chapter">Chapter 2</span>
</div>
<div class="item" data-id="3">
  <a class="title" href="https://demo.local/series/sky-tale/ch5">Sky Tale Episode 5</a>
  <img src="https://img.demo.local/sky.jpg" />
  <span class="date">2026-03-15</span>
  <span class="author">Studio B</span>
  <span class="tags">fantasy,soft,longform</span>
  <p class="desc">Fantasy road story.</p>
  <span class="series">Sky Tale</span>
  <span class="chapter">Episode 5</span>
</div>
<div class="item" data-id="4">
  <a class="title" href="https://demo.local/series/dark-dungeon/ch9">Dark Dungeon Chapter 9</a>
  <img src="https://img.demo.local/dark.jpg" />
  <span class="date">2026-03-02</span>
  <span class="author">Studio C</span>
  <span class="tags">dark,action,explicit</span>
  <p class="desc">Dark action arc.</p>
  <span class="series">Dark Dungeon</span>
  <span class="chapter">Chapter 9</span>
</div>
</body></html>
"""


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
