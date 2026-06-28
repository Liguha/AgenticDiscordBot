from abc import ABC, abstractmethod
from ..event_broker import EventBroker

__all__ = ["EventProducer"]

class EventProducer(ABC):
    def __init__(self, broker: EventBroker) -> None:
        self._broker = broker

    @property
    def broker(self) -> EventBroker:
        return self._broker
    
    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass