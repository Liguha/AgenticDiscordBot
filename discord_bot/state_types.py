from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING
from .return_types import AudioTrack
if TYPE_CHECKING:
    from .actions.actions.audio.utils import MuxPCMAudio
    from .routers.discord_agent.utils.context_manager import ContextManager

__all__ = [
    "BaseState",
    "PrefixState",
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


@no_serialization
class AudioPlayerState(BaseState):
    queue: list[AudioTrack] = []
    current_track: AudioTrack | None = None
    is_looping: bool = False
    is_playing: bool = False
    mixer: MuxPCMAudio | None = None

def init_context() -> ContextManager:
    from .routers.discord_agent.utils.context_manager import ContextManager
    return ContextManager()

class LLMContextState(BaseState):
    text_chat_ctx: ContextManager = Field(default_factory=init_context)

from .routers.discord_agent.utils.context_manager import ContextManager
from .actions.actions.audio.utils import MuxPCMAudio
LLMContextState.model_rebuild()
AudioPlayerState.model_rebuild()