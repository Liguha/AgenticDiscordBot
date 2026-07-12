from pydantic import BaseModel, ConfigDict
from typing import Literal
from .actions.actions.audio.utils import MuxPCMAudio

__all__ = [
    "BaseState",
    "PrefixState",
    "AudioSourceType",
    "AudioTrack", 
    "AudioPlayerState"
]

def no_serialization[T](cls: type[T]) -> type[T]:
    cls.__SKIP_DUMP__ = True
    return cls

class BaseState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

############################################################################

class PrefixState(BaseState):
    prefix: str = ">"

AudioSourceType = Literal["youtube", "soundcloud"]

class AudioTrack(BaseModel):
    title: str
    url: str
    duration: float
    source_type: AudioSourceType

@no_serialization
class AudioPlayerState(BaseState):
    queue: list[AudioTrack] = []
    current_track: AudioTrack | None = None
    is_looping: bool = False
    is_playing: bool = False
    mixer: MuxPCMAudio | None = None