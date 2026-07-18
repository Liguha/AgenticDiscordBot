from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, TYPE_CHECKING
if TYPE_CHECKING:
    from .actions.actions.audio.utils import MuxPCMAudio
    from .routers.discord_agent.context_manager import ContextManager

__all__ = [
    "BaseState",
    "PrefixState",
    "AudioSourceType",
    "AudioTrack", 
    "AudioPlayerState",
    "LLMContextState"
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

def init_context() -> ContextManager:
    from .routers.discord_agent.context_manager import ContextManager
    return ContextManager()

class LLMContextState(BaseState):
    text_chat_ctx: ContextManager = Field(default_factory=init_context)

from .routers.discord_agent.context_manager import ContextManager
LLMContextState.model_rebuild()