# Log: Always save to Yandex.Disk + tmp inside Yandex.Disk

## Step 1: Update bot/config.py
- Removed `DOWNLOAD_DIR` env var support (was `os.getenv("DOWNLOAD_DIR", "/tmp/yt_downloads")`)
- Now derived: `DOWNLOAD_DIR = os.path.join(YANDEX_DISK_PATH, "tmp")`
- `os.makedirs(DOWNLOAD_DIR, exist_ok=True)` kept as-is
- File changed: `bot/config.py` line 22

## Step 2: Update bot/handlers.py _send_file
- Rewrote `_send_file` to always copy to Yandex.Disk first (via `_yandex_dest`), regardless of file size
- Small files (<=50 MB): saved to Yandex.Disk, then sent to Telegram, then tmp file deleted
- Large files (>50 MB): saved to Yandex.Disk, user prompted about compression (same as before)
- If Yandex.Disk copy fails on a small file, still attempts Telegram send
- If Yandex.Disk copy fails on a large file, returns early (can't send via Telegram anyway)

## Step 3: Update bot/handlers.py help_command
- Updated help text to reflect that all files are saved to Yandex.Disk automatically
- Clarified that files <=50 MB are additionally sent to Telegram

## Step 4: Update .env
- Removed `DOWNLOAD_DIR=/tmp/yt_downloads` line (no longer configurable, always derived)

## Step 5: Verify compress_callback and cancel_command
- `cancel_command`: uses `DOWNLOAD_DIR` to glob and delete temp files — still correct, now cleans `{YANDEX_DISK_PATH}/tmp/*`
- `compress_callback`:
  - On "compress:no": deletes pending temp file from tmp/, shows "Оригинал сохранён в Яндекс.Диск" — correct, original is already saved
  - On successful compression+send: deletes compressed file and original temp file — correct
  - On still-too-large: deletes compressed attempt file, keeps original temp for next attempt — correct
- No changes needed in compress_callback or cancel_command
