import asyncio
import logging
from functools import partial

import yt_dlp

from bot.config import DOWNLOAD_DIR

logger = logging.getLogger(__name__)

COMMON_RESOLUTIONS = {"360p", "480p", "720p", "1080p"}


async def get_video_info(url: str) -> dict:
    """Fetch video metadata and available resolutions (no download)."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }

    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await loop.run_in_executor(
            None, partial(ydl.extract_info, url, download=False)
        )

    seen_resolutions: set[str] = set()
    formats: list[dict] = []
    for f in info.get("formats", []):
        height = f.get("height")
        if not height:
            continue
        resolution = f"{height}p"
        if resolution not in COMMON_RESOLUTIONS:
            continue
        if resolution in seen_resolutions:
            continue
        seen_resolutions.add(resolution)
        formats.append(
            {
                "resolution": resolution,
                "height": height,
                "filesize_approx": f.get("filesize") or f.get("filesize_approx"),
            }
        )

    # Sort by height ascending (360p, 480p, 720p, 1080p)
    formats.sort(key=lambda x: x["height"])

    return {
        "title": info.get("title"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "formats": formats,
    }


async def download_video(url: str, height: int) -> tuple[str, str]:
    """Download video at the given resolution. Returns (file_path, title)."""
    opts = {
        "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
        "outtmpl": DOWNLOAD_DIR + "/%(title)s.%(ext)s",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await loop.run_in_executor(None, partial(ydl.extract_info, url))

    title = info.get("title", "video")
    file_path = info["requested_downloads"][0]["filepath"]
    return file_path, title


async def download_audio(url: str) -> tuple[str, str]:
    """Download audio as MP3. Returns (file_path, title)."""
    opts = {
        "format": "bestaudio/best",
        "outtmpl": DOWNLOAD_DIR + "/%(title)s.%(ext)s",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await loop.run_in_executor(None, partial(ydl.extract_info, url))

    title = info.get("title", "audio")
    file_path = info["requested_downloads"][0]["filepath"]
    return file_path, title
