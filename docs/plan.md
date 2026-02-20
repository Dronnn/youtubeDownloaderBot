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
