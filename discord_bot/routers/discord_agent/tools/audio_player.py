import asyncio
from typing import Literal
from discord import Client, Guild
from pydantic import BaseModel, Field
from .base import ToolResult, ToolError, Tool, ToolErrorCodes
from ....events import EventBroker
from ....state_types import AudioPlayerState
from ....return_types import AudioSourceType, AudioTrack
from ....actions import (
    join_voice_to_user,
    search_audio,
    add_tracks_many,
    remove_by_indices,
    remove_by_title,
    move_track,
    skip_track,
    toggle_loop
)

__all__ = [
    "PlayerStatusResult", "get_audio_player_status",
    "AddTracksResult", "audio_player_add_tracks",
    "QueueEditOp", "EditQueueResult", "audio_player_edit_queue"
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
    position: int | None = Field(description="Insert offset used for the added batch.")


@Tool.with_group(GROUP_ID)
async def audio_player_add_tracks(broker: EventBroker,
                                  client: Client,
                                  guild: Guild,
                                  state: AudioPlayerState,
                                  queries: list[str],
                                  requesting_user_id: str,
                                  platform: AudioSourceType = "youtube",
                                  position: int | None = None
                                 ) -> tuple[AddTracksResult | ToolError, AudioPlayerState]:
    """Search several queries and enqueue all matching tracks in a single call.

    Joins the requesting user's voice channel once, then resolves every query and
    adds the top result of each to the queue. Optionally inserts at a queue offset.

    Args:
        queries: One or more track titles, keywords, or URLs to search and queue.
        requesting_user_id: Discord Snowflake ID of the user issuing the request.
        platform: The streaming platform to search on.
        position: Optional 0-based queue position to insert all added tracks.

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
            _, state = await add_tracks_many(broker, client, state, guild, tracks, position)
            added = [_track_meta(t) for t in tracks]
    return AddTracksResult(added=added, failed_queries=failed_queries, position=position), state


class QueueEditOp(BaseModel):
    operation: Literal["remove_by_index", "remove_by_title", "move", "skip", "clear", "set_loop", "toggle_loop"]
    indices: list[int] = Field(default_factory=list, description="0-based queue positions for remove_by_index.")
    patterns: list[str] = Field(default_factory=list, description="Case-insensitive title substrings for remove_by_title.")
    from_index: int | None = Field(default=None, description="Source position for move.")
    to_index: int | None = Field(default=None, description="Target position for move.")
    loop_enabled: bool | None = Field(default=None, description="Loop state for set_loop.")


class QueueEditReport(BaseModel):
    operation: str = Field(description="The executed queue operation identifier.")
    ok: bool = Field(description="Whether the operation succeeded.")
    removed_titles: list[str] | None = Field(default=None, description="Titles removed by remove operations.")
    is_looping: bool | None = Field(default=None, description="Loop state after a loop operation.")
    error: str | None = Field(default=None, description="Error detail when the operation failed.")


class EditQueueResult(ToolResult):
    results: list[QueueEditReport] = Field(description="Per-operation outcomes in execution order.")


@Tool.with_group(GROUP_ID)
async def audio_player_edit_queue(broker: EventBroker,
                                  client: Client,
                                  guild: Guild,
                                  state: AudioPlayerState,
                                  ops: list[QueueEditOp]
                                 ) -> tuple[EditQueueResult | ToolError, AudioPlayerState]:
    """Apply a batch of queue edits in order.

    Each operation yields a report entry; later operations see the result of the
    preceding ones. 0-based positions refer to the state of the queue at the moment
    that specific operation runs.

    Args:
        ops: Ordered list of queue operations to execute.

    Returns:
        A per-operation success report.
    """
    if state is None:
        state = AudioPlayerState()
    reports: list[QueueEditReport] = []
    for op in ops:
        name = op.operation
        try:
            if name == "remove_by_index":
                removed, state = await remove_by_indices(broker, client, state, op.indices)
                reports.append(QueueEditReport(operation=name, ok=True, removed_titles=[r.title for r in removed]))
            elif name == "remove_by_title":
                removed, _ = await remove_by_title(broker, client, state, op.patterns)
                reports.append(QueueEditReport(operation=name, ok=True, removed_titles=[r.title for r in removed]))
            elif name == "move":
                ok, state = await move_track(broker, client, state, op.from_index, op.to_index)
                reports.append(QueueEditReport(operation=name, ok=bool(ok)))
            elif name == "skip":
                ok, state = await skip_track(broker, client, state, guild)
                reports.append(QueueEditReport(operation=name, ok=bool(ok)))
            elif name == "clear":
                state = state.model_copy(update={"queue": []})
                reports.append(QueueEditReport(operation=name, ok=True))
            elif name == "set_loop":
                if state.is_looping != op.loop_enabled:
                    state = state.model_copy(update={"is_looping": bool(op.loop_enabled)})
                reports.append(QueueEditReport(operation=name, ok=True, is_looping=bool(state.is_looping)))
            elif name == "toggle_loop":
                loop_status, state = await toggle_loop(broker, client, state)
                reports.append(QueueEditReport(operation=name, ok=True, is_looping=loop_status))
            else:
                reports.append(QueueEditReport(operation=name, ok=False, error="Unsupported operation."))
        except Exception as e:
            reports.append(QueueEditReport(operation=name, ok=False, error=str(e)))
    return EditQueueResult(results=reports), state