import os
from dataclasses import dataclass, field
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    app_name: str = "PornClaw"
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'pornclaw.db'}"))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "dev-secret"))
    request_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")))
    request_retries: int = field(default_factory=lambda: int(os.getenv("REQUEST_RETRIES", "2")))
    adapter_user_agent: str = field(
        default_factory=lambda: os.getenv(
            "ADAPTER_USER_AGENT",
            "PornClaw/2.0 (+https://github.com/Boom5426/PornClaw)",
        )
    )
    candidate_sample_size: int = field(default_factory=lambda: int(os.getenv("CANDIDATE_SAMPLE_SIZE", "8")))
    recommendation_limit: int = field(default_factory=lambda: int(os.getenv("RECOMMENDATION_LIMIT", "5")))
    default_source_type: str = field(default_factory=lambda: os.getenv("DEFAULT_SOURCE_TYPE", "auto"))
    source_types: list[str] = field(
        default_factory=lambda: ["auto", "demo", "generic_template", "pornhub", "telegram"]
    )
    telegram_api_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_API_ID", ""))
    telegram_api_hash: str = field(default_factory=lambda: os.getenv("TELEGRAM_API_HASH", ""))
    telegram_session_string: str = field(default_factory=lambda: os.getenv("TELEGRAM_SESSION_STRING", ""))
    telegram_session_file: str = field(default_factory=lambda: os.getenv("TELEGRAM_SESSION_FILE", ""))
    playwright_headless: bool = field(
        default_factory=lambda: os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() != "false"
    )
    standard_tags: list[str] = field(
        default_factory=lambda: [
            "romance",
            "school",
            "fantasy",
            "action",
            "drama",
            "longform",
            "shortform",
            "dark",
            "soft",
            "explicit",
            "taboo",
        ]
    )
    tag_aliases: dict[str, list[str]] = field(
        default_factory=lambda: {
            "romance": ["romance", "love", "恋爱", "纯爱"],
            "school": ["school", "academy", "校园", "学园"],
            "fantasy": ["fantasy", "magic", "异世界", "奇幻"],
            "action": ["action", "battle", "combat", "战斗"],
            "drama": ["drama", "story", "剧情"],
            "longform": ["long", "series", "chapter", "长篇", "连载"],
            "shortform": ["short", "one-shot", "短篇", "短篇集"],
            "dark": ["dark", "ntr", "gore", "阴暗"],
            "soft": ["soft", "sweet", "温柔", "轻松"],
            "explicit": ["explicit", "adult", "18+", "露骨"],
            "taboo": ["taboo", "forbidden", "禁忌"],
        }
    )
    freshness_keywords: dict[str, list[str]] = field(
        default_factory=lambda: {
            "recent": ["recent", "latest", "最近", "最近一周", "新"],
            "archive": ["old", "classic", "旧作", "老作品"],
        }
    )


settings = Settings()
