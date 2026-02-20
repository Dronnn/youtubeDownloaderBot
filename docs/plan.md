# Plan: YouTube Downloader Telegram Bot

## Goal
Создать Telegram-бота для скачивания видео/аудио с YouTube. Отправляешь ссылку → выбираешь формат и качество → получаешь файл в чат (или в Яндекс.Диск если большой).

## Steps

- [x] Brainstorming и дизайн — требования, UX flow, архитектура
- [x] Написать дизайн-документ (`docs/plans/2026-02-20-youtube-downloader-bot-design.md`)
- [x] Инициализация проекта — git init, .gitignore, README.md, структура папок
- [x] Создать GitHub репо, init commit
- [x] Реализовать `bot/config.py` — загрузка .env конфигурации
- [x] Реализовать `bot/downloader.py` — скачивание через yt-dlp
- [x] Реализовать `bot/handlers.py` — обработчики команд и callback'ов
- [x] Реализовать `bot/main.py` — точка входа
- [x] Создать `.env.example` и `requirements.txt`
- [x] Code review и исправление ошибок
- [x] Деплой на старый Mac (macbook-i7, Python 3.12.12)
- [x] Исправление ffmpeg_location (PATH недоступен при nohup)
- [x] Установка ffprobe (нужен для compress_to_fit)
- [x] Функция сжатия файлов (compress_to_fit — до 49 МБ через ffmpeg)
- [x] Запрос у пользователя перед сжатием (inline-кнопки: сжать / Яндекс.Диск)
- [x] Выбор битрейта аудио (96 / 128 / 192 / 320 kbps)
- [x] Разделение папок Яндекс.Диска на Video / Audio
- [x] Отладка проблемы с Screen Sharing (firewall disable/enable)
- [x] Обновление .env с реальным путём Яндекс.Диска
- [ ] Финальное end-to-end тестирование (видео + аудио + сжатие + Яндекс.Диск)
- [ ] Автоматический запуск через launchd (LaunchAgent plist)

---

## Deploy to macbook-i7 (2026-02-20)

Target: old Mac via SSH (`ssh macbook-i7`), Python 3.12.12 at `/usr/local/bin/python3.12`

- [x] Step 1: Check existing bots (noted 4 bots + uvicorn + postgres)
- [x] Step 2: Install ffmpeg 8.0.1-tessus static binary to /usr/local/bin (no sudo needed)
- [x] Step 3: Clone repo from GitHub (fresh clone)
- [x] Step 4: Create venv with Python 3.12.12
- [x] Step 5: Install dependencies — python-telegram-bot 22.6, yt-dlp 2026.2.4, etc.
- [x] Step 6: Create .env file and temp directories (/tmp/yt_downloads, /tmp/yt_yandex)
- [x] Step 7: Test run — Config OK, token starts with 8180875918
- [x] Step 8: Start bot in background (nohup, PID 79737)
- [x] Step 9: Bot running, log shows "Application started" + Telegram API 200 OK
- [x] Step 10: All 4 original bots + uvicorn + postgres still running — nothing disturbed

---

## Large-file compression loop + /cancel command (2026-02-20)

### Goal
Rework oversized-file handling: always save original to Yandex.Disk first, then offer
iterative compression with user confirmation after each attempt. Add /cancel command.

### Steps
- [x] Update `bot/downloader.py`: add `compress_file()` and `calculate_bitrate()`
- [x] Update `bot/handlers.py`: rewrite `_send_file()`, replace `toobig_callback` with
      `compress_callback`, add `cancel_command`
- [x] Update `bot/main.py`: register new handlers, remove old `toobig_callback`
- [x] git commit and push
- [x] Deploy to macbook-i7, verify bot starts

---

## Code Review & Bugfix (2026-02-20)

- [x] VERSION MISMATCH: проверить совместимость кода с python-telegram-bot v22 — OK, совместим
- [x] SECURITY: добавить whitelist-проверку в format_callback и resolution_callback
- [x] SECURITY: поправить .env.example — убрать реальные данные, только плейсхолдеры
- [x] YT-DLP: перейти на `requested_downloads` для получения filepath
- [x] YT-DLP: перейти на format-строки вместо format_id для видео
- [x] HANDLERS: исправить вызовы download_video/download_audio (сигнатуры не совпадали)
- [x] HANDLERS: исправить format_callback (обрабатывал результат get_video_info неправильно)
- [x] CODE QUALITY: общая чистка, проверка error handling, cleanup временных файлов
- [x] COMPATIBILITY: проверена совместимость с macOS Big Sur (Python 3.11, yt-dlp, python-telegram-bot v22)

---

## Always save to Yandex.Disk + tmp inside Yandex.Disk (2026-02-20)

### Goal
All downloaded files should always be saved to Yandex.Disk (Video/ or Audio/), not just
files over 50 MB. Temporary download directory moves from /tmp/yt_downloads to
{YANDEX_DISK_PATH}/tmp so downloads happen directly on the Yandex.Disk volume.

### Steps
- [x] Update `bot/config.py`: derive DOWNLOAD_DIR from YANDEX_DISK_PATH instead of env var
- [x] Update `bot/handlers.py` `_send_file`: always copy to Yandex.Disk before sending
- [x] Update `bot/handlers.py` `help_command`: reflect that all files go to Yandex.Disk
- [x] Update `.env`: remove DOWNLOAD_DIR line
- [x] Verify compress_callback and cancel_command still clean up tmp files correctly

---

## Revert "always save to Yandex.Disk" (2026-02-20)

### Goal
Revert the always-save-to-Yandex.Disk behavior. Original logic: files <= 50 MB go to
Telegram only (no Yandex.Disk), files > 50 MB go to Yandex.Disk with compression prompt.

### Steps
- [x] Revert `bot/config.py`: DOWNLOAD_DIR back to env var with default `/tmp/yt_downloads`
- [x] Revert `bot/handlers.py` `_send_file`: Yandex.Disk copy only for > 50 MB
- [x] Revert `bot/handlers.py` `help_command`: original help text
- [x] Revert `.env`: add back `DOWNLOAD_DIR=/tmp/yt_downloads`

---

## Progress reporting in Telegram chat (2026-02-20)

### Goal
Show download/conversion progress in Telegram messages (e.g. "Скачиваю... 34% (12.5 / 36.8 MB)"),
updating every ~4 seconds. Uses yt-dlp progress_hooks and postprocessor hooks.

### Steps
- [x] Update `bot/downloader.py`: add `_make_hooks()`, wire `progress_callback` into `download_video` and `download_audio`
- [x] Update `bot/handlers.py`: add `_make_tg_progress()`, pass progress callback from `resolution_callback` and `audio_callback`
- [x] Verify no imports or existing functionality broken

---

## Bot management script on macbook-i7 (2026-02-20)

### Goal
Create `/Users/andrewmaier/manage-bots.sh` on macbook-i7 — a single script to start/stop/restart/status
all 5 Telegram bots running on that machine. PID-file based, colorized output, safe stop via PID only.

### Steps
- [x] Write manage-bots.sh via SSH and chmod +x
- [x] Test with `status` command (no stop/restart)

---

## Large-file handling improvements (2026-02-20)

### Goal
Support Local Telegram Bot API Server for 2 GB file uploads while keeping compression as fallback.
Add "Оригинал" (original) audio option for fastest downloads without conversion.

### Steps
- [x] Add Local Bot API Server support — implement `use_local_api` config flag
- [x] Add "Оригинал" audio option — download raw audio without ffmpeg conversion (fastest)
- [x] Compression as fallback — keep iterative compression for files > 2 GB only
- [x] Update help text to document new options
- [x] git commit: "Add Local Bot API Server support for 2 GB file uploads"
- [x] git commit: "Add original audio format option and improve progress messages"

---

## Progress messages improvements (2026-02-20)

### Goal
Enhance progress reporting throughout download-send pipeline with separate progress bars for
video/audio tracks, post-processing steps, and file upload.

### Steps
- [x] Video/audio download progress — show percentage, speed, and MB downloaded
- [x] Separate progress lines for video track and audio track downloads (when merging)
- [x] Post-processing progress — merging and conversion to MP3 (if applicable)
- [x] Upload progress — "Отправляю в Telegram (X MB)..." status message
- [x] Telegram message updates — dedup identical text, catch BadRequest silently
- [x] git commit: "Improve progress messages throughout download-send pipeline"

---

## Documentation and deployment (2026-02-20)

### Goal
Document deployment process and best practices for managing bot instances.

### Steps
- [x] Create `DEPLOY.md` — deployment guide for local Telegram Bot API Server
- [x] Document manage-bots.sh usage and PID-file management
- [x] Add version constraints and compatibility notes

---

## Audio format choice + webm→MP3 conversion (2026-02-20)

### Goal
Дать пользователю полный выбор формата аудио. После отправки webm предложить
конвертацию в MP3 без потери качества.

### Steps
- [x] Обновить кнопки аудио: Оригинал (webm/opus) / MP3 96 / MP3 128 / MP3 192 / MP3 320
- [x] Добавить `convert_to_mp3()` в downloader.py (ffmpeg `-q:a 0`)
- [x] Добавить `convert_callback` — после отправки webm спрашивает "Сконвертировать в MP3?"
- [x] Зарегистрировать обработчик `convert:` в main.py
- [x] git commit: "Add audio format choice and post-send MP3 conversion option"

---

## Telegram command menu (2026-02-20)

- [x] Добавить `set_my_commands` в `post_init` — кнопка меню: /start, /help, /cancel
- [x] git commit: "Add Telegram command menu (start, help, cancel)"

---

## Local API: file path instead of streaming (2026-02-20)

- [x] `send_document(document=Path(file_path))` в local mode — сервер читает с диска, без таймаутов
- [x] Увеличены HTTP таймауты до 300 сек как fallback
- [x] Обновлена справка: лимит 2 GB, актуальные форматы
- [x] git commits: "Use local file paths for send_document", "Increase HTTP timeouts", "Update help text"

---

## Testing and validation (2026-02-20)

- [ ] End-to-end test: download video at multiple resolutions, verify quality
- [ ] End-to-end test: download audio at 96/128/192/320 kbps, verify quality
- [ ] End-to-end test: "Оригинал" audio option (raw download without ffmpeg)
- [ ] Test file > 2 GB with Local Bot API Server
- [ ] Test file > 2 GB fallback compression (if Server unavailable)
- [ ] Verify progress messages update smoothly (no spam, dedup working)
- [ ] Verify /cancel command stops download gracefully
- [ ] Verify Yandex.Disk upload on compression failure

---

## Remaining / Future

- [ ] Auto-start via launchd (LaunchAgent plist) — not critical for MVP
- [ ] Rate limiting and cooldown for repeated requests
- [ ] Logging to file for debugging on production machine
