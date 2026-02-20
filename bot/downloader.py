import asyncio
import logging
import os
import subprocess
import time
from functools import partial

import yt_dlp

from bot.config import DOWNLOAD_DIR, FFMPEG_PATH, MAX_TELEGRAM_SIZE

logger = logging.getLogger(__name__)

COMMON_RESOLUTIONS = {"360p", "480p", "720p", "1080p"}

_UPDATE_INTERVAL = 4.0  # seconds between progress updates to Telegram


def _make_hooks(progress_callback):
    """Create yt-dlp progress_hook and postprocessor_hook that call progress_callback(text)."""
    last_update = {"t": 0.0}
    stream_count = {"n": 0}

    def progress_hook(d):
        if d["status"] == "downloading":
            now = time.time()
            if now - last_update["t"] < _UPDATE_INTERVAL:
                return
            last_update["t"] = now

            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            speed = d.get("speed")

            prefix = "Скачиваю"
            if stream_count["n"] == 1:
                prefix = "Скачиваю аудиодорожку"

            if total and total > 0:
                pct = downloaded / total * 100
                dl_mb = downloaded / 1024 / 1024
                total_mb = total / 1024 / 1024
                text = f"{prefix}... {pct:.0f}% ({dl_mb:.1f} / {total_mb:.1f} MB)"
            else:
                dl_mb = downloaded / 1024 / 1024
                text = f"{prefix}... {dl_mb:.1f} MB"

            if speed:
                text += f" | {speed / 1024 / 1024:.1f} MB/s"

            progress_callback(text)

        elif d["status"] == "finished":
            stream_count["n"] += 1
            if stream_count["n"] == 1:
                progress_callback("Видеодорожка скачана. Скачиваю аудио...")
            else:
                progress_callback("Скачано. Обрабатываю...")

    def pp_hook(d):
        pp = d.get("postprocessor", "")
        if d["status"] == "started":
            if pp == "FFmpegMergerPP":
                progress_callback("Объединяю видео и аудио...")
            elif pp == "FFmpegExtractAudio":
                progress_callback("Конвертирую в MP3...")
            elif pp == "MoveFiles":
                progress_callback("Отправляю в Telegram...")

    return progress_hook, pp_hook

_FFPROBE_PATH = FFMPEG_PATH.replace("ffmpeg", "ffprobe") if "ffmpeg" in FFMPEG_PATH else "ffprobe"


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


async def download_video(url: str, height: int, progress_callback=None) -> tuple[str, str]:
    """Download video at the given resolution. Returns (file_path, title)."""
    opts = {
        "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
        "outtmpl": DOWNLOAD_DIR + "/%(title)s.%(ext)s",
        "merge_output_format": "mp4",
        "ffmpeg_location": FFMPEG_PATH,
        "quiet": True,
        "no_warnings": True,
    }

    if progress_callback:
        progress_hook, pp_hook = _make_hooks(progress_callback)
        opts["progress_hooks"] = [progress_hook]

    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(opts) as ydl:
        if progress_callback:
            ydl.add_postprocessor_hook(pp_hook)
        info = await loop.run_in_executor(None, partial(ydl.extract_info, url))

    title = info.get("title", "video")
    file_path = info["requested_downloads"][0]["filepath"]
    return file_path, title


async def download_audio(url: str, bitrate: str = "192", progress_callback=None) -> tuple[str, str]:
    """Download audio as MP3 (or original format if bitrate='original')."""
    opts = {
        "format": "bestaudio/best",
        "outtmpl": DOWNLOAD_DIR + "/%(title)s.%(ext)s",
        "ffmpeg_location": FFMPEG_PATH,
        "quiet": True,
        "no_warnings": True,
    }

    if bitrate != "original":
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": bitrate,
            }
        ]

    if progress_callback:
        progress_hook, pp_hook = _make_hooks(progress_callback)
        opts["progress_hooks"] = [progress_hook]

    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(opts) as ydl:
        if progress_callback:
            ydl.add_postprocessor_hook(pp_hook)
        info = await loop.run_in_executor(None, partial(ydl.extract_info, url))

    title = info.get("title", "audio")
    file_path = info["requested_downloads"][0]["filepath"]
    return file_path, title


async def _get_duration(file_path: str) -> float:
    """Return media duration in seconds via ffprobe. Falls back to 300 s on error."""
    probe_cmd = [
        _FFPROBE_PATH,
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
        return float(result.stdout.strip())
    except Exception:
        logger.warning("Could not probe duration for %s, using 300 s fallback", file_path)
        return 300.0


def calculate_bitrate(
    duration: float,
    target_bytes: int,
    is_audio: bool,
    attempt: int = 1,
    prev_video_kbps: int = 0,
    prev_audio_kbps: int = 128,
) -> tuple[int, int]:
    """Return (video_bitrate_kbps, audio_bitrate_kbps) for a compression attempt.

    attempt=1 calculates from scratch; attempt>=2 reduces previous values by 40%.
    For audio-only files video_bitrate_kbps is always 0.
    """
    if attempt == 1:
        total_kbps = int((target_bytes * 8) / duration / 1000)
        if is_audio:
            audio_kbps = max(64, min(total_kbps, 192))
            return 0, audio_kbps
        else:
            audio_kbps = 128
            video_kbps = max(200, total_kbps - audio_kbps)
            return video_kbps, audio_kbps
    else:
        if is_audio:
            audio_kbps = max(64, int(prev_audio_kbps * 0.6))
            return 0, audio_kbps
        else:
            video_kbps = max(200, int(prev_video_kbps * 0.6))
            audio_kbps = max(96, int(prev_audio_kbps * 0.6))
            return video_kbps, audio_kbps


async def compress_file(
    file_path: str,
    video_bitrate_kbps: int,
    audio_bitrate_kbps: int = 128,
) -> tuple[str, int]:
    """Compress a media file using the supplied bitrates.

    Returns (compressed_path, actual_size_bytes).
    Raises RuntimeError if ffmpeg fails or produces no output.
    """
    base, ext = os.path.splitext(file_path)
    compressed_path = f"{base}_compressed{ext}"

    is_audio = ext.lower() in (".mp3", ".m4a", ".aac", ".ogg", ".opus")

    if is_audio:
        cmd = [
            FFMPEG_PATH, "-i", file_path,
            "-b:a", f"{audio_bitrate_kbps}k",
            "-y", compressed_path,
        ]
    else:
        cmd = [
            FFMPEG_PATH, "-i", file_path,
            "-b:v", f"{video_bitrate_kbps}k",
            "-b:a", f"{audio_bitrate_kbps}k",
            "-y", compressed_path,
        ]

    logger.info(
        "compress_file: %s (%.1f MB) video=%dk audio=%dk",
        file_path,
        os.path.getsize(file_path) / 1024 / 1024,
        video_bitrate_kbps,
        audio_bitrate_kbps,
    )

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            partial(subprocess.run, cmd, capture_output=True, text=True, timeout=600),
        )
    except Exception as e:
        logger.error("compress_file ffmpeg error: %s", e)
        if os.path.exists(compressed_path):
            os.remove(compressed_path)
        raise RuntimeError(f"ffmpeg failed: {e}") from e

    if not os.path.exists(compressed_path) or os.path.getsize(compressed_path) == 0:
        raise RuntimeError("ffmpeg produced no output file")

    return compressed_path, os.path.getsize(compressed_path)


async def compress_to_fit(file_path: str) -> str:
    """Legacy single-pass compression. Kept for reference; not used by handlers."""
    target_bytes = MAX_TELEGRAM_SIZE - 1_048_576
    file_size = os.path.getsize(file_path)

    if file_size <= MAX_TELEGRAM_SIZE:
        return file_path

    ext = os.path.splitext(file_path)[1]
    is_audio = ext.lower() in (".mp3", ".m4a", ".aac", ".ogg", ".opus")
    duration = await _get_duration(file_path)
    video_kbps, audio_kbps = calculate_bitrate(duration, target_bytes, is_audio, attempt=1)

    compressed_path, result_size = await compress_file(file_path, video_kbps, audio_kbps)
    if result_size <= MAX_TELEGRAM_SIZE:
        return compressed_path

    if os.path.exists(compressed_path):
        os.remove(compressed_path)
    raise RuntimeError(
        f"Сжатый файл всё ещё слишком большой ({result_size / 1024 / 1024:.1f} MB)"
    )
