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
- [ ] Тестирование — проверить полный flow на старом Mac
- [ ] Деплой на старый Mac

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
