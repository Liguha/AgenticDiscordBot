from __future__ import annotations
from discord import Guild, Client
from .commands import InteractionCommand, MessageCommand, CallbackPostprocessing
from ..base import Router, DiscordGuildRouter
from ..state_manager import GroupState
from ...events import EventBroker, DiscordMessageEvent, DiscordInteractionEvent, DiscordCallabackEvent
from ...state_types import PrefixState

__all__ = ["DiscordCLIRouter", "DiscordCLIGuildRouter"]

class DiscordCLIGuildRouter(DiscordGuildRouter):
    async def new_router(self, guild: Guild) -> DiscordCLIRouter:
        return DiscordCLIRouter(self.client, 
                                guild, 
                                self.broker, 
                                self.group_state[DiscordCLIRouter.group_from_context(guild)]
                               )

class DiscordCLIRouter(Router):
    def __init__(self, client: Client, guild: Guild, broker: EventBroker, group_state: GroupState) -> None:
        super().__init__(broker, group_state)
        self._guild = guild
        self._client = client
        if self.group_state["prefix"][...] is None: # hardcode for specific service command
            self.group_state["prefix"][...] = PrefixState()

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
        if func is None:
            async with msg.channel.typing():
                await msg.reply(f"Command `{cmd}` doesn't exist.")
            return
        kwds = func.parse_arguments(self.client, msg, args)
        state = self.group_state[func.group_id][...]
        self.group_state[func.group_id][...] = await func(self.broker, self.client, msg, state, **kwds)

    async def route_interaction(self, interact_event: DiscordInteractionEvent) -> None:
        interaction = interact_event.payload
        name = getattr(interaction.command, "name")
        if name is None:
            return
        func = InteractionCommand.from_name(name)
        if func is None:
            await interaction.response.defer(thinking=True)
            await interaction.followup.send(f"Command `{name}` doesn't exist.")
            return
        kwds = {x["name"]: x["value"] for x in interaction.data.get("options", {})} # TODO: generalize rudimentary parser
        state = self.group_state[func.group_id][...]
        self.group_state[func.group_id][...] = await func.evaluate(self.broker, interaction, state, **kwds)

    async def route_callback(self, callback_event: DiscordCallabackEvent) -> None:
        func = CallbackPostprocessing.from_name(callback_event.name)
        if func is None:
            return
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