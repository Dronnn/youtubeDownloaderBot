# YouTube Downloader Bot

Telegram-бот для скачивания видео и аудио с YouTube.

**Автор:** Andreas Maier

## Возможности

- Скачивание видео с YouTube по ссылке
- Выбор формата: видео (MP4) или аудио (MP3)
- Выбор разрешения для видео (360p, 480p, 720p, 1080p)
- Отправка файла прямо в Telegram-чат (до 50 МБ)
- Автоматическое сохранение больших файлов на Яндекс.Диск
- Whitelist — доступ только для разрешённых пользователей

## Требования

- Python 3.11+
- Telegram Bot Token (через [@BotFather](https://t.me/BotFather))
- Яндекс.Диск (опционально, для больших файлов)

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/amaier/youtubeDownloaderBot.git
cd youtubeDownloaderBot

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Настроить переменные окружения
cp .env.example .env
# Отредактировать .env — указать свой BOT_TOKEN и остальные параметры
```

## Конфигурация (.env)

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен Telegram-бота от BotFather |
| `ALLOWED_USERS` | Telegram ID разрешённых пользователей (через запятую) |
| `YANDEX_DISK_PATH` | Путь к папке Яндекс.Диска для больших файлов |
| `DOWNLOAD_DIR` | Директория для временных файлов |
| `MAX_TELEGRAM_SIZE` | Максимальный размер файла для отправки через Telegram (байт) |

## Использование

```bash
# Запуск бота
python -m bot.main
```

### Команды

- `/start` — приветствие и краткая инструкция
- `/help` — список команд и описание

### Flow

1. Отправить ссылку на YouTube-видео
2. Бот покажет информацию о видео и предложит выбрать формат (видео / аудио)
3. Для видео — выбрать разрешение
4. Бот скачает файл и отправит в чат
5. Если файл больше 50 МБ — бот сохранит его на Яндекс.Диск и отправит уведомление

## Структура проекта

```
youtubeDownloaderBot/
├── bot/
│   ├── __init__.py
│   ├── main.py          # Точка входа
│   ├── config.py         # Загрузка конфигурации
│   ├── handlers.py       # Обработчики команд и callback'ов
│   └── downloader.py     # Логика скачивания через yt-dlp
├── .env.example
├── requirements.txt
└── README.md
```
