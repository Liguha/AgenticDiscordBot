from typing import Protocol, Concatenate
from collections.abc import Callable, Awaitable
from .structs import ActionResult, ExecutionContext

__all__ = ["Action"]

class Action[**ExtraArgs, CtxType, StateType, ReturnType](Protocol):
    def __init__(self,
                 func: Callable[Concatenate[ExecutionContext[CtxType], StateType, ExtraArgs], Awaitable[tuple[ActionResult[ReturnType], StateType]]]
                ) -> None:
        self._func = func

    async def __call__(self, ctx: ExecutionContext[CtxType], state: StateType, *args: ExtraArgs.args, **kwds: ExtraArgs.kwargs) -> tuple[ActionResult[ReturnType], StateType]:
        return await self._func(ctx, state, *args, **kwds)