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

AudioSourceType = Literal["youtube", "soundcloud"]

class AudioTrack(BaseModel):
    title: str
    url: str
    duration: float
    source_type: AudioSourceType

class AudioPlayerState(BaseModel):
    queue: list[AudioTrack] = []
    current_track: AudioTrack | None = None
    is_looping: bool = False
    is_playing: bool = False