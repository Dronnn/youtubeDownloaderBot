# Log: Progress reporting in Telegram chat

## 2026-02-20

### Step 1: Update bot/downloader.py
- Adding `import time` at module top
- Adding `_UPDATE_INTERVAL = 4.0` constant
- Adding `_make_hooks(progress_callback)` function that returns (progress_hook, pp_hook)
- Modifying `download_video()` signature: added optional `progress_callback=None`
- Modifying `download_audio()` signature: added optional `progress_callback=None`
- Both functions wire hooks into yt-dlp opts when callback is provided

### Step 2: Update bot/handlers.py
- Added `import asyncio` and `from telegram.error import BadRequest`
- Added `_make_tg_progress(chat_id, message_id, bot, loop)` helper
  - Returns a sync callback safe to call from background threads
  - Uses `asyncio.run_coroutine_threadsafe` to bridge into the event loop
  - Deduplicates identical text (skips if same as last sent)
  - Catches `BadRequest` ("message not modified") silently
  - Catches other exceptions (rate-limit, network) silently — next update will come
- Modified `resolution_callback`: gets event loop, creates progress_cb, passes to `download_video`
- Modified `audio_callback`: same pattern, passes to `download_audio`

### Step 3: Verification
- Reviewed both files end-to-end
- All existing functions untouched (get_video_info, compress_file, compress_to_fit, etc.)
- All existing handler flows preserved (format_callback, compress_callback, _send_file, etc.)
- `progress_callback` is optional (default None) — existing callers unaffected
- No new dependencies needed
