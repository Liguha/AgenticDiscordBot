# preloaded_binaries

Preloaded model weights for local pipeline stages (ASR / TTS). Everything in
this folder **except this README** is stored in Git LFS (see `.gitattributes`)
— these are large binaries, do not commit unpacked weights anywhere else.

| folder | contents | used by |
|---|---|---|
| `whisper-tiny/` | faster-whisper tiny, int8 CT2 weights (~75 MB) | `speech_recognizer.py` (ASR) |
| `silero-tts/` | Silero TTS v5 RU checkpoint (`v5_ru.pt`, ~145 MB) | `speech_synthesizer.py` (TTS) |

Silero VAD ships bundled with `faster-whisper` package assets (no weights needed).

Folder paths are resolved via `discord_bot/globals.py::PRELOADED_BINARIES_FOLDER`.