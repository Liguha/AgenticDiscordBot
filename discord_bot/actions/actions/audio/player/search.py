from discord import Client
from ..utils import YTDL_SEARCH
from ....wrapper import Action
from .....events import EventBroker
from .....state_types import AudioSourceType, AudioTrack
from .....utils import run_in_executor

__all__ = ["search_audio"]

@run_in_executor
def _extract_meta(query: str, limit: int, source_type: AudioSourceType) -> list[dict]:
    search_query = query
    if source_type == "youtube":
        search_query = f"ytsearch{limit}:{query}"
    elif source_type == "soundcloud":
        search_query = f"scsearch{limit}:{query}"
    info: dict = YTDL_SEARCH.extract_info(search_query, download=False)
    if not info:
        return []
    if "entries" in info:
        return list(info["entries"])
    return [info]

@Action
async def search_audio(broker: EventBroker,
                       client: Client,
                       state: None,
                       query: str,
                       source_type: AudioSourceType = "youtube",
                       limit: int = 1
                      ) -> tuple[list[AudioTrack], None]:
    raw_entries = await _extract_meta(query, limit, source_type)
    tracks = []
    for entry in raw_entries:
        if not entry:
            continue
        resolved_url = entry.get("url") or entry.get("webpage_url") or query
        duration = entry.get("duration")
        tracks.append(AudioTrack(
            title=entry.get("title", "Unknown Resource"),
            url=resolved_url,
            duration=float(duration) if duration else 0.0,
            source_type=source_type
        ))
    return tracks, None