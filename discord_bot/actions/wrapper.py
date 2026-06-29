from typing import Protocol, Concatenate
from collections.abc import Callable, Awaitable
from .structs import ExecutionContext

__all__ = ["Action"]

class Action[**ExtraArgs, StateType, ReturnType](Protocol):
    def __init__(self,
                 func: Callable[Concatenate[ExecutionContext, StateType, ExtraArgs], Awaitable[tuple[ReturnType, StateType]]]
                ) -> None:
        self._func = func

    async def __call__(self, ctx: ExecutionContext, state: StateType, *args: ExtraArgs.args, **kwds: ExtraArgs.kwargs) -> tuple[ReturnType, StateType]:
        return await self._func(ctx, state, *args, **kwds)