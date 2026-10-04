from __future__ import annotations
from asyncio import CancelledError, Task, create_task, get_running_loop
from collections.abc import Awaitable, Callable
from inspect import iscoroutinefunction
from multiprocessing import Process, Queue
from threading import Thread
from typing import Final, Literal

__all__ = ["PipelineBlock", "Pipeline", "PIPELINE_STOP"]

PIPELINE_STOP: Final[str] = "\x00pipeline-stop"

type BlockMode = Literal["map", "consume"]


class PipelineBlock[I, O]:
    @classmethod
    def from_map(cls, separate_process: bool = False) -> Callable[
            [Callable[[I], O | Awaitable[O]]], PipelineBlock[I, O]]:
        def factory(func: Callable[[I], O | Awaitable[O]]) -> PipelineBlock[I, O]:
            return cls(func, "map", separate_process=separate_process)
        return factory

    @classmethod
    def from_consumer(cls, separate_process: bool = False) -> Callable[
            [Callable[[Queue[I], Queue[O]], None]], PipelineBlock[I, O]]:
        def factory(func: Callable[[Queue[I], Queue[O]], None]) -> PipelineBlock[I, O]:
            return cls(func, "consume", separate_process=separate_process)
        return factory

    def __init__(self,
                 func: Callable[..., object],
                 mode: BlockMode,
                 /, *,
                 separate_process: bool) -> None:
        self._func = func
        self._mode = mode
        self._separate_process = separate_process
        self._is_async = iscoroutinefunction(func)
        self.input: Queue[I] | None = None
        self.output: Queue[O] | None = None
        self._worker: Process | Thread | None = None
        self._task: Task[None] | None = None

    def _run_map(self) -> None:
        func = self._func
        while (item := self.input.get()) != PIPELINE_STOP:
            self.output.put(func(item))
        self.output.put(PIPELINE_STOP)

    async def _run_map_async(self) -> None:
        func = self._func
        loop = get_running_loop()
        while (item := await loop.run_in_executor(None, self.input.get)) != PIPELINE_STOP:
            self.output.put(await func(item))
        self.output.put(PIPELINE_STOP)

    async def _run_consume_async(self) -> None:
        func = self._func
        loop = get_running_loop()
        await func(self.input, self.output)

    @staticmethod
    def _report_task_crash(task: Task) -> None:
        if not task.cancelled() and task.exception() is not None:
            from traceback import print_exception
            print_exception(task.exception())

    def _run(self) -> None:
        try:
            if self._mode == "map":
                self._run_map()
            else:
                self._func(self.input, self.output)
        except BaseException:
            from traceback import print_exc
            print_exc()
            raise

    def _spawn(self) -> None:
        if self._separate_process:
            self._worker = Process(target=self._run, daemon=True)
            self._worker.start()
        elif self._is_async:
            runner = self._run_map_async if self._mode == "map" else self._run_consume_async
            self._task = create_task(runner())
            self._task.add_done_callback(self._report_task_crash)
        else:
            self._worker = Thread(target=self._run, daemon=True)
            self._worker.start()


class Pipeline:
    def __init__(self, *blocks: PipelineBlock) -> None:
        if not blocks:
            raise ValueError("Pipeline requires at least one block")
        for left, right in zip(blocks, blocks[1:]):
            queue: Queue = Queue()
            left.output = queue
            right.input = queue
        head: Queue = Queue()
        tail: Queue = Queue()
        blocks[0].input = head
        blocks[-1].output = tail
        self.input: Queue = head
        self.output: Queue = tail
        self._blocks = blocks

    async def start(self) -> None:
        for block in self._blocks:
            block._spawn()

    async def stop(self) -> None:
        self.input.put(PIPELINE_STOP)
        for block in self._blocks:
            if block._task is not None:
                try:
                    await block._task
                except CancelledError:
                    pass
            elif isinstance(block._worker, Process):
                block._worker.join(timeout=5.0)
                if block._worker.is_alive():
                    block._worker.terminate()
                    block._worker.join(timeout=5.0)