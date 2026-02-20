# Code Review Log — 2026-02-20

## Findings

### 1. VERSION MISMATCH (python-telegram-bot v22)
- **Status**: v22 is compatible. Breaking changes in v22 are about removed deprecated features (filters.CHAT, Defaults.disable_web_page_preview, quote→do_quote). None of these are used in the project code.
- **Action**: Keep v22. No code changes needed for this.

### 2. SECURITY — Missing whitelist in callbacks
- `format_callback` and `resolution_callback` have no `ALLOWED_USERS` check.
- An unauthorized user could craft a callback query to bypass the URL handler's check.
- **Fix**: Add `user_id not in ALLOWED_USERS` guard at top of both.

### 3. SECURITY — .env.example
- Contains `ALLOWED_USERS=123456789,987654321` which looks like real IDs.
- **Fix**: Change to `ALLOWED_USERS=YOUR_TELEGRAM_ID`.

### 4. BUG — download_video/download_audio signature mismatch
- `downloader.py` defines `download_video(url, format_id, download_dir)` → returns `str`
- `handlers.py` calls `download_video(url, format_id)` → expects tuple `(file_path, title)`
- Same for `download_audio(url, download_dir)` → handlers expect `(file_path, title)`
- **Fix**: Update downloader to accept DOWNLOAD_DIR from config internally, return (path, title) tuple.

### 5. BUG — format_callback processes get_video_info result wrong
- `get_video_info()` returns a dict with keys: title, duration, thumbnail, formats
- `format_callback` assigns the full dict to `formats` and iterates it like a list
- Line 87: `if not formats` — this checks the whole dict, which is always truthy
- Line 92: `for fmt in formats` — iterates dict keys, not the formats list
- **Fix**: Extract `formats["formats"]` properly.

### 6. YT-DLP — Use requested_downloads for filepath
- Current code uses progress_hook + prepare_filename fallback — fragile.
- **Fix**: Use `info['requested_downloads'][0]['filepath']` after download.

### 7. YT-DLP — Use format strings instead of format_id
- Current code passes raw format_id from info extraction. After format selection in UI, the format_id may not be stable.
- **Fix**: Store resolution (height) in user_data, use `bestvideo[height<=X]+bestaudio/best[height<=X]` format string.

### 8. Duplicate logging.basicConfig
- Called in both config.py and main.py with different formats.
- **Fix**: Remove from config.py, keep only in main.py.

---

## Changes Made

### bot/config.py
- Removed `import logging` and `logging.basicConfig()` (duplicate — main.py owns logging config)

### bot/downloader.py (rewritten)
- Imports `DOWNLOAD_DIR` from config instead of accepting it as parameter
- `get_video_info()`: added deduplication of resolutions (seen_resolutions set), stores `height` as int in format dicts, sorts formats by height ascending, removed `ext` filter (format strings handle this)
- `download_video(url, height)`: takes `height: int` instead of `format_id: str`; uses format string `bestvideo[height<=X]+bestaudio/best[height<=X]` with `merge_output_format: mp4`; uses `info['requested_downloads'][0]['filepath']` for output path; returns `tuple[str, str]` (path, title)
- `download_audio(url)`: no longer takes `download_dir` param; uses `info['requested_downloads'][0]['filepath']` for output path; returns `tuple[str, str]` (path, title)
- Removed all progress_hook code and prepare_filename fallbacks

### bot/handlers.py (rewritten)
- Added `ALLOWED_USERS` whitelist check at top of `format_callback()` and `resolution_callback()`
- `handle_url()`: added `ALLOWED_USERS and` guard so empty whitelist allows all users
- `format_callback()`: fixed — now correctly extracts `info["formats"]` list from the dict returned by `get_video_info()`; callback_data now uses `res:{height}` instead of `res:{format_id}:{resolution}`
- `resolution_callback()`: parses `height` as int from callback_data; calls `download_video(url, height)` with correct signature; added `ValueError` guard for malformed callback data
- Renamed `send_file` → `_send_file` and `download_and_send_audio` → `_download_and_send_audio` (private helpers)
- `_send_file()`: removed unused `title` parameter
- Removed unused `DOWNLOAD_DIR` import

### .env.example
- Changed `ALLOWED_USERS=123456789,987654321` → `ALLOWED_USERS=YOUR_TELEGRAM_ID`

### Files checked, no changes needed
- `bot/main.py` — correct, all imports and handler registrations match
- `bot/__init__.py` — empty, correct
- `requirements.txt` — v22 is compatible, no changes needed
- `README.md` — no issues found
- `.gitignore` — no issues found
- No AI/LLM attribution found in any file
