import os
import re
import shutil
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import ALLOWED_USERS, YANDEX_DISK_PATH, MAX_TELEGRAM_SIZE
from bot.downloader import get_video_info, download_video, download_audio, compress_to_fit

logger = logging.getLogger(__name__)

YOUTUBE_URL_RE = re.compile(
    r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[^\s]+'
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я скачиваю видео и аудио с YouTube.\n\n"
        "Просто отправь мне ссылку на YouTube-видео, и я предложу варианты загрузки.\n\n"
        "Поддерживаются форматы:\n"
        "  - youtube.com/watch?v=...\n"
        "  - youtu.be/...\n"
        "  - youtube.com/shorts/...\n\n"
        "Используй /help для справки."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Отправь ссылку на YouTube — я предложу скачать видео или только аудио.\n\n"
        "Если файл слишком большой для Telegram, он будет сохранён на Яндекс.Диск."
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
        await _download_and_send_audio(update, context)
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

    # callback_data = "res:{height}"
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

    try:
        file_path, title = await download_video(url, height)
    except Exception as e:
        logger.error("download_video failed for %s (height %d): %s", url, height, e)
        await query.edit_message_text(f"Не удалось скачать: {e}")
        return

    context.user_data["pending_file"] = file_path
    try:
        await _send_file(update, context, file_path)
    except Exception as e:
        logger.error("_send_file failed for %s: %s", file_path, e)
        await query.edit_message_text(f"Не удалось отправить файл: {e}")


async def _send_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str) -> None:
    """Send the file via Telegram if small enough, otherwise ask user what to do."""
    size = os.path.getsize(file_path)

    if size <= MAX_TELEGRAM_SIZE:
        try:
            with open(file_path, "rb") as f:
                await update.effective_chat.send_document(
                    document=f,
                    filename=os.path.basename(file_path),
                )
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
            context.user_data.pop("pending_file", None)
        return

    # File too large — ask user
    size_mb = size / (1024 * 1024)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Сжать и отправить", callback_data="toobig:compress"),
            InlineKeyboardButton("Сохранить в Яндекс.Диск", callback_data="toobig:yandex"),
        ]
    ])
    await update.effective_chat.send_message(
        f"Файл {size_mb:.1f} MB — слишком большой для Telegram (лимит {MAX_TELEGRAM_SIZE // 1024 // 1024} MB).\n"
        "Что сделать?",
        reply_markup=keyboard,
    )


async def toobig_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user choice for oversized files."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await query.edit_message_text("У вас нет доступа.")
        return

    file_path = context.user_data.get("pending_file")
    if not file_path or not os.path.exists(file_path):
        await query.edit_message_text("Файл не найден. Попробуй скачать заново.")
        return

    choice = query.data  # "toobig:compress" or "toobig:yandex"

    if choice == "toobig:yandex":
        os.makedirs(YANDEX_DISK_PATH, exist_ok=True)
        dest_path = os.path.join(YANDEX_DISK_PATH, os.path.basename(file_path))
        shutil.copy2(file_path, dest_path)
        os.remove(file_path)
        context.user_data.pop("pending_file", None)
        await query.edit_message_text(f"Сохранён в Яндекс.Диск:\n{dest_path}")
        return

    # toobig:compress
    await query.edit_message_text("Сжимаю...")
    compressed_path = None
    try:
        compressed_path = await compress_to_fit(file_path)
        with open(compressed_path, "rb") as f:
            await update.effective_chat.send_document(
                document=f,
                filename=os.path.basename(file_path),
            )
        await query.edit_message_text("Сжато и отправлено.")
    except Exception as e:
        logger.error("Compression/send failed: %s", e)
        # Fallback to Yandex.Disk
        os.makedirs(YANDEX_DISK_PATH, exist_ok=True)
        dest_path = os.path.join(YANDEX_DISK_PATH, os.path.basename(file_path))
        if os.path.exists(file_path):
            shutil.copy2(file_path, dest_path)
        await query.edit_message_text(
            f"Не удалось сжать. Сохранён в Яндекс.Диск:\n{dest_path}"
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if compressed_path and compressed_path != file_path and os.path.exists(compressed_path):
            os.remove(compressed_path)
        context.user_data.pop("pending_file", None)


async def _download_and_send_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    url = context.user_data.get("url")
    if not url:
        await query.edit_message_text("URL не найден. Отправь ссылку заново.")
        return

    await query.edit_message_text("Скачиваю аудио...")

    try:
        file_path, title = await download_audio(url)
    except Exception as e:
        logger.error("download_audio failed for %s: %s", url, e)
        await query.edit_message_text(f"Не удалось скачать: {e}")
        return

    context.user_data["pending_file"] = file_path
    try:
        await _send_file(update, context, file_path)
    except Exception as e:
        logger.error("_send_file failed for %s: %s", file_path, e)
        await query.edit_message_text(f"Не удалось отправить файл: {e}")
