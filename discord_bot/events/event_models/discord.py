from dataclasses import dataclass
from typing import ClassVar
from discord import Message, Guild, Interaction
from .base import Event

__all__ = [
    "DiscordEvent", 
    "DiscordInGuildEvent", 
    "DiscordGuildJoinEvent", 
    "DiscordMessageEvent",
    "DiscordInteractionEvent"
]

class DiscordEvent[PayloadType](Event[PayloadType]):    # just for typing
    label: ClassVar[str] = "general"

@dataclass
class DiscordGuildJoinEvent(DiscordEvent[Guild]):
    label: ClassVar[str] = "guild"

    @classmethod
    def key_from_context(cls) -> str:
        return f"ds.{cls.label}"

@dataclass(init=False)
class DiscordInGuildEvent[PayloadType](DiscordEvent[PayloadType]):
    guild: Guild

    def __init__(self, payload: PayloadType, guild: Guild) -> None:
        self.payload = payload
        self.guild = guild

    @property
    def key(self) -> str:
        return self.key_from_context(self.guild)
    
    @classmethod
    def key_from_context(cls, guild: Guild) -> str:
        return f"ds.{cls.label}.{guild.id}"
    
class DiscordMessageEvent(DiscordInGuildEvent[Message]):
    label: ClassVar[str] = "msg"

class DiscordInteractionEvent(DiscordInGuildEvent[Interaction]):
    label: ClassVar[str] = "inter"
