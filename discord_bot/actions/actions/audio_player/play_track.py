import asyncio
from typing import Any
from discord import Client, Guild, FFmpegOpusAudio, VoiceClient
from .config import FFMPEG_OPTIONS
from ...wrapper import Action
from ....events import EventBroker, DiscordCallabackEvent
from ....state_types import AudioPlayerState, AudioTrack

__all__ = ["TRACK_FINISHED_CALLBACK_NAME", "play_next_track", "on_track_finished"]

TRACK_FINISHED_CALLBACK_NAME: str = "track_finished"

@Action
async def play_next_track(broker: EventBroker, client: Client, state: AudioPlayerState, guild: Guild) -> tuple[AudioTrack | None, AudioPlayerState]:
    vc: VoiceClient = guild.voice_client
    if vc is None:
        return None, state.model_copy(update={"is_playing": False, "current_track": None})
    if vc.is_playing() or vc.is_paused():
        return state.current_track, state
    new_queue = list(state.queue)
    if state.is_looping and state.current_track:
        new_queue.append(state.current_track)
    if not new_queue:
        return None, state.model_copy(update={"queue": [], "is_playing": False, "current_track": None})
    next_track = new_queue.pop(0)
    try:
        source = FFmpegOpusAudio(next_track.url, **FFMPEG_OPTIONS)
        def after_callback(error: Exception | None) -> None:
            if error:
                print(f"PCM Stream extraction fault notice: {error}")
            event = DiscordCallabackEvent(
                name=TRACK_FINISHED_CALLBACK_NAME,
                payload={
                    "broker": broker,
                    "client": client,
                    "guild": guild
                },
                guild=guild
            )
            asyncio.run_coroutine_threadsafe(broker.publish(event), client.loop)
        vc.play(source, after=after_callback)
        return next_track, state.model_copy(update={
            "queue": new_queue,
            "current_track": next_track,
            "is_playing": True
        })
    except Exception as e:
        print(f"FFmpeg pipeline instantiation failure: {e}")
        return None, state.model_copy(update={"queue": new_queue, "is_playing": False, "current_track": None})

async def on_track_finished(state: AudioPlayerState, payload: dict[str, Any]) -> AudioPlayerState:
    broker: EventBroker = payload["broker"]
    client: Client = payload["client"]
    guild: Guild = payload["guild"]
    _, updated_state = await play_next_track(broker, client, state, guild)
    return updated_state