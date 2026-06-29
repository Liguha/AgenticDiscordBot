from dataclasses import dataclass
from discord import Client, Guild, TextChannel, VoiceChannel
from ..globals import TriggerEnum

__all__ = ["ExecutionContext"]

@dataclass(frozen=True)
class ExecutionContext:
    trigger: TriggerEnum
    client: Client
    guild: Guild
    text_channel: TextChannel | None = None
    voice_channel: VoiceChannel | None = None