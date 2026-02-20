import asyncio
import glob
import logging
import os
import re
import shutil
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.config import ALLOWED_USERS, DOWNLOAD_DIR, YANDEX_DISK_PATH, MAX_TELEGRAM_SIZE, LOCAL_API_URL
from bot.downloader import (
    get_video_info,
    download_video,
    download_audio,
    convert_to_mp3,
    compress_file,
    calculate_bitrate,
    _get_duration,
)

logger = logging.getLogger(__name__)

YOUTUBE_URL_RE = re.compile(
    r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[^\s]+'
)

# Telegram send limits depend on whether we use the Local Bot API Server
if LOCAL_API_URL:
    _SEND_LIMIT = 2000 * 1024 * 1024    # 2 GB with local server
    _TARGET_BYTES = 1999 * 1024 * 1024
else:
    _SEND_LIMIT = 50 * 1024 * 1024      # 50 MB with official API
    _TARGET_BYTES = 49 * 1024 * 1024


def _make_tg_progress(chat_id: int, message_id: int, bot, loop) -> callable:
    """Return a sync callback that schedules Telegram message edits on the event loop.

    The callback is called from a background thread (run_in_executor) so we use
    asyncio.run_coroutine_threadsafe to bridge into the async world.
    """
    last_text = {"v": ""}

    def callback(text: str) -> None:
        if text == last_text["v"]:
            return
        last_text["v"] = text
        future = asyncio.run_coroutine_threadsafe(
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text),
            loop,
        )
        try:
            future.result(timeout=10)
        except BadRequest:
            # "Message is not modified" — same text sent twice, harmless
            pass
        except Exception:
            # Network hiccup or rate-limit; skip this update, next one will come
            pass

    return callback


def _yandex_dest(file_path: str, file_type: str) -> str:
    """Return the Yandex.Disk destination path for a file."""
    subdir = "Video" if file_type == "video" else "Audio"
    dest_dir = os.path.join(YANDEX_DISK_PATH, subdir)
    os.makedirs(dest_dir, exist_ok=True)
    return os.path.join(dest_dir, os.path.basename(file_path))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я скачиваю видео и аудио с YouTube.\n\n"
        "Просто отправь мне ссылку на YouTube-видео, и я предложу варианты загрузки.\n\n"
        "Поддерживаются форматы:\n"
        "  - youtube.com/watch?v=...\n"
        "  - youtu.be/...\n"
        "  - youtube.com/shorts/...\n\n"
        "Используй /help для справки.\n"
        "Используй /cancel чтобы отменить текущую операцию."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Отправь ссылку на YouTube — я предложу скачать видео или аудио.\n\n"
        "Видео — выбираешь разрешение (360p–1080p)\n"
        "Аудио — оригинал (webm) или MP3 (96–320 kbps)\n\n"
        "Файлы до 2 GB отправляются в Telegram.\n"
        "Если больше — сохраняется на Яндекс.Диск, предлагается сжатие.\n\n"
        "/cancel — отменить операцию и удалить временные файлы."
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["cancelled"] = True

    # Remove every file in DOWNLOAD_DIR (all belong to this bot instance / user)
    removed = 0
    for path in glob.glob(os.path.join(DOWNLOAD_DIR, "*")):
        try:
            os.remove(path)
            removed += 1
        except Exception:
            pass

    context.user_data.pop("pending_file", None)
    context.user_data.pop("compress_attempt", None)
    context.user_data.pop("last_video_kbps", None)
    context.user_data.pop("last_audio_kbps", None)
    context.user_data.pop("file_type", None)

    await update.message.reply_text(
        "Все задачи отменены, временные файлы удалены."
    )


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await update.message.reply_text("У вас нет доступа.")
        return

    text = update.message.text or ""
    match = YOUTUBE_URL_RE.search(text)
    if not match:
        return

    url = match.group(0)
    if not url.startswith("http"):
        url = "https://" + url

    # Reset cancellation flag on each new URL
    context.user_data["cancelled"] = False
    context.user_data["url"] = url

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Видео", callback_data="format:video"),
            InlineKeyboardButton("Аудио", callback_data="format:audio"),
        ]
    ])
    await update.message.reply_text("Выбери формат:", reply_markup=keyboard)


async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await query.edit_message_text("У вас нет доступа.")
        return

    choice = query.data  # "format:video" or "format:audio"

    if choice == "format:audio":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Оригинал ⚡", callback_data="audio:original"),
            ],
            [
                InlineKeyboardButton("MP3 96", callback_data="audio:96"),
                InlineKeyboardButton("MP3 128", callback_data="audio:128"),
            ],
            [
                InlineKeyboardButton("MP3 192", callback_data="audio:192"),
                InlineKeyboardButton("MP3 320", callback_data="audio:320"),
            ]
        ])
        await query.edit_message_text(
            "Выбери формат аудио:\n"
            "Оригинал — webm/opus, без конвертации, быстрее всего\n"
            "MP3 — конвертация, число = битрейт (kbps)",
            reply_markup=keyboard,
        )
        return

    # format:video — fetch available resolutions
    url = context.user_data.get("url")
    if not url:
        await query.edit_message_text("URL не найден. Отправь ссылку заново.")
        return

    await query.edit_message_text("Получаю информацию о видео...")

    try:
        info = await get_video_info(url)
    except Exception as e:
        logger.error("get_video_info failed for %s: %s", url, e)
        await query.edit_message_text(f"Не удалось получить информацию: {e}")
        return

    formats = info.get("formats", [])
    if not formats:
        await query.edit_message_text("Не найдено доступных форматов.")
        return

    buttons = []
    for fmt in formats:
        height = fmt["height"]
        resolution = fmt["resolution"]
        buttons.append([
            InlineKeyboardButton(resolution, callback_data=f"res:{height}")
        ])

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("Выбери качество:", reply_markup=keyboard)


async def resolution_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await query.edit_message_text("У вас нет доступа.")
        return

    parts = query.data.split(":", 1)
    if len(parts) < 2:
        await query.edit_message_text("Некорректные данные кнопки.")
        return

    try:
        height = int(parts[1])
    except ValueError:
        await query.edit_message_text("Некорректные данные кнопки.")
        return

    url = context.user_data.get("url")
    if not url:
        await query.edit_message_text("URL не найден. Отправь ссылку заново.")
        return

    await query.edit_message_text("Скачиваю видео...")
    context.user_data["file_type"] = "video"

    loop = asyncio.get_event_loop()
    progress_cb = _make_tg_progress(
        chat_id=update.effective_chat.id,
        message_id=query.message.message_id,
        bot=context.bot,
        loop=loop,
    )

    try:
        file_path, title = await download_video(url, height, progress_callback=progress_cb)
    except Exception as e:
        logger.error("download_video failed for %s (height %d): %s", url, height, e)
        await query.edit_message_text(f"Не удалось скачать: {e}")
        return

    context.user_data["pending_file"] = file_path
    try:
        await _send_file(update, context, file_path, status_message_id=query.message.message_id)
    except Exception as e:
        logger.error("_send_file failed for %s: %s", file_path, e)
        await query.edit_message_text(f"Не удалось отправить файл: {e}")


async def _send_file(
    update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str, status_message_id: int = 0,
) -> None:
    """Send file to Telegram if ≤ send limit, otherwise save to Yandex.Disk and offer compression."""
    chat_id = update.effective_chat.id
    size = os.path.getsize(file_path)
    size_mb = size / (1024 * 1024)

    async def _update_status(text: str) -> None:
        if not status_message_id:
            return
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_message_id, text=text)
        except Exception:
            pass

    if size <= _SEND_LIMIT:
        await _update_status(f"Отправляю в Telegram ({size_mb:.1f} MB)...")
        try:
            if LOCAL_API_URL:
                await update.effective_chat.send_document(document=Path(file_path))
            else:
                with open(file_path, "rb") as f:
                    await update.effective_chat.send_document(
                        document=f,
                        filename=os.path.basename(file_path),
                    )
        except Exception:
            if os.path.exists(file_path):
                os.remove(file_path)
            context.user_data.pop("pending_file", None)
            raise

        # If we just sent a non-mp3 audio file, offer conversion
        ext = os.path.splitext(file_path)[1].lower()
        if context.user_data.get("file_type") == "audio" and ext != ".mp3":
            context.user_data["convert_source"] = file_path
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Да, в MP3", callback_data="convert:yes"),
                    InlineKeyboardButton("Нет", callback_data="convert:no"),
                ]
            ])
            await update.effective_chat.send_message(
                "Сконвертировать в MP3 без потери качества?",
                reply_markup=keyboard,
            )
        else:
            if os.path.exists(file_path):
                os.remove(file_path)
            context.user_data.pop("pending_file", None)
            await _update_status("Отправлено.")
        return

    # File is too large for Telegram — save original to Yandex.Disk
    await _update_status(f"Файл {size_mb:.1f} MB — сохраняю на Яндекс.Диск...")
    file_type = context.user_data.get("file_type", "video")
    dest_path = _yandex_dest(file_path, file_type)
    try:
        shutil.copy2(file_path, dest_path)
        logger.info("Saved to Yandex.Disk: %s", dest_path)
    except Exception as e:
        logger.error("Failed to copy to Yandex.Disk: %s", e)
        await update.effective_chat.send_message(
            f"Не удалось сохранить на Яндекс.Диск: {e}"
        )
        return

    # Reset compression state for this file
    context.user_data["compress_attempt"] = 1
    context.user_data.pop("last_video_kbps", None)
    context.user_data.pop("last_audio_kbps", None)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Да, сжать", callback_data="compress:yes"),
            InlineKeyboardButton("Нет, не надо", callback_data="compress:no"),
        ]
    ])
    await update.effective_chat.send_message(
        f"Файл {size_mb:.1f} MB. Оригинал сохранён в Яндекс.Диск.\n"
        "Сжать до 49 MB и отправить в Telegram?",
        reply_markup=keyboard,
    )


async def compress_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the iterative compression loop."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await query.edit_message_text("У вас нет доступа.")
        return

    choice = query.data  # "compress:yes" or "compress:no"

    if choice == "compress:no":
        file_path = context.user_data.pop("pending_file", None)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        await query.edit_message_text("Оригинал сохранён в Яндекс.Диск.")
        return

    # compress:yes
    if context.user_data.get("cancelled"):
        await query.edit_message_text("Операция отменена.")
        return

    file_path = context.user_data.get("pending_file")
    if not file_path or not os.path.exists(file_path):
        await query.edit_message_text("Файл не найден. Попробуй скачать заново.")
        return

    attempt = context.user_data.get("compress_attempt", 1)
    file_type = context.user_data.get("file_type", "video")
    is_audio = file_type == "audio"

    await query.edit_message_text(f"Сжимаю (попытка {attempt})...")

    # Determine bitrates
    try:
        duration = await _get_duration(file_path)
    except Exception as e:
        await query.edit_message_text(f"Не удалось определить длительность: {e}")
        return

    prev_video_kbps = context.user_data.get("last_video_kbps", 0)
    prev_audio_kbps = context.user_data.get("last_audio_kbps", 128)

    video_kbps, audio_kbps = calculate_bitrate(
        duration=duration,
        target_bytes=_TARGET_BYTES,
        is_audio=is_audio,
        attempt=attempt,
        prev_video_kbps=prev_video_kbps,
        prev_audio_kbps=prev_audio_kbps,
    )

    compressed_path = None
    try:
        compressed_path, result_size = await compress_file(file_path, video_kbps, audio_kbps)
    except Exception as e:
        logger.error("compress_file failed: %s", e)
        await query.edit_message_text(f"Ошибка сжатия: {e}")
        return

    # Check cancellation after the slow ffmpeg step
    if context.user_data.get("cancelled"):
        if compressed_path and os.path.exists(compressed_path):
            os.remove(compressed_path)
        await query.edit_message_text("Операция отменена.")
        return

    result_mb = result_size / (1024 * 1024)

    if result_size <= _TARGET_BYTES:
        # Success — send to Telegram
        try:
            if LOCAL_API_URL:
                await update.effective_chat.send_document(document=Path(compressed_path))
            else:
                with open(compressed_path, "rb") as f:
                    await update.effective_chat.send_document(
                        document=f,
                        filename=os.path.basename(file_path),
                )
            await query.edit_message_text("Сжато и отправлено в Telegram.")
        except Exception as e:
            logger.error("send compressed failed: %s", e)
            await query.edit_message_text(f"Не удалось отправить: {e}")
        finally:
            if compressed_path and os.path.exists(compressed_path):
                os.remove(compressed_path)
            orig = context.user_data.pop("pending_file", None)
            if orig and os.path.exists(orig):
                os.remove(orig)
        return

    # Still too large — clean up this attempt's file and ask again
    if compressed_path and os.path.exists(compressed_path):
        os.remove(compressed_path)

    # Save bitrates for next attempt
    context.user_data["last_video_kbps"] = video_kbps
    context.user_data["last_audio_kbps"] = audio_kbps
    context.user_data["compress_attempt"] = attempt + 1

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Да, ещё сжать", callback_data="compress:yes"),
            InlineKeyboardButton("Нет, хватит", callback_data="compress:no"),
        ]
    ])
    await query.edit_message_text(
        f"Сжатый файл {result_mb:.1f} MB — всё ещё большой. Попробовать агрессивнее?",
        reply_markup=keyboard,
    )


async def convert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle convert:yes / convert:no after sending a non-mp3 audio file."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await query.edit_message_text("У вас нет доступа.")
        return

    choice = query.data  # "convert:yes" or "convert:no"
    source = context.user_data.pop("convert_source", None)

    if choice == "convert:no":
        if source and os.path.exists(source):
            os.remove(source)
        context.user_data.pop("pending_file", None)
        await query.edit_message_text("Ок, оставляем как есть.")
        return

    # convert:yes
    if not source or not os.path.exists(source):
        await query.edit_message_text("Файл не найден. Скачай заново.")
        return

    await query.edit_message_text("Конвертирую в MP3...")

    loop = asyncio.get_event_loop()
    progress_cb = _make_tg_progress(
        chat_id=update.effective_chat.id,
        message_id=query.message.message_id,
        bot=context.bot,
        loop=loop,
    )

    try:
        mp3_path = await convert_to_mp3(source, progress_callback=progress_cb)
    except Exception as e:
        logger.error("convert_to_mp3 failed: %s", e)
        await query.edit_message_text(f"Ошибка конвертации: {e}")
        return
    finally:
        if source and os.path.exists(source):
            os.remove(source)
        context.user_data.pop("pending_file", None)

    mp3_mb = os.path.getsize(mp3_path) / (1024 * 1024)
    await query.edit_message_text(f"Отправляю MP3 ({mp3_mb:.1f} MB)...")

    try:
        if LOCAL_API_URL:
            await update.effective_chat.send_document(document=Path(mp3_path))
        else:
            with open(mp3_path, "rb") as f:
                await update.effective_chat.send_document(
                    document=f,
                    filename=os.path.basename(mp3_path),
                )
        await query.edit_message_text("Отправлено.")
    except Exception as e:
        logger.error("send mp3 failed: %s", e)
        await query.edit_message_text(f"Не удалось отправить: {e}")
    finally:
        if os.path.exists(mp3_path):
            os.remove(mp3_path)


async def audio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle audio bitrate selection."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await query.edit_message_text("У вас нет доступа.")
        return

    url = context.user_data.get("url")
    if not url:
        await query.edit_message_text("URL не найден. Отправь ссылку заново.")
        return

    bitrate = query.data.split(":")[1]

    if bitrate == "original":
        await query.edit_message_text("Скачиваю аудио (оригинал)...")
    else:
        await query.edit_message_text(f"Скачиваю аудио ({bitrate} kbps)...")
    context.user_data["file_type"] = "audio"

    loop = asyncio.get_event_loop()
    progress_cb = _make_tg_progress(
        chat_id=update.effective_chat.id,
        message_id=query.message.message_id,
        bot=context.bot,
        loop=loop,
    )

    try:
        file_path, title = await download_audio(url, bitrate, progress_callback=progress_cb)
    except Exception as e:
        logger.error("download_audio failed for %s: %s", url, e)
        await query.edit_message_text(f"Не удалось скачать: {e}")
        return

    context.user_data["pending_file"] = file_path
    try:
        await _send_file(update, context, file_path, status_message_id=query.message.message_id)
    except Exception as e:
        logger.error("_send_file failed for %s: %s", file_path, e)
        await query.edit_message_text(f"Не удалось отправить файл: {e}")
