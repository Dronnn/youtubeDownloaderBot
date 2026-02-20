# Log: Large-file compression loop + /cancel

Date: 2026-02-20

## Goal
Rework oversized-file flow: save to Yandex.Disk immediately, then offer iterative
compression with decreasing bitrate. Add /cancel command to abort and clean up.

## Work log

### Step 1 — downloader.py

Adding `calculate_bitrate(file_path, target_bytes, attempt, prev_video_kbps, prev_audio_kbps)`
and `compress_file(file_path, video_bitrate_kbps, audio_bitrate_kbps)`.

Keeping `compress_to_fit` only to avoid breaking anything outside these files (will be
unused after handlers refactor).

- Added `_get_duration()` helper using ffprobe
- Added `calculate_bitrate(duration, target_bytes, is_audio, attempt, prev_video_kbps, prev_audio_kbps)`
- Added `compress_file(file_path, video_bitrate_kbps, audio_bitrate_kbps)` -> (path, size)
- `compress_to_fit` refactored to use the two new functions internally

### Step 2 — handlers.py

- `_send_file()`: saves original to Yandex.Disk if > 50 MB, resets compression state,
  shows "Да, сжать / Нет, не надо" buttons
- `compress_callback()`: handles compress:yes/no; iterates with increasing aggression;
  checks cancelled flag after each slow ffmpeg call; cleans up intermediate files
- `cancel_command()`: sets cancelled=True, deletes all files in DOWNLOAD_DIR,
  clears all compression-related user_data keys
- Removed `toobig_callback`

### Step 3 — main.py

- Registered `cancel_command` (CommandHandler "cancel")
- Registered `compress_callback` (pattern "^compress:")
- Removed `toobig_callback` registration and import

### Step 4 — commit & push

Committed as d1562ef, pushed to origin/main.

### Step 5 — deploy

git pull on macbook-i7 succeeded. Old process pkill didn't kill all instances;
killed both PIDs manually (81213, 81330), restarted. Bot started cleanly at 15:28:56.
Log confirms: "Bot started" + "Application started".
