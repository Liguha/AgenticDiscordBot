from __future__ import annotations
from discord import Guild, Client
from .tools import Toolset
from .context_manager import ContextManager
from .api_session import LLMSession
from .config import TEXT_CHAT_MODEL
from ..base import Router, DiscordGuildRouter
from ..state_manager import GroupState
from ...events import EventBroker, DiscordMessageEvent, AgentToolEvent
from ...state_types import LLMContextState

__all__ = ["DiscordAgentRouter", "DiscordAgentGuildRouter"]

class DiscordAgentGuildRouter(DiscordGuildRouter):
    async def new_router(self, guild: Guild) -> DiscordAgentRouter:
        return DiscordAgentRouter(self.client, 
                                  guild, 
                                  self.broker, 
                                  self.group_state[DiscordAgentRouter.group_from_context(guild)]
                                 )

class DiscordAgentRouter(Router):
    def __init__(self, client: Client, guild: Guild, broker: EventBroker, group_state: GroupState) -> None:
        super().__init__(broker, group_state)
        self._guild = guild
        self._client = client
        if self.group_state["llm"][...] is None: # hardcode for specific service command
            self.group_state["llm"][...] = LLMContextState()
        self._all_tools = Toolset(self.broker, self.client, self.guild)
        self._text_llm = LLMSession(self.contexts.text_chat_ctx,     # (weird) inplace state edit
                                    self._all_tools,
                                    TEXT_CHAT_MODEL)    # TODO: add system prompt

    @property
    def contexts(self) -> LLMContextState:
        return self.group_state["llm"][...]
    
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
        if (msg.author == self.client.user or 
                msg.content.startswith(self.message_prefix) or
                self.client.user.id not in [m.id for m in msg.mentions]):
            return
        user_name = msg.author.name
        user_id = msg.author.id
        content = msg.content
        print(f"USER: {content}")
        async with msg.channel.typing():
            response = await self._text_llm.send_message(user_name, user_id, content)
            print(f"LLM: {response}")
            await msg.reply(response)

    async def route_tool(self, tool_event: AgentToolEvent) -> None:
        payload = tool_event.payload
        print(f"ROUTE TOOL: {payload}")
        gid = payload.tool.group_id
        state = self.group_state[gid][...]
        self.group_state[gid][...] = await self._all_tools.router_call(state, payload)

    async def start(self) -> None:
        msg_key = DiscordMessageEvent.key_from_context(self.guild)
        tool_key = AgentToolEvent.key_from_context(self.guild)
        self._sub_msg = self.broker.subscribe(msg_key, self.route_message)
        self._sub_tool = self.broker.subscribe(tool_key, self.route_tool)
        print(f"SUBSCRIBED WITH {tool_key}")

    async def stop(self) -> None:
        self._sub_msg.cancel()
        self._sub_tool.cancel()