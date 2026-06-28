from abc import ABC, abstractmethod
from typing import Self

__all__ = ["Serializable"]

class Serializable(ABC):
    @classmethod
    @abstractmethod
    def from_json(cls) -> Self:
        pass

    @abstractmethod
    def update(self, json_data: str) -> None:
        pass

    @abstractmethod
    def to_json(self) -> str:
        pass