from asyncio import AbstractEventLoop, get_running_loop
from collections.abc import Callable
from io import BufferedIOBase
from discord import AudioSource
from .mixer_process import AudioMixerProcess

__all__ = ["MuxPCMAudio"]

class MuxPCMAudio(AudioSource):
    def __init__(self, loop: AbstractEventLoop | None = None, *, before_options: str | None = None, options: str | None = None) -> None:
        self._loop: AbstractEventLoop = loop if loop is not None else get_running_loop()
        self._music_after: Callable[[], None] | None = None
        self._aux_after: Callable[[], None] | None = None
        self._was_music_active: bool = False
        self._was_aux_active: bool = False
        self._mixer: AudioMixerProcess = AudioMixerProcess(before_options, options)
        self._mixer.start()

    def is_opus(self) -> bool:
        return False

    def read(self) -> bytes:
        frame, music_active, aux_active = self._mixer.read_mixed()
        if self._was_music_active and not music_active:
            if self._music_after is not None:
                self._loop.call_soon_threadsafe(self._music_after)
                self._music_after = None
        if self._was_aux_active and not aux_active:
            if self._aux_after is not None:
                self._loop.call_soon_threadsafe(self._aux_after)
                self._aux_after = None
        self._was_music_active = music_active
        self._was_aux_active = aux_active
        return frame

    def play_music(self, source: str | BufferedIOBase, *, is_pipe: bool = False, after: Callable[[], None] | None = None) -> None:
        self._music_after = after
        self._mixer.start_music(source, is_pipe=is_pipe)

    def stop_music(self, *, fire_callback: bool = False) -> None:
        if not fire_callback:
            self._music_after = None
            self._was_music_active = False
        self._mixer.stop_music()

    def play_aux(self, source: str | BufferedIOBase, *, is_pipe: bool = False, after: Callable[[], None] | None = None) -> None:
        self._aux_after = after
        self._mixer.start_aux(source, is_pipe=is_pipe)

    def stop_aux(self, *, fire_callback: bool = False) -> None:
        if not fire_callback:
            self._aux_after = None
            self._was_aux_active = False
        self._mixer.stop_aux()

    def cleanup(self) -> None:
        self._music_after = None
        self._aux_after = None
        self._mixer.destroy()