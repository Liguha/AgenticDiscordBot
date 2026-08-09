from __future__ import annotations
from asyncio import Queue, create_task, Task, CancelledError, gather
from typing import ClassVar
from collections.abc import Callable, Awaitable
from .event_models import Event

__all__ = ["EventCallback", "Subscription", "EventBroker", "EVENT_BROKER"]

type EventCallback = Callable[[Event], Awaitable[None]]

class Subscription:
    def __init__(self, broker: EventBroker, event_key: str, callback: EventCallback) -> None:
        self.broker = broker
        self.event_key = event_key
        self.callback = callback

    def cancel(self) -> None:
        self.broker.unsubscribe(self.event_key, self.callback)

class EventBroker:
    MAX_ACTIVE_BROKERS: ClassVar[int] = 1
    ACTIVE_BROKERS: ClassVar[int] = 0

    def __init__(self) -> None:
        cls = self.__class__
        if cls.ACTIVE_BROKERS >= cls.MAX_ACTIVE_BROKERS:
            raise ValueError(f"Can't create new {cls.__name__} - limit reached.")
        cls.ACTIVE_BROKERS += 1
        self._running: bool = False
        self._queue: Queue[Event] = Queue()
        self._listener: Task | None = None
        self._subscribers: dict[str, list[EventCallback]] = {}
        self._background_tasks: set[Task] = set()

    async def start(self) -> Task:
        async def listener_loop() -> None:
            try:
                while self._running:
                    event = await self._queue.get()
                    callbacks = self._subscribers.get(event.key, [])
                    for cb in callbacks:
                        task = create_task(cb(event))
                        self._background_tasks.add(task)
                        task.add_done_callback(self._background_tasks.discard)
                    self._queue.task_done()
            except CancelledError:
                pass
        self._running = True
        self._listener = create_task(listener_loop())

    async def stop(self) -> None:
        self._running = False
        if self._listener:
            self._listener.cancel()

    async def publish(self, event: Event) -> None:
        await self._queue.put(event)

    def subscribe(self, event_key: str, callback: EventCallback) -> Subscription:
        if event_key not in self._subscribers:
            self._subscribers[event_key] = []
        self._subscribers[event_key].append(callback)
        return Subscription(self, event_key, callback)

    def unsubscribe(self, event_key: str, callback: EventCallback) -> None:
        callbacks = self._subscribers.get(event_key, [])
        callbacks.remove(callback)

    def __del__(self) -> None:
        cls = self.__class__
        cls.ACTIVE_BROKERS -= 1

EVENT_BROKER: EventBroker = EventBroker()