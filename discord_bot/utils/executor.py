from asyncio import get_running_loop
from functools import wraps, partial
from typing import Callable, Awaitable

__all__ = ["run_in_executor"]

def run_in_executor[**Args, Return](func: Callable[Args, Return]) -> Callable[Args, Awaitable[Return]]:
    wraps(func)
    async def wrapper(*args: Args.args, **kwds: Args.kwargs) -> Return:
        loop = get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwds))
    return wrapper