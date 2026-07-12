from typing import Optional
from discord import Client, Guild, VoiceChannel, User, VoiceClient, Member
from ...wrapper import Action
from ....events import EventBroker
from ....state_types import AudioPlayerState
from .utils import MuxPCMAudio, HIGH_BITRATE_KBPS, FFMPEG_OPTIONS

__all__ = ["join_voice", "join_voice_to_user"]

@Action
async def join_voice(broker: EventBroker, client: Client, state: AudioPlayerState, guild: Guild, channel: VoiceChannel) -> tuple[bool, AudioPlayerState]:
    vc: Optional[VoiceClient] = guild.voice_client
    new_state: AudioPlayerState = state.model_copy()

    if vc is None and new_state.mixer is not None:
        try:
            new_state.mixer.cleanup()
        except Exception:
            pass
        new_state.mixer = None

    if vc is not None:
        if vc.channel.id != channel.id:
            await vc.move_to(channel)
            channel_bitrate: int = channel.bitrate * 1000 if channel else HIGH_BITRATE_KBPS
            bitrate = min(channel_bitrate, HIGH_BITRATE_KBPS)
            vc.play(state.mixer, bitrate=bitrate, signal_type="music")
            return True, new_state
        return False, new_state

    vc = await channel.connect()
    channel_bitrate = vc.channel.bitrate // 1000 if vc.channel else HIGH_BITRATE_KBPS
    bitrate: int = min(channel_bitrate, HIGH_BITRATE_KBPS)
    mixer: MuxPCMAudio = MuxPCMAudio(**FFMPEG_OPTIONS)
    vc.play(mixer, bitrate=bitrate, signal_type="music")
    new_state.mixer = mixer
    return True, new_state

@Action
async def join_voice_to_user(broker: EventBroker, client: Client, state: AudioPlayerState, guild: Guild, user: User) -> tuple[bool, AudioPlayerState]:
    member: Optional[Member] = guild.get_member(user.id)
    if member is None or member.voice is None or member.voice.channel is None:
        return False, state
    return await join_voice(broker, client, state, guild, member.voice.channel)