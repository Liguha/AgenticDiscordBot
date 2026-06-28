from dataclasses import dataclass
from collections.abc import Callable, Awaitable
from discord import Client, Guild, TextChannel, VoiceChannel
from ..enums import PlatformEnum, TriggerEnum

__all__ = ["ActionResult", "ExecutionContext", "DiscordData"]

@dataclass(frozen=True)
class ActionResult[DataType]:
    data: DataType
    deffered_calls: list[Callable[[], Awaitable[None]]]

@dataclass(frozen=True)
class ExecutionContext[DataType]:
    platform: PlatformEnum
    trigger: TriggerEnum
    data: DataType

@dataclass(frozen=True)
class DiscordData:
    client: Client
    guild: Guild
    text_channel: TextChannel | None = None
    voice_channel: VoiceChannel | None = None
