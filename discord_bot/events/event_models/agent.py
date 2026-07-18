from __future__ import annotations
from typing import Any, TYPE_CHECKING
from discord import Guild
from dataclasses import dataclass
from .base import Event
if TYPE_CHECKING:
    from ...routers.discord_agent.tools import Tool

__all__ = [
    "AgentToolPayload",
    "AgentToolEvent"
]

@dataclass
class AgentToolPayload:
    call_id: int
    tool: Tool
    args: tuple[Any]
    kwds: dict[str, Any]

@dataclass(init=False)
class AgentToolEvent(Event[AgentToolPayload]):
    guild: Guild

    def __init__(self, guild: Guild, payload: AgentToolPayload) -> None:
        self.payload = payload
        self.guild = guild

    @property
    def key(self) -> str:
        return self.key_from_context(self.guild)
    
    @classmethod
    def key_from_context(cls, guild: Guild) -> str:
        return f"agt.tool.{guild.id}"
