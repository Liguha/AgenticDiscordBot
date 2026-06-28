from abc import ABC, abstractmethod
from asyncio import gather
from ..actions import ActionResult
from ..events import EventBroker
from ..utils import Serializable

__all__ = []

class Router(ABC):
    def __init__(self, broker: EventBroker, state: Serializable) -> None:
        self._broker = broker
        self._state = state

    @property
    def broker(self) -> EventBroker:
        return self._broker
    
    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    def load_state(self, json_data: str) -> None:
        self._state.update(json_data)

    def serialize_state(self) -> str:
        return self._state.to_json()

    async def execute_serial(self, result: ActionResult) -> None:
        for call in result.deffered_calls:
            await call()

    async def execute_parallel(self, result: ActionResult) -> None:
        await gather(*[call() for call in result.deffered_calls])