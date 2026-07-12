from typing import Optional
from discord import Client, Guild, VoiceClient
from .play_track import play_next_track
from ....wrapper import Action
from .....events import EventBroker
from .....state_types import AudioPlayerState, AudioTrack

__all__ = ["add_track", "skip_track", "remove_range", "toggle_loop"]

@Action
async def add_track(broker: EventBroker, client: Client, state: AudioPlayerState, guild: Guild, track: AudioTrack) -> tuple[None, AudioPlayerState]:
    updated_queue: list[AudioTrack] = list(state.queue)
    updated_queue.append(track)
    new_state: AudioPlayerState = state.model_copy(update={"queue": updated_queue})
    if not state.is_playing:
        _, new_state = await play_next_track._func(broker, client, new_state, guild)
    return None, new_state

@Action
async def skip_track(broker: EventBroker, client: Client, state: AudioPlayerState, guild: Guild) -> tuple[bool, AudioPlayerState]:
    vc: Optional[VoiceClient] = guild.voice_client
    if vc is None or state.mixer is None:
        return False, state
    state.mixer.stop_music()
    reset_state: AudioPlayerState = state.model_copy(update={"is_playing": False})
    _, new_state = await play_next_track._func(broker, client, reset_state, guild)
    return True, new_state

@Action
async def remove_range(broker: EventBroker, client: Client, state: AudioPlayerState, start_idx: int, end_idx: int) -> tuple[int, AudioPlayerState]:
    updated_queue: list[AudioTrack] = list(state.queue)
    initial_length: int = len(updated_queue)
    try:
        del updated_queue[start_idx:end_idx]
        removed_count: int = initial_length - len(updated_queue)
        new_state: AudioPlayerState = state.model_copy(update={"queue": updated_queue})
        return removed_count, new_state
    except Exception:
        return 0, state

@Action
async def toggle_loop(broker: EventBroker, client: Client, state: AudioPlayerState) -> tuple[bool, AudioPlayerState]:
    new_loop_status: bool = not state.is_looping
    new_state: AudioPlayerState = state.model_copy(update={"is_looping": new_loop_status})
    return new_loop_status, new_state