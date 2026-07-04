import yt_dlp

__all__ = ["YTDL", "FFMPEG_OPTIONS"]

YTDL_OPTIONS = {
    "format": "bestaudio[abr<=96]/bestaudio[abr<=128]/bestaudio/best",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "youtube_include_dash_manifest": False,
    "youtube_include_hls_manifest": False,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -reconnect_on_network_error 1",
    "options": "-vn -thread_queue_size 4096",
}

YTDL = yt_dlp.YoutubeDL(YTDL_OPTIONS)