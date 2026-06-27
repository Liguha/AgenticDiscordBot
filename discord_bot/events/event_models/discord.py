from dataclasses import dataclass
from typing import ClassVar
from discord import Message, Guild
from .base import Event
from ...enums import PlatformEnum

__all__ = ["DiscordEvent", "DiscordMessageEvent"]

@dataclass(init=False)
class DiscordEvent[PayloadType](Event[PayloadType]):
    guild: Guild
    label: ClassVar[str] = "general"

    def __init__(self, payload: PayloadType, guild: Guild) -> None:
        self.platform = PlatformEnum.DISCORD
        self.payload = payload
        self.guild = guild

    @property
    def key(self) -> str:
        return self.key_from_context(self.guild)
    
    @classmethod
    def key_from_context(cls, guild: Guild) -> str:
        return f"ds.{cls.label}.{guild.id}"
    
class DiscordMessageEvent(DiscordEvent[Message]):
    label: ClassVar[str] = "msg"
