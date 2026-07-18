import inspect
from typing import Any, Protocol, Concatenate, ClassVar, get_args
from types import UnionType
from collections.abc import Callable, Awaitable
from ..state_types import BaseState
from discord import Client, User, Member
from discord.abc import GuildChannel
from ..events import EventBroker

__all__ = ["Action"]

_ID_PARSERS_REGISTRY: dict[type, Callable[[Client, Any], Awaitable[Any]]] = {}

def id_parser[RawId, DiscordType](func: Callable[[Client, RawId], Awaitable[DiscordType]]) -> Callable[[Client, RawId], Awaitable[DiscordType]]:
    sig = inspect.signature(func)
    target_type = sig.return_annotation
    if target_type is inspect.Parameter.empty:
        raise ValueError(f"Parser `{func.__name__}` must have a return type annotation.")
    _ID_PARSERS_REGISTRY[target_type] = staticmethod(func)
    return func

class Action[**ExtraArgs, ReturnType, StateType: BaseState](Protocol):
    ID_PARSERS_REGISTRY: ClassVar[dict[type, Callable[[Client, Any], Awaitable[Any]]]] = _ID_PARSERS_REGISTRY

    def __init__(self,
                 func: Callable[Concatenate[EventBroker, Client, StateType, ExtraArgs], Awaitable[tuple[ReturnType, StateType]]]
                ) -> None:
        self._func = func
        self._sig = inspect.signature(func)
        
    @classmethod
    async def parse_id[Target](cls, client: Client, uid: Any, target_type: type[Target]) -> Target:
        if target_type in cls.ID_PARSERS_REGISTRY:
            return await cls.ID_PARSERS_REGISTRY[target_type](client, uid)
        for dtype, func in cls.ID_PARSERS_REGISTRY.items():
            if issubclass(target_type, dtype):
                return await func(client, uid)
        raise IndexError(f"Can't find `{target_type.__name__}` with id `{uid}` ({type(uid).__name__}).")
    
    @id_parser
    async def id_to_channel(client: Client, uid: int | str) -> GuildChannel:
        return await client.fetch_channel(int(uid))

    @id_parser
    async def id_to_user(client: Client, uid: int | str | Member) -> User:
        if isinstance(uid, Member):
            return uid
        return await client.fetch_user(int(uid))

    async def __call__(self, broker: EventBroker, client: Client, state: StateType | None, *args: ExtraArgs.args, **kwds: ExtraArgs.kwargs) -> tuple[ReturnType, StateType]:
        if state is None:
            state_param = self._sig.parameters.get("state")
            if state_param is not None:
                state_type = state_param.annotation
                target_model: type[BaseState] | None = None
                if isinstance(state_type, UnionType) or hasattr(state_type, "__origin__"):
                    for t in get_args(state_type):
                        if isinstance(t, type) and issubclass(t, BaseState):
                            target_model = t
                            break
                elif isinstance(state_type, type) and issubclass(state_type, BaseState):
                    target_model = state_type
                if target_model is not None:
                    state = target_model()
        bound = self._sig.bind(broker, client, state, *args, **kwds)
        bound.apply_defaults()
        for name, value in bound.arguments.items():
            param = self._sig.parameters[name]
            target_type = param.annotation
            if target_type is inspect.Parameter.empty or not isinstance(target_type, type):
                continue
            if isinstance(value, target_type):
                continue
            bound.arguments[name] = await self.parse_id(client, value, target_type)
        return await self._func(*bound.args, **bound.kwargs)