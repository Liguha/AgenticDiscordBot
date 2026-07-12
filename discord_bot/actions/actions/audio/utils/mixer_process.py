import numpy as np
import threading
from multiprocessing import Process, Queue
from typing import Any
from subprocess import Popen, PIPE, DEVNULL
from queue import Empty
from enum import Enum
from io import BufferedIOBase
from shlex import split as shlex_split
from .config import (
    AUDIO_RATE_HZ,
    AUDIO_CHANNELS,
    AUDIO_FORMAT,
    AUDIO_FORMAT_NP,
    DUCKED_VOLUME,
    NORMAL_VOLUME,
    PCM_FRAME_SIZE,
    CLIP_MIN,
    CLIP_MAX,
    FADE_SPEED,
    OUTPUT_QUEUE_MAXSIZE,
    STREAM_QUEUE_MAXSIZE,
)

__all__ = ["MixerCommand", "AudioTarget", "AudioMixerProcess"]

class MixerCommand(Enum):
    STOP = 0
    PLAY = 1

class AudioTarget(Enum):
    MUSIC = 0
    AUX = 1

class AudioMixerProcess(Process):
    def __init__(self, before_options: str | None = None, options: str | None = None) -> None:
        super().__init__(daemon=True)
        self._cmd_queue: Queue = Queue()
        self._output_queue: Queue = Queue(maxsize=OUTPUT_QUEUE_MAXSIZE)
        self._music_stream_queue: Queue = Queue(maxsize=STREAM_QUEUE_MAXSIZE)
        self._aux_stream_queue: Queue = Queue(maxsize=STREAM_QUEUE_MAXSIZE)
        self._before_options: str | None = before_options
        self._options: str | None = options

    def run(self) -> None:
        music_proc: Popen[bytes] | None = None
        aux_proc: Popen[bytes] | None = None
        w: float = 0.0
        blank_frame: bytes = b"\x00" * PCM_FRAME_SIZE

        while True:
            # 1. Drain incoming configuration control commands
            while not self._cmd_queue.empty():
                try:
                    cmd, target, source, is_pipe = self._cmd_queue.get_nowait()
                    if cmd == MixerCommand.PLAY:
                        if target == AudioTarget.MUSIC:
                            if music_proc: music_proc.kill()
                            music_proc = self._spawn_decoder(source, is_pipe, self._music_stream_queue)
                        elif target == AudioTarget.AUX:
                            if aux_proc: aux_proc.kill()
                            aux_proc = self._spawn_decoder(source, is_pipe, self._aux_stream_queue)
                    elif cmd == MixerCommand.STOP:
                        if target == AudioTarget.MUSIC and music_proc:
                            music_proc.kill()
                            music_proc = None
                            self._clear_queue(self._music_stream_queue)
                        elif target == AudioTarget.AUX and aux_proc:
                            aux_proc.kill()
                            aux_proc = None
                            self._clear_queue(self._aux_stream_queue)
                except Empty:
                    break
            # 2. Collect audio frames from the active streams and Assess stream lifecycles
            music_bytes = self._read_stream(music_proc)
            aux_bytes = self._read_stream(aux_proc)
            music_active = False
            if music_proc:
                if music_bytes is None:
                    music_proc.kill()
                    music_proc = None
                else:
                    music_active = True
            aux_active = False
            if aux_proc:
                if aux_bytes is None:
                    aux_proc.kill()
                    aux_proc = None
                else:
                    aux_active = True
            # 5. Crossfade volume transition gains
            target_w = 1.0 if aux_active else 0.0
            if w < target_w:
                w = min(target_w, w + FADE_SPEED)
            elif w > target_w:
                w = max(target_w, w - FADE_SPEED)
            m_raw = music_bytes if (music_bytes and music_active) else blank_frame
            a_raw = aux_bytes if (aux_bytes and aux_active) else blank_frame
            if not music_active and not aux_active:
                mixed_bytes = blank_frame
            elif music_active and not aux_active and w == 0.0:
                mixed_bytes = m_raw
            else:
                m_arr = np.frombuffer(m_raw, dtype=AUDIO_FORMAT_NP).astype(np.float32)
                a_arr = np.frombuffer(a_raw, dtype=AUDIO_FORMAT_NP).astype(np.float32)
                music_vol = NORMAL_VOLUME + w * (DUCKED_VOLUME - NORMAL_VOLUME)
                aux_vol = w * NORMAL_VOLUME
                mixed_f32 = (m_arr * music_vol) + (a_arr * aux_vol)
                mixed_bytes = np.clip(mixed_f32, CLIP_MIN, CLIP_MAX).astype(AUDIO_FORMAT_NP).tobytes()
            # 4. Blocking write paces the entire process loop directly to Discord's sample consumption rate
            self._output_queue.put((mixed_bytes, music_active, aux_active))

    def read_mixed(self) -> tuple[bytes, bool, bool]:
        """Pulls calculated audio matrices and telemetry flags from the output queue."""
        try:
            return self._output_queue.get_nowait()
        except Empty:
            return (b"\x00" * PCM_FRAME_SIZE, False, False)

    def start_music(self, source: str | BufferedIOBase, *, is_pipe: bool = False) -> None:
        """Pushes a track initialization directive down the command line pipeline."""
        is_str = isinstance(source, str)
        payload_source = source if (not is_pipe or is_str) else None
        
        self._cmd_queue.put_nowait((MixerCommand.PLAY, AudioTarget.MUSIC, payload_source, is_pipe))
        
        if is_pipe and not is_str:
            self._spawn_parent_feeder_thread(source, self._music_stream_queue)

    def stop_music(self) -> None:
        """Halts the primary music layer instantly."""
        self._cmd_queue.put_nowait((MixerCommand.STOP, AudioTarget.MUSIC, None, False))

    def start_aux(self, source: str | BufferedIOBase, *, is_pipe: bool = False) -> None:
        """Pushes an auxiliary override configuration directive down the pipeline."""
        is_str = isinstance(source, str)
        payload_source = source if (not is_pipe or is_str) else None
        
        self._cmd_queue.put_nowait((MixerCommand.PLAY, AudioTarget.AUX, payload_source, is_pipe))
        
        if is_pipe and not is_str:
            self._spawn_parent_feeder_thread(source, self._aux_stream_queue)

    def stop_aux(self) -> None:
        """Halts the auxiliary track layer instantly."""
        self._cmd_queue.put_nowait((MixerCommand.STOP, AudioTarget.AUX, None, False))

    def destroy(self) -> None:
        if self.is_alive():
            self.terminate()
            self.join(timeout=2.0)
            if self.is_alive():
                self.kill()
                self.join()
        for q in (self._cmd_queue, self._output_queue, self._music_stream_queue, self._aux_stream_queue):
            q.close()
            q.cancel_join_thread()

    def _spawn_decoder(self, source: str | None, is_pipe: bool, target_stream_queue: Queue) -> Popen[bytes]:
        args = ["ffmpeg"]
        kwargs: dict[str, Any] = {"stdout": PIPE, "stderr": DEVNULL}
        if isinstance(self._before_options, str):
            args.extend(shlex_split(self._before_options))
        args.append("-i")
        if is_pipe and source is None:
            args.append("-")
            kwargs["stdin"] = PIPE
        elif is_pipe and isinstance(source, str):
            args.append(source)
            kwargs["stdin"] = DEVNULL
        else:
            args.append(str(source))
            kwargs["stdin"] = DEVNULL
        args.extend([
            "-f", AUDIO_FORMAT, 
            "-ar", str(AUDIO_RATE_HZ), 
            "-ac", str(AUDIO_CHANNELS), 
            "-loglevel", "quiet"
        ])
        if isinstance(self._options, str):
            args.extend(shlex_split(self._options))
        args.append("pipe:1")
        proc = Popen(args, **kwargs)
        if is_pipe and source is None and proc.stdin:
            def child_stdin_writer() -> None:
                while proc.poll() is None:
                    try:
                        chunk = target_stream_queue.get(timeout=1.0)
                        if not chunk: 
                            break
                        proc.stdin.write(chunk)
                        proc.stdin.flush()
                    except Empty:
                        continue
                    except Exception:
                        break
                try:
                    proc.stdin.close()
                except Exception:
                    pass
            threading.Thread(target=child_stdin_writer, daemon=True).start()
        return proc

    def _read_stream(self, process: Popen[bytes] | None) -> bytes | None:
        if not process or not process.stdout: 
            return None
        try:
            data = process.stdout.read(PCM_FRAME_SIZE)
            if data == b"" and process.poll() is not None: 
                return None
            if not data: 
                return b"\x00" * PCM_FRAME_SIZE
            if len(data) < PCM_FRAME_SIZE:
                return data + b"\x00" * (PCM_FRAME_SIZE - len(data))
            return data
        except Exception:
            return None

    def _spawn_parent_feeder_thread(self, stream: BufferedIOBase, target_queue: Queue) -> None:
        self._clear_queue(target_queue)
        def parent_feeder() -> None:
            while True:
                try:
                    data = stream.read(4096)
                    if not data:
                        target_queue.put(b"")  
                        break
                    target_queue.put(data)
                except Exception:
                    break
        threading.Thread(target=parent_feeder, daemon=True).start()

    def _clear_queue(self, target_queue: Queue) -> None:
        while not target_queue.empty():
            try:
                target_queue.get_nowait()
            except Empty:
                break