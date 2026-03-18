from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceContext:
    source_type: str = "auto"
    credential_profile: str | None = None
    cookies_mode: str = "none"
    max_items: int = 20
    fetch_detail_pages: bool = True
    channel_or_feed_hint: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, source_type: str = "auto", context: dict[str, Any] | None = None) -> "SourceContext":
        payload = dict(context or {})
        return cls(
            source_type=source_type or "auto",
            credential_profile=payload.pop("credential_profile", None),
            cookies_mode=payload.pop("cookies_mode", "none"),
            max_items=int(payload.pop("max_items", 20) or 20),
            fetch_detail_pages=bool(payload.pop("fetch_detail_pages", True)),
            channel_or_feed_hint=payload.pop("channel_or_feed_hint", None),
            extra=payload,
        )

    def safe_metadata(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "credential_profile": self.credential_profile,
            "cookies_mode": self.cookies_mode,
            "max_items": self.max_items,
            "fetch_detail_pages": self.fetch_detail_pages,
            "channel_or_feed_hint": self.channel_or_feed_hint,
            **self.extra,
        }


class BaseAdapter(ABC):
    name = "base"

    @abstractmethod
    def supports(self, url: str, source_type: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def validate_source(self, url: str, context: SourceContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch_recent_items(self, url: str, context: SourceContext) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def detect_source_name(self, url: str, context: SourceContext | None = None) -> str:
        raise NotImplementedError
