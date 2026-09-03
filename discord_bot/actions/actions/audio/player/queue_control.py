from typing import Optional
from discord import Client, Guild
from discord.voice import VoiceClient
from .play_track import play_next_track
from ....wrapper import Action
from .....events import EventBroker
from .....state_types import AudioPlayerState
from .....return_types import AudioTrack

__all__ = [
    "add_track", "add_tracks_many", "skip_track", "remove_range",
    "remove_by_indices", "remove_by_title", "move_track", "toggle_loop"
]

@Action
async def add_track(broker: EventBroker, client: Client, state: AudioPlayerState, guild: Guild, track: AudioTrack) -> tuple[None, AudioPlayerState]:
    updated_queue: list[AudioTrack] = list(state.queue)
    updated_queue.append(track)
    new_state: AudioPlayerState = state.model_copy(update={"queue": updated_queue})
    if not state.is_playing:
        _, new_state = await play_next_track._func(broker, client, new_state, guild)
    return None, new_state

@Action
async def add_tracks_many(broker: EventBroker, client: Client, state: AudioPlayerState, guild: Guild, tracks: list[AudioTrack], position: int | None = None) -> tuple[list[AudioTrack], AudioPlayerState]:
    updated_queue: list[AudioTrack] = list(state.queue)
    new_tracks: list[AudioTrack] = list(tracks)
    if position is None:
        updated_queue.extend(new_tracks)
    else:
        bound: int = max(0, min(position, len(updated_queue)))
        updated_queue[bound:bound] = new_tracks
    new_state: AudioPlayerState = state.model_copy(update={"queue": updated_queue})
    if not state.is_playing:
        _, new_state = await play_next_track._func(broker, client, new_state, guild)
    return new_tracks, new_state

@Action
async def remove_by_indices(broker: EventBroker, client: Client, state: AudioPlayerState, indices: list[int]) -> tuple[list[AudioTrack], AudioPlayerState]:
    updated_queue: list[AudioTrack] = list(state.queue)
    removed: list[AudioTrack] = []
    for idx in sorted({i for i in indices if 0 <= i < len(updated_queue)}, reverse=True):
        removed.append(updated_queue.pop(idx))
    return removed, state.model_copy(update={"queue": updated_queue})

@Action
async def remove_by_title(broker: EventBroker, client: Client, state: AudioPlayerState, patterns: list[str]) -> tuple[list[AudioTrack], AudioPlayerState]:
    needles: list[str] = [p.strip().lower() for p in patterns if p and p.strip()]
    def matches(track: AudioTrack) -> bool:
        title: str = track.title.lower()
        return any(n in title for n in needles)
    updated_queue: list[AudioTrack] = [t for t in state.queue if not matches(t)]
    removed: list[AudioTrack] = [t for t in state.queue if matches(t)]
    return removed, state.model_copy(update={"queue": updated_queue})

@Action
async def move_track(broker: EventBroker, client: Client, state: AudioPlayerState, from_idx: int, to_idx: int) -> tuple[bool, AudioPlayerState]:
    updated_queue: list[AudioTrack] = list(state.queue)
    if not (0 <= from_idx < len(updated_queue) and 0 <= to_idx < len(updated_queue)):
        return False, state
    track: AudioTrack = updated_queue.pop(from_idx)
    updated_queue.insert(to_idx, track)
    return True, state.model_copy(update={"queue": updated_queue})

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