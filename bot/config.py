import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment / .env file")

YANDEX_DISK_PATH: str = os.getenv("YANDEX_DISK_PATH", "")
if not YANDEX_DISK_PATH:
    raise ValueError("YANDEX_DISK_PATH is not set in environment / .env file")

_allowed_raw = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS: list[int] = (
    [int(uid.strip()) for uid in _allowed_raw.split(",") if uid.strip()]
    if _allowed_raw.strip()
    else []
)

DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "/tmp/yt_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_TELEGRAM_SIZE: int = int(os.getenv("MAX_TELEGRAM_SIZE", "52428800"))

FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "/usr/local/bin/ffmpeg")
