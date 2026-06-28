from __future__ import annotations
from asyncio import gather, get_running_loop
from discord import Guild, Client
from ..base import Router
from ...events import EventBroker, DiscordMessageEvent
from ...actions import send_message, ExecutionContext, DiscordData
from ...enums import PlatformEnum, TriggerEnum

__all__ = ["DiscordCLIRouter"]

# !!! JUST DEMP PLACEHOLDERS !!!

class DiscordCLIRouter(Router):
    def __init__(self, client: Client, guild: Guild, broker: EventBroker) -> None:
        super().__init__(broker, None)
        self._guild = guild
        self._client = client

    async def route_message(self, msg_event: DiscordMessageEvent) -> None:
        msg = msg_event.payload
        ctx = ExecutionContext(PlatformEnum.DISCORD, TriggerEnum.CLI, 
                               DiscordData(self._client, msg.guild, msg.channel))
        res, _ = await send_message(ctx, None, msg.content)
        await self.execute_serial(res)

    async def start(self) -> None:
        event_key = DiscordMessageEvent.key_from_context(self._guild)
        print(f"Router at {event_key}")
        self._sub = self.broker.subscribe(event_key, self.route_message)

    async def stop(self) -> None:
        self._sub.cancel()