from __future__ import annotations
import json
from abc import ABC, abstractmethod
from asyncio import create_task, sleep, CancelledError, Task
from typing import Any, ClassVar, overload, NoReturn, Self, TYPE_CHECKING
from types import EllipsisType, ModuleType
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path
from importlib import import_module
from contextlib import asynccontextmanager
from ..utils import AsyncRWLock
from ..globals import RUNTIME_FOLDER

if TYPE_CHECKING:
    from ..state_types import BaseState

__all__ = ["GroupState", "StateManager"]

DEFAULT_PATH = RUNTIME_FOLDER / "states.json"

class GroupTreeProtocol(ABC):
    @asynccontextmanager
    async def lock(self, exclusive: bool = True) -> AsyncGenerator[Self, None]:
        for ancestor_lock in self.ancestor_rwlocks:
            await ancestor_lock.acquire_shared()
        if exclusive:
            await self.rwlock.acquire_exclusive()
        else:
            await self.rwlock.acquire_shared()
        try:
            yield self
        finally:
            if exclusive:
                await self.rwlock.release_exclusive()
            else:
                await self.rwlock.release_shared()
            for ancestor_lock in reversed(self.ancestor_rwlocks):
                await ancestor_lock.release_shared()

    @property
    @abstractmethod
    def rwlock(self) -> AsyncRWLock:
        pass

    @property
    @abstractmethod
    def ancestor_rwlocks(self) -> tuple[AsyncRWLock, ...]:
        pass

    @abstractmethod
    def get_shared(self) -> BaseState | None:
        pass
    
    @abstractmethod
    def set_shared(self, data: BaseState | None = None) -> None:
        pass
    
    @abstractmethod
    def get_subgroup(self, group_id: str) -> GroupState:
        pass
    
    @overload
    def __getitem__(self, key: str) -> GroupState: ...
    @overload
    def __getitem__(self, key: EllipsisType) -> BaseState | None: ...
    def __getitem__(self, key: str | EllipsisType) -> GroupState | BaseState | None:
        if isinstance(key, str):
            return self.get_subgroup(key)
        return self.get_shared()
    
    @overload
    def __setitem__(self, key: str, value: BaseState | None) -> NoReturn: ...
    @overload
    def __setitem__(self, key: EllipsisType, value: BaseState | None) -> None: ...
    def __setitem__(self, key: str | EllipsisType, value: BaseState | None) -> NoReturn | None:
        if isinstance(key, str):
            raise IndexError("Can't assign to group.")
        return self.set_shared(value)

@dataclass
class GroupState(GroupTreeProtocol):
    SHARED_KEY: ClassVar[str] = "shared"
    TYPE_KEY: ClassVar[str] = "dtype"
    LOCK_KEY: ClassVar[str] = "__lock__"

    data: dict[str, dict | BaseState] = field(default_factory=dict)

    locks: dict[str, dict | AsyncRWLock] = field(default_factory=dict, repr=False)
    _ancestor_locks: tuple[AsyncRWLock, ...] = field(default=(), repr=False, compare=False)

    @property
    def rwlock(self) -> AsyncRWLock:
        if self.LOCK_KEY not in self.locks:
            self.locks[self.LOCK_KEY] = AsyncRWLock()
        return self.locks[self.LOCK_KEY]

    @property
    def ancestor_rwlocks(self) -> tuple[AsyncRWLock, ...]:
        return self._ancestor_locks

    @classmethod
    def deserialize(cls, serialized: dict[str, Any]) -> GroupState:
        def recursive_parser(data: dict[str, Any], states_module: ModuleType) -> dict[str, BaseState | dict]:
            group_state = {}
            if cls.SHARED_KEY in data:
                dtype: type[BaseState] = getattr(states_module, data[cls.TYPE_KEY])
                group_state[cls.SHARED_KEY] = dtype.model_validate(data[cls.SHARED_KEY])
            for key, value in data.items():
                if key == cls.SHARED_KEY or key == cls.TYPE_KEY or value is None:
                    continue
                group_state[key] = recursive_parser(value, states_module)
            return group_state
        states_module = import_module("...state_types", package=__name__)
        return cls(recursive_parser(serialized, states_module))

    def serialize(self) -> dict[str, Any]:
        serialized = {}
        for key in self.data.keys():
            if key == self.SHARED_KEY:
                data = self.get_shared()
                if data is None or getattr(data, "__SKIP_DUMP__", False):
                    continue
                serialized[self.SHARED_KEY] = data.model_dump()
                serialized[self.TYPE_KEY] = data.__class__.__name__
            else:
                serialized[key] = self.get_subgroup(key).serialize()
        return serialized

    def get_shared(self) -> BaseState | None:
        return self.data.get(self.SHARED_KEY)
    
    def set_shared(self, data: BaseState | None = None) -> None:
        self.data[self.SHARED_KEY] = data

    def get_subgroup(self, group_id: str) -> GroupState:
        sub_data = self.data.setdefault(group_id, {})
        sub_locks = self.locks.setdefault(group_id, {})
        if not isinstance(sub_data, dict):
            raise ValueError(f"Incorrect subgroup `{group_id}`.")
        next_ancestors = (*self._ancestor_locks, self.rwlock)
        return GroupState(data=sub_data, locks=sub_locks, _ancestor_locks=next_ancestors)

class StateManager(GroupTreeProtocol):
    def __init__(self, save_period: float, file_path: Path = DEFAULT_PATH) -> None:
        self._running = False
        self._period = save_period
        self._file = file_path
        self._listener: Task | None = None
        if file_path.exists():
            self._storage = GroupState.deserialize(json.loads(file_path.read_text("utf-8")))
        else:
            self._storage = GroupState()

    def __repr__(self) -> None:
        return f"StateManager(Period: {self._period}, Data: {self._storage})"

    @property
    def rwlock(self) -> AsyncRWLock:
        return self.group_state.rwlock

    @property
    def ancestor_rwlocks(self) -> tuple[AsyncRWLock, ...]:
        return self.group_state.ancestor_rwlocks
    
    @property
    def group_state(self) -> GroupState:
        return self._storage

    def get_shared(self) -> BaseState | None:
        return self.group_state.get_shared()
    
    def set_shared(self, data: BaseState | None = None) -> None:
        return self.group_state.set_shared(data)
    
    def get_subgroup(self, group_id: str) -> GroupState:
        return self.group_state.get_subgroup(group_id)
        
    async def start(self) -> None:
        async def serialization_loop() -> None:
            try:
                while self._running:
                    await sleep(self._period)
                    json_str = json.dumps(self.group_state.serialize())
                    self._file.write_text(json_str, encoding="utf-8")
            except CancelledError:
                pass
        self._running = True
        self._listener = create_task(serialization_loop())

    async def stop(self) -> None:
        self._running = False
        if self._listener:
            self._listener.cancel()