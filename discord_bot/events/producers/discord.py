from collections.abc import Callable, Awaitable
from typing import Any
from functools import wraps
from discord import Client, Message, Guild
from .base import EventProducer
from ..event_models import DiscordMessageEvent, DiscordGuildJoinEvent
from ..event_broker import EventBroker

__all__ = ["DiscrordEventProducer"]

def discord_event[**Args](func: Callable[Args, Awaitable[None]]) -> Callable[Args, Awaitable[None]]:
    func._is_event_ = True
    return func

class DiscrordEventProducer(EventProducer):
    def __init__(self, client: Client, broker: EventBroker) -> None:
        super().__init__(broker)
        self._active = False
        self._client = client
        self._listened: set[str] = set()

    def _wrap_conditional[**Args](self, func: Callable[Args, Awaitable[None]]) -> Callable[Args, Awaitable[None]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwds: Any) -> None:
            if self._active:
                return await func(*args, **kwds)
            return None
        return wrapper

    @property
    def client(self) -> Client:
        return self._client
    
    @discord_event
    async def on_message(self, msg: Message) -> None:
        if msg.author == self._client.user:
            return
        await self.broker.publish(DiscordMessageEvent(msg, msg.guild))

    @discord_event
    async def on_guild_join(self, guild: Guild) -> None:
        await self.broker.publish(DiscordGuildJoinEvent(guild))
    
    async def start(self) -> None:
        for name in dir(self):
            attr = getattr(self, name)
            if not getattr(attr, "_is_event_", False) or name in self._listened:
                continue
            method = self._wrap_conditional(attr)
            self._listened.add(name)
            self._client.event(method)
        self._active = True
        
    async def stop(self) -> None:
        self._active = False