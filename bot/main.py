import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.config import BOT_TOKEN, LOCAL_API_URL
from bot.handlers import (
    start_command,
    help_command,
    handle_url,
    format_callback,
    resolution_callback,
    compress_callback,
    audio_callback,
    cancel_command,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    builder = Application.builder().token(BOT_TOKEN)

    if LOCAL_API_URL:
        builder = (
            builder
            .base_url(f"{LOCAL_API_URL}/bot")
            .base_file_url(f"{LOCAL_API_URL}/file/bot")
            .local_mode(True)
        )
        logger.info("Using Local Bot API Server at %s", LOCAL_API_URL)

    application = builder.build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(format_callback, pattern="^format:"))
    application.add_handler(CallbackQueryHandler(resolution_callback, pattern="^res:"))
    application.add_handler(CallbackQueryHandler(audio_callback, pattern="^audio:"))
    application.add_handler(CallbackQueryHandler(compress_callback, pattern="^compress:"))

    logger.info("Bot started")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
