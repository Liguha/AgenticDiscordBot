from __future__ import annotations
from asyncio import gather
from discord import Guild, Client
from ..base import Router
from ..state_manager import GroupState
from ...events import EventBroker, DiscordMessageEvent, DiscordGuildJoinEvent
from ...actions import send_message
from ...globals import TriggerEnum

__all__ = ["DiscordCLIRouter", "DiscordCLIGuildRouter"]

class DiscordCLIRouter(Router):
    def __init__(self, client: Client, broker: EventBroker, group_state: GroupState) -> None:
        super().__init__(broker, group_state)
        self._client = client
        self._routers: list[DiscordCLIGuildRouter] = []

    @classmethod
    def group_from_context(cls) -> str:
        return "ds_cli"

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
        self._routers.append(DiscordCLIGuildRouter(self.client, 
                                                   guild, 
                                                   self.broker, 
                                                   self.group_state[DiscordCLIGuildRouter.group_from_context(guild)]
                                                   ))
        await self._routers[-1].start()

    async def stop(self) -> None:
        self._sub.cancel()
        await gather(*[r.stop() for r in self._routers])
        self._routers = []

class DiscordCLIGuildRouter(Router):
    def __init__(self, client: Client, guild: Guild, broker: EventBroker, group_state: GroupState) -> None:
        super().__init__(broker, group_state)
        self._guild = guild
        self._client = client

    @property
    def client(self) -> Client:
        return self._client
    
    @property
    def guild(self) -> Guild:
        return self._guild
    
    @classmethod
    def group_from_context(cls, guild: Guild) -> str:
        return f"{guild.id}"
    
    @property
    def group_id(self) -> str:
        return self.group_from_context(self.guild)

    async def route_message(self, msg_event: DiscordMessageEvent) -> None:
        msg = msg_event.payload
        _, state = await send_message(self.client, None, msg.channel, msg.content)   # echo placeholder

    async def start(self) -> None:
        event_key = DiscordMessageEvent.key_from_context(self.guild)
        self._sub = self.broker.subscribe(event_key, self.route_message)

    async def stop(self) -> None:
        self._sub.cancel()