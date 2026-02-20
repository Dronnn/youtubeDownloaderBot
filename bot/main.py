import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.config import BOT_TOKEN
from bot.handlers import start_command, help_command, handle_url, format_callback, resolution_callback

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(format_callback, pattern="^format:"))
    application.add_handler(CallbackQueryHandler(resolution_callback, pattern="^res:"))

    logger.info("Bot started")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
