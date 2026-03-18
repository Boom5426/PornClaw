from app.adapters.base import BaseAdapter, SourceContext
from app.adapters.demo_source import DemoSourceAdapter
from app.adapters.generic_template import GenericTemplateAdapter
from app.adapters.pornhub import PornhubAdapter
from app.adapters.telegram_channel import TelegramChannelAdapter

__all__ = [
    "BaseAdapter",
    "SourceContext",
    "DemoSourceAdapter",
    "GenericTemplateAdapter",
    "PornhubAdapter",
    "TelegramChannelAdapter",
]
