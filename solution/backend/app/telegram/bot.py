"""Telegram bot setup — supports both webhook and polling modes."""

import logging

from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.config import settings
from app.telegram.handlers import handle_start, handle_message

logger = logging.getLogger(__name__)


def build_application() -> Application:
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app


async def send_message(telegram_user_id: int, text: str) -> None:
    """Utility used by the re-engagement scheduler to push messages."""
    bot = Bot(token=settings.telegram_bot_token)
    await bot.send_message(chat_id=telegram_user_id, text=text, parse_mode="Markdown")


async def set_webhook(app: Application) -> None:
    if not settings.telegram_webhook_url:
        logger.warning("TELEGRAM_WEBHOOK_URL not set — skipping webhook registration.")
        return

    await app.bot.set_webhook(
        url=f"{settings.telegram_webhook_url}/telegram/webhook",
        secret_token=settings.telegram_webhook_secret,
    )
    logger.info("Telegram webhook registered at %s", settings.telegram_webhook_url)
