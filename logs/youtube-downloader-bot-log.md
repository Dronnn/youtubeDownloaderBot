# Log: YouTube Downloader Telegram Bot

## Step 1: Brainstorming и дизайн
- Определены требования: Python, python-telegram-bot + yt-dlp, монолит
- UX flow: ссылка → видео/аудио → разрешение → скачивание → отправка (или Яндекс.Диск)
- Деплой: старый Mac, venv, не ломать существующие 4 бота
- Доступ: whitelist Telegram ID
- Лимит 50 MB через стандартный Bot API, fallback на Яндекс.Диск

## Step 2: Дизайн-документ
- Создан `docs/plans/2026-02-20-youtube-downloader-bot-design.md`
- Описаны: структура проекта, конфигурация, компоненты, error handling

## Step 3: Инициализация проекта
- Начато: создание git repo, .gitignore, README, структура
- Создан `.gitignore` — Python, venv, .env, IDE, OS, downloads, temp, logs
- Создан `bot/__init__.py` — пустой файл пакета
- Создан `.env.example` — шаблон переменных окружения (BOT_TOKEN, ALLOWED_USERS, и т.д.)
- Создан `requirements.txt` — python-telegram-bot, yt-dlp, python-dotenv
- Создан `README.md` — на русском, автор Andreas Maier, инструкции по установке и использованию
