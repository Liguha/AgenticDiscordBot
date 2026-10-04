from __future__ import annotations
from pathlib import Path
from collections.abc import Iterator
from numpy import float32, frombuffer, int16, ndarray
from faster_whisper import WhisperModel
from faster_whisper.transcribe import Segment, TranscriptionInfo
from scipy.signal import resample_poly

__all__ = ["SpeechRecognizer"]


class SpeechRecognizer:
    def __init__(self, model_path: Path, cpu_threads: int = 4) -> None:
        self._model = WhisperModel(
            str(model_path),
            device="cpu",
            compute_type="int8",
            cpu_threads=cpu_threads,
        )

    def transcribe(self, pcm: bytes, sample_rate: int = 48000) -> str:
        segments: Iterator[Segment]
        _info: TranscriptionInfo
        segments, _info = self._model.transcribe(
            self._to_float16k(pcm, sample_rate),
            language="ru",
            beam_size=3,
            best_of=3,
            vad_filter=True,
            without_timestamps=True,
            condition_on_previous_text=True,
        )
        return "".join(segment.text for segment in segments).strip()

    @staticmethod
    def _to_float16k(pcm: bytes, sample_rate: int) -> ndarray:
        audio = frombuffer(pcm, dtype=int16).astype(float32) / 32768.0
        if sample_rate != 16000:
            audio = resample_poly(audio, 16000, sample_rate).astype(float32)
        return audio