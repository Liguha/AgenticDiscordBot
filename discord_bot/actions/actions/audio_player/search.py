import asyncio
import functools
from typing import Literal, Callable, Awaitable
from discord import Client
from .config import YTDL
from ...wrapper import Action
from ....events import EventBroker
from ....state_types import AudioPlayerState, AudioTrack

__all__ = ["search_audio"]

def run_in_executor[**Args, Return](func: Callable[Args, Return]) -> Callable[Args, Awaitable[Return]]:
    @functools.wraps(func)
    async def wrapper(*args: Args.args, **kwds: Args.kwargs) -> Return:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwds))
    return wrapper

@run_in_executor
def _extract_meta(query: str, limit: int, source_type: str) -> list[dict]:
    search_query = query
    if source_type == "youtube" and not query.startswith(("http://", "https://")):
        search_query = f"ytsearch{limit}:{query}"
    elif source_type == "spotify":
        # TODO: spotify
        search_query = f"ytsearch{limit}:{query}"   # placeholder
    info: dict = YTDL.extract_info(search_query, download=False)
    if not info:
        return []
    return info.get("entries", [info]) if "entries" in info else [info]

@Action
async def search_audio(broker: EventBroker,
                       client: Client,
                       state: None,
                       query: str,
                       source_type: Literal["youtube", "spotify"] = "youtube",
                       limit: int = 1
                      ) -> tuple[list[AudioTrack], None]:
    raw_entries = await _extract_meta(query, limit, source_type)
    tracks = []
    for entry in raw_entries:
        if not entry:
            continue
        tracks.append(AudioTrack(
            title=entry.get("title", "Unknown Resource"),
            url=entry.get("url", ""),
            source_url=entry.get("webpage_url", query),
            duration=float(entry.get("duration", 0.0)),
            source_type=source_type,
            thumbnail=entry.get("thumbnail")
        ))
    return tracks, None