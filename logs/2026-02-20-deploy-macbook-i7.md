# Deploy Log: macbook-i7 (2026-02-20)

Target machine: macbook-i7 (old Mac, Intel x86_64)
Python: /usr/local/bin/python3.12 (3.12.12)
Repo: https://github.com/Dronnn/youtubeDownloaderBot.git

---

## Step 1: Check existing bots

Existing processes (must not be touched):
- PID 2019: uvicorn app.main:app (daycast-api, port 8000, 2 workers — PIDs 2022/2023/2024)
- PID 78786: .venv/bin/python -m bot.main (bot, started ~1:55PM)
- PID 76963: .venv/bin/python -m bot.main (bot, started ~12:43PM)
- PID 63544: fortune-teller-telegram-bot (Go binary)
- PID 63539: python -m bot.main (another bot, started ~10:39PM)
- PID 79452: postgres idle (vocab_traibot)

STATUS: DONE

---

## Step 2: Install ffmpeg static binary

- /usr/local/bin is writable by andrewmaier — no sudo needed
- Downloaded ffmpeg 8.0.1-tessus from evermeet.cx (25 MB zip)
- Installed to /usr/local/bin/ffmpeg, chmod +x
- Verified: `ffmpeg version 8.0.1-tessus https://evermeet.cx/ffmpeg/`
- Note: `ffmpeg` not in PATH of non-interactive SSH sessions, but /usr/local/bin/ffmpeg works

STATUS: DONE

---

## Step 3: Clone repo

- Repo did not exist — fresh clone
- `git clone https://github.com/Dronnn/youtubeDownloaderBot.git`
- Contents: README.md, bot/, docs/, logs/, requirements.txt

STATUS: DONE

---

## Step 4: Create venv with Python 3.12

- `/usr/local/bin/python3.12 -m venv venv`
- Verified: `venv/bin/python --version` → Python 3.12.12

STATUS: DONE

---

## Step 5: Install dependencies

Installed:
- python-telegram-bot 22.6
- yt-dlp 2026.2.4
- python-dotenv 1.2.1
- httpx 0.28.1, httpcore 1.0.9, h11 0.16.0
- aiolimiter 1.2.1, apscheduler 3.11.2, cachetools 6.2.6, tornado 6.5.4
- anyio 4.12.1, certifi, idna, typing_extensions, tzlocal

STATUS: DONE

---

## Step 6: Create .env file and directories

- .env written to ~/youtubeDownloaderBot/.env
  - BOT_NAME=mrYTDownloaderBot
  - BOT_TOKEN=8180875918:AAFF...
  - ALLOWED_USERS=58502902
  - YANDEX_DISK_PATH=/tmp/yt_yandex (temp)
  - DOWNLOAD_DIR=/tmp/yt_downloads
  - MAX_TELEGRAM_SIZE=52428800
- Created /tmp/yt_downloads and /tmp/yt_yandex

STATUS: DONE

---

## Step 7: Test run (config import check)

- `from bot.config import BOT_TOKEN` — OK
- Output: `Config OK, token starts with: 8180875918...`

STATUS: DONE

---

## Step 8: Start bot in background

- `nohup venv/bin/python -m bot.main > ~/youtubeDownloaderBot/bot.log 2>&1 &`
- Bot started as PID 79737

STATUS: DONE

---

## Step 9: Verify bot running + check log

- PID 79737: Python -m bot.main — running
- bot.log output:
  ```
  2026-02-20 14:51:11,933 - __main__ - INFO - Bot started
  2026-02-20 14:51:15,232 - httpx - INFO - POST getMe "HTTP/1.1 200 OK"
  2026-02-20 14:51:15,302 - httpx - INFO - POST deleteWebhook "HTTP/1.1 200 OK"
  2026-02-20 14:51:15,304 - apscheduler.scheduler - INFO - Scheduler started
  2026-02-20 14:51:15,305 - telegram.ext.Application - INFO - Application started
  ```

STATUS: DONE

---

## Step 10: Verify other bots still running

All original processes confirmed still running:
- PID 2019: uvicorn daycast-api (+ workers 2022/2023/2024)
- PID 78786: .venv/bin/python -m bot.main
- PID 76963: .venv/bin/python -m bot.main
- PID 63544: fortune-teller-telegram-bot (Go binary)
- PID 63539: python -m bot.main
- PID 79452: postgres vocab_traibot idle

New bot PID 79737 added without disturbing any existing process.

STATUS: DONE

---

## Summary

Deployment complete. Bot mrYTDownloaderBot is running on macbook-i7 as PID 79737.
Log: ~/youtubeDownloaderBot/bot.log
Temp note: YANDEX_DISK_PATH=/tmp/yt_yandex — needs updating once Yandex Disk is configured.

