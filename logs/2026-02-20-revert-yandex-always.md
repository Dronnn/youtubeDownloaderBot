# Log: Revert "always save to Yandex.Disk"

## Step 1: Revert bot/config.py
- Changed DOWNLOAD_DIR from `os.path.join(YANDEX_DISK_PATH, "tmp")` back to `os.getenv("DOWNLOAD_DIR", "/tmp/yt_downloads")`
- This restores the original configurable download directory

## Step 2: Revert bot/handlers.py _send_file
- Removed the "always copy to Yandex.Disk" block at the top of _send_file
- Restored original logic: if <= 50 MB, send to Telegram and delete temp file; if > 50 MB, copy to Yandex.Disk and offer compression

## Step 3: Revert bot/handlers.py help_command
- Restored original help text describing the original behavior

## Step 4: Revert .env
- Added back DOWNLOAD_DIR=/tmp/yt_downloads
