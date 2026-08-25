import asyncio
from discord import Client, Guild
from pydantic import Field
from .base import ToolResult, ToolError, Tool, ToolErrorCodes
from ....events import EventBroker
from ....state_types import AudioPlayerState
from ....return_types import AudioSourceType, AudioTrack
from ....actions import (
    join_voice_to_user,
    search_audio,
    add_tracks_many,
    skip_track,
    toggle_loop,
    play_next_track
)

__all__ = [
    "PlayerStatusResult", "get_audio_player_status",
    "AddTracksResult", "audio_player_add_tracks",
    "SkipResult", "audio_player_skip",
    "RemoveResult", "audio_player_remove",
    "ToggleLoopResult", "audio_player_toggle_loop"
]

GROUP_ID: str = "audio"

TrackMeta = dict[str, str | float]


def _track_meta(track: AudioTrack) -> TrackMeta:
    return {
        "title": track.title,
        "url": track.url,
        "duration": track.duration,
        "source_type": track.source_type
    }


class PlayerStatusResult(ToolResult):
    is_playing: bool = Field(description="True when an audio track is active.")
    is_looping: bool = Field(description="True when queue loop mode is on.")
    current_track: TrackMeta | None = Field(description="Metadata of the active track or null.")
    queue: list[TrackMeta] = Field(description="Upcoming tracks in order.")


@Tool.with_group(GROUP_ID)
async def get_audio_player_status(broker: EventBroker, client: Client, guild: Guild, state: AudioPlayerState) -> tuple[PlayerStatusResult | ToolError, AudioPlayerState]:
    """Inspect the audio player: playback, loop mode, and the upcoming queue.

    Returns:
        The player status and queued tracks.
    """
    if state is None:
        state = AudioPlayerState()
    cur = _track_meta(state.current_track) if state.current_track else None
    queue_list = [_track_meta(t) for t in state.queue]
    result = PlayerStatusResult(
        is_playing=state.is_playing,
        is_looping=state.is_looping,
        current_track=cur,
        queue=queue_list
    )
    return result, state


class AddTracksResult(ToolResult):
    added: list[TrackMeta] = Field(description="Metadata of successfully queued tracks.")
    failed_queries: list[str] = Field(description="Queries that produced no results.")


@Tool.with_group(GROUP_ID)
async def audio_player_add_tracks(broker: EventBroker,
                                  client: Client,
                                  guild: Guild,
                                  state: AudioPlayerState,
                                  queries: list[str],
                                  requesting_user_id: str,
                                  platform: AudioSourceType = "youtube"
                                 ) -> tuple[AddTracksResult | ToolError, AudioPlayerState]:
    """Search several queries and enqueue all matching tracks in a single call.

    Joins the requesting user's voice channel once, then resolves every query and
    adds the top result of each to the upcoming queue.

    Args:
        queries: One or more track titles, keywords, or URLs to search and queue.
        requesting_user_id: Discord Snowflake ID of the user issuing the request.
        platform: The streaming platform to search on.

    Returns:
        List of queued track metadata plus any queries that failed to match.
    """
    if state is None:
        state = AudioPlayerState()
    added: list[TrackMeta] = []
    failed_queries: list[str] = []
    if queries:
        joined, state = await join_voice_to_user(broker, client, state, guild, requesting_user_id)
        if not joined and not guild.voice_client:
            return ToolError(
                error_code=ToolErrorCodes.RUNTIME_ERROR.name,
                message="Requesting user is not in a discoverable voice channel."
            ), state
        tracks: list[AudioTrack] = []
        async def _search(query: str) -> tuple[str, AudioTrack | None]:
            try:
                found, _ = await search_audio(broker, client, None, query, source_type=platform, limit=1)
                return query, found[0] if found else None
            except Exception:
                return query, None
        search_results = await asyncio.gather(*(_search(q) for q in queries))
        for query, track in search_results:
            if track is not None:
                tracks.append(track)
            else:
                failed_queries.append(query)
        if tracks:
            _, state = await add_tracks_many(broker, client, state, guild, tracks)
            added = [_track_meta(t) for t in tracks]
    return AddTracksResult(added=added, failed_queries=failed_queries), state


class SkipResult(ToolResult):
    skipped: TrackMeta | None = Field(description="The current track that was skipped, or null.")
    next_track: TrackMeta | None = Field(description="The track now playing, or null if fully stopped.")


@Tool.with_group(GROUP_ID)
async def audio_player_skip(broker: EventBroker,
                            client: Client,
                            guild: Guild,
                            state: AudioPlayerState
                           ) -> tuple[SkipResult | ToolError, AudioPlayerState]:
    """Skip the current track and advance to the next.

    With loop mode enabled the skipped track is re-queued to the end and is NOT
    removed from rotation.

    Returns:
        The skipped track and the track now playing.
    """
    if state is None:
        state = AudioPlayerState()
    skipped = _track_meta(state.current_track) if state.current_track else None
    ok, new_state = await skip_track(broker, client, state, guild)
    if not ok:
        return ToolError(
            error_code=ToolErrorCodes.RUNTIME_ERROR.name,
            message="Cannot skip: no active voice playback in this guild."
        ), state
    next_track = _track_meta(new_state.current_track) if new_state.current_track else None
    return SkipResult(skipped=skipped, next_track=next_track), new_state


class RemoveResult(ToolResult):
    removed: list[TrackMeta] = Field(description="Upcoming tracks removed from the queue.")
    skipped_current: TrackMeta | None = Field(description="The current track skipped and dropped when index 0 was requested.")


@Tool.with_group(GROUP_ID)
async def audio_player_remove(broker: EventBroker,
                              client: Client,
                              guild: Guild,
                              state: AudioPlayerState,
                              indices: list[int]
                             ) -> tuple[RemoveResult | ToolError, AudioPlayerState]:
    """Remove tracks from the player queue.

    The queue is 1-indexed: index 1 is the next upcoming track. Requesting index 0
    skips and drops the current track (removed even when loop mode is on).

    Args:
        indices: 1-based queue positions to remove; 0 removes the current track.

    Returns:
        The removed tracks and the current track if it was dropped.
    """
    if state is None:
        state = AudioPlayerState()
    index_set: set[int] = set(indices)
    dropped_current = 0 in index_set
    removed: list[TrackMeta] = []
    kept: list[AudioTrack] = []
    for i, track in enumerate(state.queue, start=1):
        if i in index_set:
            removed.append(_track_meta(track))
        else:
            kept.append(track)
    new_state: AudioPlayerState = state.model_copy(update={"queue": kept})
    if not dropped_current:
        return RemoveResult(removed=removed, skipped_current=None), new_state
    skipped_current = _track_meta(new_state.current_track) if new_state.current_track else None
    if new_state.mixer is None or guild.voice_client is None:
        new_state = new_state.model_copy(update={"is_playing": False, "current_track": None, "is_looping": False})
    else:
        new_state.mixer.stop_music()
        reset_state = new_state.model_copy(update={"is_playing": False, "current_track": None, "is_looping": False})
        _, new_state = await play_next_track(broker, client, reset_state, guild)
    return RemoveResult(removed=removed, skipped_current=skipped_current), new_state


class ToggleLoopResult(ToolResult):
    is_looping: bool = Field(description="Loop mode state after toggling.")


@Tool.with_group(GROUP_ID)
async def audio_player_toggle_loop(broker: EventBroker,
                                   client: Client,
                                   guild: Guild,
                                   state: AudioPlayerState
                                  ) -> tuple[ToggleLoopResult | ToolError, AudioPlayerState]:
    """Toggle queue loop mode on/off.

    With loop mode on, finished or skipped tracks are re-queued.

    Returns:
        The new loop mode state.
    """
    if state is None:
        state = AudioPlayerState()
    is_looping, new_state = await toggle_loop(broker, client, state)
    return ToggleLoopResult(is_looping=is_looping), new_state