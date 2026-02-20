# Деплой

## Сервер
- Хост: `macbook-i7` (ssh macbook-i7)
- Путь: `/Users/andrewmaier/youtubeDownloaderBot`

## Управление через manage-bots.sh

```bash
ssh macbook-i7 "~/manage-bots.sh status"            # статус всех ботов
ssh macbook-i7 "~/manage-bots.sh start youtube"      # запустить
ssh macbook-i7 "~/manage-bots.sh stop youtube"       # остановить
ssh macbook-i7 "~/manage-bots.sh restart youtube"    # перезапустить
ssh macbook-i7 "~/manage-bots.sh restart all"        # перезапустить все
```

## Ручной запуск

```bash
ssh macbook-i7
cd /Users/andrewmaier/youtubeDownloaderBot
nohup venv/bin/python -m bot.main >> bot.log 2>&1 < /dev/null &
echo $! > .bot.pid
```

## Логи

```bash
ssh macbook-i7 "tail -50 /Users/andrewmaier/youtubeDownloaderBot/bot.log"
```

## Важно
- На macbook-i7 также работает локальный Telegram Bot API Server на порту 8081
- Никогда не использовать `pkill -f 'python.*bot.main'` — убьёт ВСЕ боты
- Всегда останавливать через manage-bots.sh или по PID из `.bot.pid`
