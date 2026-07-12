import yt_dlp
import numpy as np

__all__ = [
    "HIGH_BITRATE_KBPS",
    "SAMPLE_SIZE_BYTES",
    "AUDIO_RATE_HZ",
    "AUDIO_CHANNELS",
    "AUDIO_FORMAT",
    "AUDIO_FORMAT_NP",
    "FADE_DURATION_MS",
    "DUCKED_VOLUME",
    "NORMAL_VOLUME",
    "PCM_FRAME_SIZE",
    "CLIP_MIN",
    "CLIP_MAX",
    "FADE_SPEED",
    "OUTPUT_QUEUE_MAXSIZE",
    "STREAM_QUEUE_MAXSIZE",
    "YTDL_FORMAT_FILTER",
    "YTDL_SEARCH_OPTIONS",
    "YTDL_PLAYER_OPTIONS",
    "FFMPEG_OPTIONS",
    "YTDL_SEARCH",
    "YTDL_PLAYER"
]

HIGH_BITRATE_KBPS: int = 64  

SAMPLE_SIZE_BYTES: int = 2
FRAME_DURATION_MS: int = 20
AUDIO_RATE_HZ: int = 48000
AUDIO_CHANNELS: int = 2
AUDIO_FORMAT: str = "s16le"
AUDIO_FORMAT_NP: type = np.int16

FADE_DURATION_MS: int = 500
DUCKED_VOLUME: float = 0.15
NORMAL_VOLUME: float = 1.0

PCM_FRAME_SIZE: int = int(AUDIO_RATE_HZ * (FRAME_DURATION_MS / 1000) * AUDIO_CHANNELS * SAMPLE_SIZE_BYTES)
CLIP_MIN: int = np.iinfo(AUDIO_FORMAT_NP).min
CLIP_MAX: int = np.iinfo(AUDIO_FORMAT_NP).max

FADE_SPEED: float = FRAME_DURATION_MS / FADE_DURATION_MS 

OUTPUT_QUEUE_MAXSIZE: int = 10
STREAM_QUEUE_MAXSIZE: int = 64

YTDL_FORMAT_FILTER: str = f"bestaudio[abr<={HIGH_BITRATE_KBPS}]/bestaudio/best"

YTDL_SEARCH_OPTIONS: dict[str, str | bool | int] = {
    "format": YTDL_FORMAT_FILTER,
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": "in_playlist",
    "process": False,
}

YTDL_PLAYER_OPTIONS: dict[str, str | bool | int] = {
    "format": YTDL_FORMAT_FILTER,
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5 "
        "-thread_queue_size 512 "
        "-fflags +genpts"
    ),
    "options": "-vn -af aresample=async=1:min_hard_comp=0.010000:first_pts=0"
}

YTDL_SEARCH: yt_dlp.YoutubeDL = yt_dlp.YoutubeDL(YTDL_SEARCH_OPTIONS)
YTDL_PLAYER: yt_dlp.YoutubeDL = yt_dlp.YoutubeDL(YTDL_PLAYER_OPTIONS)