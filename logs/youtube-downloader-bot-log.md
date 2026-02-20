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

## Step 4: Git init + GitHub repo
- `git init` — инициализирован репозиторий
- Добавлены 8 файлов: .gitignore, .env.example, requirements.txt, README.md, bot/__init__.py, docs/plan.md, docs/plans/2026-02-20-youtube-downloader-bot-design.md, logs/youtube-downloader-bot-log.md
- Initial commit: `46d276e`
- Создан GitHub-репозиторий: https://github.com/Dronnn/youtubeDownloaderBot
- Push выполнен на `main`
- Visibility изменён на public (по запросу)

## Step 5: Реализация bot/config.py
- Загрузка конфигурации из .env через python-dotenv
- Валидация обязательных переменных (BOT_TOKEN, ALLOWED_USERS, YANDEX_DISK_PATH)
- Создание DOWNLOAD_DIR если не существует

## Step 6: Реализация bot/downloader.py
- get_video_info() — получение метаданных и списка форматов
- download_video() — скачивание видео в выбранном разрешении (mp4)
- download_audio() — скачивание аудио (mp3)
- Все функции async через run_in_executor

## Step 7: Реализация bot/handlers.py
- /start и /help команды
- Обработка YouTube URL с regex
- Inline-кнопки для выбора формата и разрешения
- Отправка файлов (Telegram или Яндекс.Диск)
- Whitelist проверка доступа

## Step 8: Реализация bot/main.py
- Точка входа, регистрация хендлеров, запуск polling

## Step 9: Обновление документации
- README.md обновлён
- requirements.txt проверен

## Step 10: Code review и исправления (2026-02-20)
- Прошёлся по всему коду, нашёл и исправил ряд проблем:
- SECURITY: в format_callback и resolution_callback не было проверки whitelist — добавлено
- SECURITY: в .env.example были реальные данные — заменены на плейсхолдеры
- YT-DLP: filepath брался через `info["filepath"]` — заменено на `info["requested_downloads"][0]["filepath"]` (правильный способ)
- YT-DLP: формат видео задавался через format_id — переделано на format-строку `bestvideo[height<=N]+bestaudio/best[height<=N]`
- HANDLERS: сигнатуры download_video/download_audio не совпадали с тем, что передавалось из handlers — исправлено
- HANDLERS: format_callback неправильно разбирал результат get_video_info — переделан
- CODE QUALITY: добавлен cleanup временных файлов в блок finally, улучшена обработка ошибок

## Step 11: Проверка совместимости с macOS Big Sur (2026-02-20)
- Целевая машина для деплоя работает на macOS Big Sur
- Python 3.11 доступен через Homebrew, совместим
- python-telegram-bot v22 требует Python 3.8+ — OK
- yt-dlp совместим с Big Sur без ограничений
- ffmpeg доступен через Homebrew, работает на Big Sur
- asyncio и run_in_executor — стандартные, без платформ-специфичных зависимостей
- Итог: несовместимостей не выявлено, деплой возможен

## Step 12: Исправление ffmpeg_location (2026-02-20)
- Проблема: при запуске через `nohup` переменная `$PATH` обрезана, `ffmpeg` не находится по имени
- Решение: добавил `FFMPEG_PATH` в `.env` с абсолютным путём к бинарнику (`/usr/local/bin/ffmpeg`)
- В `bot/config.py` добавлена переменная `FFMPEG_PATH` с дефолтным значением `/usr/local/bin/ffmpeg`
- В `download_video()` и `download_audio()` добавлен параметр `ffmpeg_location: FFMPEG_PATH` в опции yt-dlp
- После исправления скачивание и конвертация в MP3 работают корректно под nohup

## Step 13: Установка ffprobe (2026-02-20)
- Обнаружено: функция `compress_to_fit()` использует `ffprobe` для определения длительности файла
- На macbook-i7 ffprobe отсутствовал (был установлен только ffmpeg-бинарник без ffprobe)
- Установлен ffprobe — статический бинарник, скопирован в `/usr/local/bin/ffprobe`
- Проверка: `ffprobe -version` — OK
- Путь к ffprobe формируется автоматически из `FFMPEG_PATH` (замена `ffmpeg` → `ffprobe`)

## Step 14: Функция сжатия файлов (2026-02-20)
- Добавлена функция `compress_to_fit()` в `bot/downloader.py`
- Целевой размер: `MAX_TELEGRAM_SIZE - 1 MB` (около 49 МБ)
- Для видео: пересчитывается общий битрейт на основе длительности, видеобитрейт = total − 128k (аудио)
- Для аудио: пересчитывается битрейт, зажат между 64k и 192k
- Длительность определяется через ffprobe; при ошибке — fallback 300 секунд
- Сжатый файл сохраняется рядом с оригиналом (`_compressed` суффикс)
- Если после сжатия файл всё ещё больше лимита — выбрасывается RuntimeError, оригинал очищается

## Step 15: Запрос у пользователя перед сжатием (2026-02-20)
- Раньше при превышении лимита файл автоматически копировался на Яндекс.Диск
- Теперь бот присылает сообщение с двумя inline-кнопками:
  - «Сжать и отправить» — запускает compress_to_fit, отправляет в Telegram
  - «Сохранить в Яндекс.Диск» — копирует файл в папку Яндекс.Диска
- Добавлен хендлер `toobig_callback` в `handlers.py`, зарегистрирован в `main.py` по паттерну `^toobig:`
- Ссылка на текущий файл хранится в `context.user_data["pending_file"]`
- При неудаче сжатия — автоматический fallback на Яндекс.Диск с уведомлением пользователя

## Step 16: Выбор битрейта аудио (2026-02-20)
- При выборе формата «Аудио» теперь показывается дополнительное меню с кнопками: 96 / 128 / 192 / 320 kbps
- Добавлен хендлер `audio_callback` в `handlers.py`, зарегистрирован в `main.py` по паттерну `^audio:`
- Функция `download_audio()` принимает параметр `bitrate: str`, передаёт его в FFmpegExtractAudio postprocessor
- Дефолтный битрейт убран — пользователь всегда явно выбирает качество

## Step 17: Разделение папок Яндекс.Диска (2026-02-20)
- Раньше все файлы сохранялись в корень `YANDEX_DISK_PATH`
- Теперь: видео → `YANDEX_DISK_PATH/Video/`, аудио → `YANDEX_DISK_PATH/Audio/`
- Подпапки создаются автоматически через `os.makedirs(dest_dir, exist_ok=True)`
- Тип файла определяется из `context.user_data["file_type"]` (устанавливается в `resolution_callback` и `audio_callback`)
- Логика применяется в `toobig_callback` и в fallback при ошибке сжатия

## Step 18: Отладка Screen Sharing / Firewall (2026-02-20)
- Проблема: Screen Sharing на macbook-i7 не работал — подключение зависало
- Причина: macOS firewall блокировал входящие соединения для screensharingd
- Временно отключён firewall через `System Settings → Firewall → выкл.`
- После проверки Screen Sharing — firewall снова включён
- Бот и все остальные процессы не были затронуты

## Step 19: Обновление .env с реальным путём Яндекс.Диска (2026-02-20)
- Обновлён `YANDEX_DISK_PATH` в `.env` на macbook-i7 — указан реальный путь к смонтированной папке Яндекс.Диска
- Проверено: папки `Video/` и `Audio/` создаются автоматически при первом использовании
- Бот перезапущен после обновления .env
