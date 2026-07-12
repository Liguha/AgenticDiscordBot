import asyncio
from typing import Any
from discord import Client, Guild, VoiceClient
from ..utils import YTDL_PLAYER
from ....wrapper import Action
from .....events import EventBroker
from .....state_types import AudioPlayerState, AudioTrack
from .....utils import run_in_executor
from .....events import DiscordCallabackEvent

__all__ = ["TRACK_FINISHED_CALLBACK_NAME", "play_next_track", "on_track_finished"]

TRACK_FINISHED_CALLBACK_NAME: str = "track_finished"

@run_in_executor
def _resolve_stream_context(webpage_url: str) -> str:
    info: dict[str, Any] | None = YTDL_PLAYER.extract_info(webpage_url, download=False)
    if not info:
        raise ValueError("Failed to extract operational stream manifest.")
    return str(info["url"])

@Action
async def play_next_track(broker: EventBroker, client: Client, state: AudioPlayerState, guild: Guild) -> tuple[AudioTrack | None, AudioPlayerState]:
    vc: VoiceClient | None = guild.voice_client
    if vc is None or state.mixer is None:
        return None, state.model_copy(update={"is_playing": False, "current_track": None})
    if state.is_playing:
        return state.current_track, state
    new_queue: list[AudioTrack] = list(state.queue)
    if state.is_looping and state.current_track:
        new_queue.append(state.current_track)
    if not new_queue:
        return None, state.model_copy(update={"queue": [], "is_playing": False, "current_track": None})
    next_track: AudioTrack = new_queue.pop(0)
    try:
        stream_url: str = await _resolve_stream_context(next_track.url)
        def after_callback() -> None:
            event: DiscordCallabackEvent = DiscordCallabackEvent(
                name=TRACK_FINISHED_CALLBACK_NAME,
                payload={"broker": broker, "client": client, "guild": guild},
                guild=guild
            )
            asyncio.run_coroutine_threadsafe(broker.publish(event), client.loop)
        state.mixer.play_music(stream_url, after=after_callback)
        return next_track, state.model_copy(update={"queue": new_queue, "current_track": next_track,"is_playing": True})
    except Exception as e:
        print(f"Audio context compilation error: {e}")
        return None, state.model_copy(update={"queue": new_queue, "is_playing": False, "current_track": None})

async def on_track_finished(state: AudioPlayerState, payload: dict[str, Any]) -> AudioPlayerState:
    broker: EventBroker = payload["broker"]
    client: Client = payload["client"]
    guild: Guild = payload["guild"]
    reset_state: AudioPlayerState = state.model_copy(update={"is_playing": False})
    _, updated_state = await play_next_track(broker, client, reset_state, guild)
    return updated_state