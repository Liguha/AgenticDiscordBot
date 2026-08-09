from asyncio import Condition

__all__ = ["AsyncRWLock"]

class AsyncRWLock:
    def __init__(self):
        self._readers = 0
        self._writer = False
        self._cond = Condition()

    async def acquire_shared(self):
        async with self._cond:
            while self._writer:
                await self._cond.wait()
            self._readers += 1

    async def release_shared(self):
        async with self._cond:
            self._readers -= 1
            if self._readers == 0:
                self._cond.notify_all()

    async def acquire_exclusive(self):
        async with self._cond:
            while self._writer or self._readers > 0:
                await self._cond.wait()
            self._writer = True

    async def release_exclusive(self):
        async with self._cond:
            self._writer = False
            self._cond.notify_all()