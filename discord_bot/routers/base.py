from abc import ABC, abstractmethod
from .state_manager import GroupState
from ..events import EventBroker
from ..utils import Serializable

__all__ = ["Router"]

class Router(ABC):
    def __init__(self, broker: EventBroker, group_state: GroupState) -> None:
        self._broker = broker
        self._state = group_state

    @property
    def broker(self) -> EventBroker:
        return self._broker
    
    @property
    def group_state(self) -> GroupState:
        return self._state
    
    @property
    @abstractmethod
    def group_id(self) -> str:
        pass
    
    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass