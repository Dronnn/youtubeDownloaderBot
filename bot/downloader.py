import asyncio
import logging
import os
import subprocess
from functools import partial

import yt_dlp

from bot.config import DOWNLOAD_DIR, FFMPEG_PATH, MAX_TELEGRAM_SIZE

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
        "ffmpeg_location": FFMPEG_PATH,
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
        "ffmpeg_location": FFMPEG_PATH,
        "quiet": True,
        "no_warnings": True,
    }

    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await loop.run_in_executor(None, partial(ydl.extract_info, url))

    title = info.get("title", "audio")
    file_path = info["requested_downloads"][0]["filepath"]
    return file_path, title


async def compress_to_fit(file_path: str) -> str:
    """Compress file with ffmpeg to fit under MAX_TELEGRAM_SIZE (49 MB target).

    For video: re-encode with calculated bitrate.
    For audio: re-encode at lower bitrate.
    Returns path to compressed file (original is kept).
    """
    target_bytes = MAX_TELEGRAM_SIZE - 1_048_576  # 1 MB margin
    file_size = os.path.getsize(file_path)

    if file_size <= MAX_TELEGRAM_SIZE:
        return file_path

    base, ext = os.path.splitext(file_path)
    compressed_path = f"{base}_compressed{ext}"

    # Get duration
    probe_cmd = [
        FFMPEG_PATH.replace("ffmpeg", "ffprobe") if "ffmpeg" in FFMPEG_PATH else "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]

    loop = asyncio.get_event_loop()

    try:
        result = await loop.run_in_executor(
            None,
            partial(subprocess.run, probe_cmd, capture_output=True, text=True, timeout=30),
        )
        duration = float(result.stdout.strip())
    except Exception:
        logger.warning("Could not probe duration, using fallback bitrate")
        duration = 300  # fallback 5 min

    if ext.lower() in (".mp3", ".m4a", ".aac", ".ogg", ".opus"):
        # Audio: calculate target bitrate in kbps
        target_bitrate_kbps = int((target_bytes * 8) / duration / 1000)
        target_bitrate_kbps = max(64, min(target_bitrate_kbps, 192))

        cmd = [
            FFMPEG_PATH, "-i", file_path,
            "-b:a", f"{target_bitrate_kbps}k",
            "-y", compressed_path,
        ]
    else:
        # Video: calculate total bitrate, reserve 128k for audio
        total_bitrate_kbps = int((target_bytes * 8) / duration / 1000)
        audio_bitrate_kbps = 128
        video_bitrate_kbps = max(200, total_bitrate_kbps - audio_bitrate_kbps)

        cmd = [
            FFMPEG_PATH, "-i", file_path,
            "-b:v", f"{video_bitrate_kbps}k",
            "-b:a", f"{audio_bitrate_kbps}k",
            "-y", compressed_path,
        ]

    logger.info("Compressing %s (%.1f MB) to fit under %.0f MB",
                file_path, file_size / 1024 / 1024, MAX_TELEGRAM_SIZE / 1024 / 1024)

    try:
        await loop.run_in_executor(
            None,
            partial(subprocess.run, cmd, capture_output=True, text=True, timeout=600),
        )
    except Exception as e:
        logger.error("Compression failed: %s", e)
        if os.path.exists(compressed_path):
            os.remove(compressed_path)
        raise

    if os.path.exists(compressed_path) and os.path.getsize(compressed_path) <= MAX_TELEGRAM_SIZE:
        return compressed_path

    # Compression didn't shrink enough — clean up
    if os.path.exists(compressed_path):
        os.remove(compressed_path)
    raise RuntimeError(f"Сжатый файл всё ещё слишком большой ({os.path.getsize(compressed_path) / 1024 / 1024:.1f} MB)")
