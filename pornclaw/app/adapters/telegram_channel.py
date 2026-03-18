from __future__ import annotations

import asyncio
import re
from typing import Any, Callable
from urllib.parse import urlparse

from app.adapters.base import BaseAdapter, SourceContext
from app.config import settings
from app.utils.datetime import coerce_utc_naive


class TelegramChannelAdapter(BaseAdapter):
    name = "telegram-channel"

    def __init__(
        self,
        client_factory: Callable[[SourceContext], Any] | None = None,
        credential_resolver: Callable[[str | None], dict[str, str] | None] | None = None,
    ) -> None:
        self.client_factory = client_factory
        self.credential_resolver = credential_resolver or self._resolve_credentials

    def supports(self, url: str, source_type: str) -> bool:
        host = urlparse(url).netloc.lower()
        return host in {"t.me", "telegram.me"} and source_type in {"auto", "telegram"}

    def validate_source(self, url: str, context: SourceContext) -> bool:
        username = self._extract_username(url)
        return bool(username)

    def detect_source_name(self, url: str, context: SourceContext | None = None) -> str:
        return "telegram"

    def fetch_recent_items(self, url: str, context: SourceContext) -> list[dict]:
        if not self.validate_source(url, context):
            raise ValueError("Invalid Telegram public channel URL")
        credentials = self.credential_resolver(context.credential_profile)
        if credentials is None and self.client_factory is None:
            raise ValueError("Telegram credentials are not configured")
        username = self._extract_username(url)
        client = self.client_factory(context) if self.client_factory else self._build_client(credentials or {})
        if client is None:
            raise ValueError("Telegram credentials are not configured")
        items = asyncio.run(self._fetch_public_channel_messages(client, username, context.max_items))
        return items

    async def _fetch_public_channel_messages(self, client: Any, username: str, limit: int) -> list[dict]:
        if hasattr(client, "connect"):
            await client.connect()
        entity = await client.get_entity(username)
        messages = await client.get_messages(entity, limit=limit)
        items = [self._map_message(entity, username, message) for message in messages if message is not None]
        if hasattr(client, "disconnect"):
            await client.disconnect()
        return items

    def _map_message(self, entity: Any, username: str, message: Any) -> dict:
        raw_text = getattr(message, "message", "") or ""
        hashtags = re.findall(r"#([A-Za-z0-9_]+)", raw_text)
        title = re.sub(r"#\w+", "", raw_text).strip().splitlines()[0] if raw_text.strip() else f"Message {message.id}"
        return {
            "source_id": f"{username}:{message.id}",
            "title": title or f"Message {message.id}",
            "detail_url": f"https://t.me/{username}/{message.id}",
            "cover_url": "",
            "publish_time": coerce_utc_naive(getattr(message, "date", None)),
            "author_or_group": getattr(entity, "title", username),
            "tags_raw": hashtags,
            "description_raw": raw_text,
            "series_name_raw": getattr(entity, "title", username),
            "chapter_or_episode_raw": "",
        }

    def _extract_username(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.netloc.lower() not in {"t.me", "telegram.me"}:
            return ""
        path = parsed.path.strip("/")
        if not path or path.startswith(("+", "joinchat")) or path.startswith("c/"):
            return ""
        if path.startswith("s/"):
            path = path[2:]
        parts = path.split("/")
        return parts[0] if parts else ""

    def _resolve_credentials(self, profile: str | None) -> dict[str, str] | None:
        effective_profile = profile or "telegram_default"
        if effective_profile != "telegram_default":
            return None
        if not settings.telegram_api_id or not settings.telegram_api_hash:
            return None
        return {
            "api_id": settings.telegram_api_id,
            "api_hash": settings.telegram_api_hash,
            "session_string": settings.telegram_session_string,
            "session_file": settings.telegram_session_file,
        }

    def _build_client(self, credentials: dict[str, str]) -> Any:
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except Exception as exc:
            raise ValueError("Telethon is not installed") from exc
        session_string = credentials.get("session_string")
        session_file = credentials.get("session_file") or "pornclaw_telegram.session"
        session = StringSession(session_string) if session_string else session_file
        return TelegramClient(session, int(credentials["api_id"]), credentials["api_hash"])
