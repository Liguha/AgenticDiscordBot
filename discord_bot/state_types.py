from pydantic import BaseModel
from typing import Literal

__all__ = [
    "PrefixState",
    "AudioSourceType",
    "AudioTrack", 
    "AudioPlayerState"
]

class PrefixState(BaseModel):
    prefix: str = ">"

AudioSourceType = Literal["youtube", "spotify"]

class AudioTrack(BaseModel):
    title: str
    url: str                # Streamable raw file URL or absolute path
    source_url: str         # Original track link (e.g. YouTube, Spotify)
    duration: float         # In seconds
    source_type: AudioSourceType
    thumbnail: str | None = None

class AudioPlayerState(BaseModel):
    queue: list[AudioTrack] = []
    current_track: AudioTrack | None = None
    is_looping: bool = False
    is_playing: bool = False