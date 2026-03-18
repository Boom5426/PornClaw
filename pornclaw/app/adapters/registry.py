from app.adapters.base import BaseAdapter, SourceContext
from app.adapters.demo_source import DemoSourceAdapter
from app.adapters.generic_template import GenericTemplateAdapter
from app.adapters.pornhub import PornhubAdapter
from app.adapters.telegram_channel import TelegramChannelAdapter


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: list[BaseAdapter] = []

    def register(self, adapter: BaseAdapter) -> None:
        self._adapters.append(adapter)

    def resolve(self, url: str, context: SourceContext) -> BaseAdapter:
        for adapter in self._adapters:
            if adapter.supports(url, context.source_type):
                return adapter
        raise ValueError(f"No adapter available for source_type={context.source_type!r} and url={url!r}")


registry = AdapterRegistry()
registry.register(DemoSourceAdapter())
registry.register(PornhubAdapter())
registry.register(TelegramChannelAdapter())
registry.register(GenericTemplateAdapter())


def get_adapter_for_source(url: str, context: SourceContext) -> BaseAdapter:
    return registry.resolve(url, context)
