from datetime import datetime
from types import SimpleNamespace

import pytest

from app.adapters.base import SourceContext
from app.adapters.demo_source import DemoSourceAdapter
from app.adapters.generic_template import GenericTemplateAdapter
from app.adapters.pornhub import PornhubAdapter
from app.adapters.registry import get_adapter_for_source
from app.adapters.telegram_channel import TelegramChannelAdapter


CARD_LISTING_HTML = """
<html><body>
  <article class="card">
    <a class="title" href="/series/alpha-1">Alpha Mission Chapter 1</a>
    <img src="/images/alpha.jpg" />
    <time datetime="2026-03-18T09:00:00">2026-03-18</time>
    <div class="tags"><a>fantasy</a><a>drama</a></div>
    <div class="author">Studio One</div>
    <p class="summary">Fantasy drama story</p>
    <span class="series">Alpha Mission</span>
  </article>
</body></html>
"""

LISTING_WITH_DETAIL_HTML = """
<html><body>
  <ul>
    <li class="post">
      <a class="title" href="/posts/beta-7">Beta Nights Episode 7</a>
      <time datetime="2026-03-17T12:00:00">2026-03-17</time>
    </li>
  </ul>
</body></html>
"""

DETAIL_HTML = """
<html><body>
  <h1>Beta Nights Episode 7</h1>
  <img class="cover" src="/covers/beta.jpg" />
  <div class="tags"><a>school</a><a>romance</a></div>
  <div class="author">Circle Beta</div>
  <div class="description">A school romance update.</div>
  <div class="series-name">Beta Nights</div>
</body></html>
"""

PORNHUB_LISTING_HTML = """
<html><body>
  <ul id="videoCategory">
    <li class="pcVideoListItem js-pop videoBox" data-video-vkey="ph123">
      <a class="linkVideoThumb" href="/view_video.php?viewkey=ph123">
        <img data-mediumthumb="https://cdn.example/ph123.jpg" />
      </a>
      <span class="title"><a title="Creator Showcase Episode 3">Creator Showcase Episode 3</a></span>
      <span class="usernameWrap"><a>Model Hub</a></span>
      <var class="duration">12:00</var>
    </li>
  </ul>
</body></html>
"""


def test_demo_adapter_returns_normalized_fields() -> None:
    adapter = DemoSourceAdapter()

    items = adapter.fetch_recent_items("demo://seed", SourceContext(source_type="demo"))

    assert items
    required = {
        "source_id",
        "title",
        "detail_url",
        "cover_url",
        "publish_time",
        "author_or_group",
        "tags_raw",
        "description_raw",
        "series_name_raw",
        "chapter_or_episode_raw",
    }
    assert required.issubset(items[0].keys())


def test_adapter_registry_selects_expected_adapter_for_source_type_and_url() -> None:
    assert isinstance(
        get_adapter_for_source("demo://seed", SourceContext(source_type="demo")),
        DemoSourceAdapter,
    )
    assert isinstance(
        get_adapter_for_source(
            "https://example.com/feed",
            SourceContext(source_type="generic_template"),
        ),
        GenericTemplateAdapter,
    )
    assert isinstance(
        get_adapter_for_source(
            "https://www.pornhub.com/video?c=1",
            SourceContext(source_type="auto"),
        ),
        PornhubAdapter,
    )
    assert isinstance(
        get_adapter_for_source(
            "https://t.me/examplechannel",
            SourceContext(source_type="telegram"),
        ),
        TelegramChannelAdapter,
    )


def test_generic_template_adapter_parses_card_style_listing() -> None:
    adapter = GenericTemplateAdapter(
        fetcher=lambda url: CARD_LISTING_HTML,
    )

    items = adapter.fetch_recent_items(
        "https://example.com/feed",
        SourceContext(source_type="generic_template", fetch_detail_pages=False),
    )

    assert len(items) == 1
    assert items[0]["title"] == "Alpha Mission Chapter 1"
    assert items[0]["detail_url"] == "https://example.com/series/alpha-1"
    assert items[0]["cover_url"] == "https://example.com/images/alpha.jpg"
    assert items[0]["author_or_group"] == "Studio One"
    assert items[0]["series_name_raw"] == "Alpha Mission"
    assert "fantasy" in items[0]["tags_raw"]


def test_generic_template_adapter_enriches_from_detail_pages_for_list_style_sites() -> None:
    html_map = {
        "https://example.com/feed": LISTING_WITH_DETAIL_HTML,
        "https://example.com/posts/beta-7": DETAIL_HTML,
    }
    adapter = GenericTemplateAdapter(fetcher=lambda url: html_map[url])

    items = adapter.fetch_recent_items(
        "https://example.com/feed",
        SourceContext(source_type="generic_template", fetch_detail_pages=True),
    )

    assert len(items) == 1
    assert items[0]["detail_url"] == "https://example.com/posts/beta-7"
    assert items[0]["cover_url"] == "https://example.com/covers/beta.jpg"
    assert items[0]["author_or_group"] == "Circle Beta"
    assert items[0]["series_name_raw"] == "Beta Nights"
    assert "romance" in items[0]["tags_raw"]
    assert items[0]["description_raw"] == "A school romance update."


def test_pornhub_adapter_parses_listing_html_snapshot() -> None:
    adapter = PornhubAdapter(fetcher=lambda url: PORNHUB_LISTING_HTML)

    items = adapter.fetch_recent_items(
        "https://www.pornhub.com/model/example/videos",
        SourceContext(source_type="pornhub"),
    )

    assert len(items) == 1
    assert items[0]["source_id"] == "ph123"
    assert items[0]["title"] == "Creator Showcase Episode 3"
    assert items[0]["detail_url"].startswith("https://www.pornhub.com/view_video.php")
    assert items[0]["cover_url"] == "https://cdn.example/ph123.jpg"
    assert items[0]["author_or_group"] == "Model Hub"


def test_telegram_adapter_maps_public_channel_messages_to_item_schema() -> None:
    fake_message = SimpleNamespace(
        id=15,
        message="Episode 15 #romance #school",
        date=datetime(2026, 3, 18, 8, 0, 0),
        photo=None,
        media=SimpleNamespace(),
    )

    class FakeClient:
        async def get_entity(self, username: str):
            return SimpleNamespace(title="Example Channel", username=username)

        async def get_messages(self, entity, limit: int):
            return [fake_message]

    adapter = TelegramChannelAdapter(client_factory=lambda context: FakeClient())

    items = adapter.fetch_recent_items(
        "https://t.me/examplechannel",
        SourceContext(source_type="telegram", max_items=5, credential_profile="telegram_default"),
    )

    assert len(items) == 1
    assert items[0]["source_id"] == "examplechannel:15"
    assert items[0]["title"] == "Episode 15"
    assert items[0]["detail_url"] == "https://t.me/examplechannel/15"
    assert items[0]["author_or_group"] == "Example Channel"
    assert set(items[0]["tags_raw"]) == {"romance", "school"}


def test_telegram_adapter_requires_server_side_credentials() -> None:
    adapter = TelegramChannelAdapter(
        client_factory=lambda context: None,
        credential_resolver=lambda profile: None,
    )

    with pytest.raises(ValueError, match="Telegram credentials are not configured"):
        adapter.fetch_recent_items(
            "https://t.me/examplechannel",
            SourceContext(source_type="telegram", credential_profile="telegram_default"),
        )
