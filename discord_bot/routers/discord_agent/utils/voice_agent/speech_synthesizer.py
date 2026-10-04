from __future__ import annotations
import re
from pathlib import Path
from typing import Protocol
from numpy import int16, ndarray
from torch import Tensor, inference_mode, package, set_num_threads
from ru_normalizr import NormalizeOptions, normalize

__all__ = ["SpeechSynthesizer"]

_LATIN_PATTERN = re.compile(r"[A-Za-z]+")
_NORMALIZER_OPTIONS = NormalizeOptions.tts()

class SileroTTSModel(Protocol):
    def to(self, device: str) -> None: ...
    def apply_tts(self,
                  *,
                  text: str = "",
                  ssml_text: str = "",
                  speaker: str,
                  sample_rate: int,
                  put_accent: bool = False,
                  put_yo: bool = False) -> Tensor: ...

class SpeechSynthesizer:
    def __init__(self,
                 model_path: Path,
                 speaker: str = "baya",
                 sample_rate: int = 48000,
                 threads: int = 4) -> None:
        set_num_threads(threads)
        model: SileroTTSModel = package.PackageImporter(str(model_path)).load_pickle("tts_models", "model")
        model.to("cpu")
        self._model: SileroTTSModel = model
        self._speaker = speaker
        self._sample_rate = sample_rate

    def synthesize(self, text: str, rate: str | None = None) -> bytes:
        text = self._russify(text)
        with inference_mode():
            if rate is not None:
                audio: Tensor = self._model.apply_tts(
                    ssml_text=f"<speak><prosody rate=\"{rate}\">{text}</prosody></speak>",
                    speaker=self._speaker,
                    sample_rate=self._sample_rate,
                )
            else:
                audio = self._model.apply_tts(
                    text=text,
                    speaker=self._speaker,
                    sample_rate=self._sample_rate,
                    put_accent=True,
                    put_yo=True,
                )
        samples: ndarray = audio.detach().cpu().numpy()
        return (samples * 32767.0).astype(int16).tobytes()

    @staticmethod
    def _russify(text: str) -> str:
        return _LATIN_PATTERN.sub(lambda m: normalize(m.group(0), _NORMALIZER_OPTIONS), text)