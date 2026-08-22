from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

__all__ = [
    "AudioSourceType",
    "AudioTrack",
    "WebSearchResult",
]

AudioSourceType = Literal["youtube", "soundcloud"]

class AudioTrack(BaseModel):
    title: str
    url: str
    duration: float
    source_type: AudioSourceType

class WebSearchResult(BaseModel):
    title: str
    link: str
    content: str
    summary: str | None = None