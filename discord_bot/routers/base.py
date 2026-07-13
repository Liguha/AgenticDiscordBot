from asyncio import gather
from abc import ABC, abstractmethod
from typing import Any
from discord import Client, Guild
from .state_manager import GroupState
from ..events import EventBroker, DiscordGuildJoinEvent

__all__ = ["Router", "DiscordGuildRouter"]

class Router(ABC):
    def __init__(self, broker: EventBroker, group_state: GroupState) -> None:
        self._broker = broker
        self._state = group_state

    @classmethod
    @abstractmethod
    def group_from_context(cls, *args: Any, **kwds: Any) -> str:
        pass

    @property
    def broker(self) -> EventBroker:
        return self._broker
    
    @property
    def group_state(self) -> GroupState:
        return self._state
    
    @property
    @abstractmethod
    def group_id(self) -> str:
        pass
    
    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

class DiscordGuildRouter(Router):
    def __init__(self, client: Client, broker: EventBroker, group_state: GroupState) -> None:
        super().__init__(broker, group_state)
        self._client = client
        self._routers: list[Router] = []

    @classmethod
    def group_from_context(cls) -> str:
        return "guilds"

    @property
    def client(self) -> Client:
        return self._client
    
    @property
    def group_id(self) -> str:
        return self.group_from_context()

    async def start(self) -> None:
        guilds = self.client.fetch_guilds()
        await gather(*[self.add_guild(g) async for g in guilds])
        event_key = DiscordGuildJoinEvent.key_from_context()
        self._sub = self.broker.subscribe(event_key, self.on_guild_add)

    async def on_guild_add(self, guild_event: DiscordGuildJoinEvent) -> None:
        await self.add_guild(guild_event.payload)

    async def add_guild(self, guild: Guild) -> None:
        router = await self.new_router(guild)
        self._routers.append(router)
        await router.start()

    @abstractmethod
    async def new_router(self, guild: Guild) -> Router:
        pass

    async def stop(self) -> None:
        self._sub.cancel()
        await gather(*[r.stop() for r in self._routers])
        self._routers = []