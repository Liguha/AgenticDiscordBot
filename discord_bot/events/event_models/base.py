from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from ...enums import PlatformEnum

__all__ = ["Event"]

@dataclass
class Event[PayloadType](ABC):
    platform: PlatformEnum
    payload: PayloadType

    @property
    @abstractmethod
    def key(self) -> str:
        pass

    @classmethod
    @abstractmethod
    def key_from_context(cls, *args: Any, **kwargs: Any) -> str:
        pass