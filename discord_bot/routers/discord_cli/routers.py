from __future__ import annotations
from asyncio import gather
from discord import Guild, Client
from .commands import InteractionCommand, MessageCommand, CallbackPostprocessing
from ..base import Router
from ..state_manager import GroupState
from ...events import EventBroker, DiscordMessageEvent, DiscordGuildJoinEvent, DiscordInteractionEvent, DiscordCallabackEvent
from ...state_types import PrefixState

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
        if self.group_state["prefix"][...] is None: # hardcode for specific service command
            self.group_state["prefix"][...] = PrefixState(prefix=">")

    @property
    def message_prefix(self) -> str:
        return self.group_state["prefix"][...].prefix

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
        content = msg.content
        prefix = self.message_prefix
        if not content.startswith(prefix):
            return
        l = content.lstrip(prefix).split(" ", maxsplit=1)
        cmd, args = l if len(l) == 2 else [l[0], ""]
        func = MessageCommand.from_name(cmd)
        kwds = func.parse_arguments(self.client, msg, args)
        state = self.group_state[func.group_id][...]
        self.group_state[func.group_id][...] = await func(self.broker, self.client, msg, state, **kwds)

    async def route_interaction(self, interact_event: DiscordInteractionEvent) -> None:
        interaction = interact_event.payload
        name = interaction.command.name
        func = InteractionCommand.from_name(name)
        kwds = {x["name"]: x["value"] for x in interaction.data.get("options", {})} # TODO: generalize rudimentary parser
        state = self.group_state[func.group_id][...]
        self.group_state[func.group_id][...] = await func.evaluate(self.broker, interaction, state, **kwds)

    async def route_callback(self, callback_event: DiscordCallabackEvent) -> None:
        func = CallbackPostprocessing.from_name(callback_event.name)
        state = self.group_state[func.group_id][...]
        self.group_state[func.group_id][...] = await func(state, callback_event.payload)

    async def start(self) -> None:
        msg_key = DiscordMessageEvent.key_from_context(self.guild)
        inter_key = DiscordInteractionEvent.key_from_context(self.guild)
        clbk_key = DiscordCallabackEvent.key_from_context(self.guild)
        self._sub_msg = self.broker.subscribe(msg_key, self.route_message)
        self._sub_inter = self.broker.subscribe(inter_key, self.route_interaction)
        self._sub_clbk = self.broker.subscribe(clbk_key, self.route_callback)

    async def stop(self) -> None:
        self._sub_msg.cancel()
        self._sub_inter.cancel()
        self._sub_clbk.cancel()