# Plan: YouTube Downloader Telegram Bot

## Goal
Создать Telegram-бота для скачивания видео/аудио с YouTube. Отправляешь ссылку → выбираешь формат и качество → получаешь файл в чат (или в Яндекс.Диск если большой).

## Steps

- [x] Brainstorming и дизайн — требования, UX flow, архитектура
- [x] Написать дизайн-документ (`docs/plans/2026-02-20-youtube-downloader-bot-design.md`)
- [x] Инициализация проекта — git init, .gitignore, README.md, структура папок
- [ ] Создать GitHub репо, init commit
- [ ] Реализовать `bot/config.py` — загрузка .env конфигурации
- [ ] Реализовать `bot/downloader.py` — скачивание через yt-dlp
- [ ] Реализовать `bot/handlers.py` — обработчики команд и callback'ов
- [ ] Реализовать `bot/main.py` — точка входа
- [ ] Создать `.env.example` и `requirements.txt`
- [ ] Тестирование — проверить полный flow локально
- [ ] Деплой на старый Mac
