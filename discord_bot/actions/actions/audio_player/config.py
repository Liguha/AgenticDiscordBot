import yt_dlp

__all__ = ["YTDL_SEARCH", "YTDL_PLAYER", "FFMPEG_OPTIONS", "HIGH_BITRATE"]

HIGH_BITRATE = 64  

YTDL_FORMAT_FILTER = f"bestaudio[abr<={HIGH_BITRATE}]/bestaudio/best"

YTDL_SEARCH_OPTIONS = {
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

YTDL_PLAYER_OPTIONS = {
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
        "-thread_queue_size 1024 "
        "-fflags +genpts"
    ),
    "options": "-vn -af aresample=async=1:min_hard_comp=0.010000:first_pts=0"
}

YTDL_SEARCH = yt_dlp.YoutubeDL(YTDL_SEARCH_OPTIONS)
YTDL_PLAYER = yt_dlp.YoutubeDL(YTDL_PLAYER_OPTIONS)