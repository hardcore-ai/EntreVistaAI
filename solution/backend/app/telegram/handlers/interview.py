"""Telegram message handler — routes every incoming message to the session service."""

import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.database import AsyncSessionLocal
from app.services import (
    get_or_create_candidate,
    get_campaign_by_token,
    get_active_session,
    create_session,
    process_message,
)

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main message handler — called for every text message from a candidate."""
    if not update.message or not update.message.text:
        return

    tg_user = update.effective_user
    user_message = update.message.text.strip()

    # Extract campaign token from bot_data (set during /start) or user_data
    campaign_token = context.user_data.get("campaign_token")
    if not campaign_token:
        await update.message.reply_text(
            "Para iniciar una entrevista, usa el enlace específico de la vacante que te compartieron.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    async with AsyncSessionLocal() as db:
        # Resolve or create candidate
        candidate = await get_or_create_candidate(
            db,
            telegram_user_id=tg_user.id,
            name=tg_user.full_name,
            username=tg_user.username,
        )

        # Resolve campaign
        campaign = await get_campaign_by_token(db, campaign_token)
        if not campaign:
            await update.message.reply_text(
                "Lo sentimos, esta vacante ya no está disponible o el enlace expiró."
            )
            return

        if campaign.status != "active":
            await update.message.reply_text(
                "Esta campaña está pausada. Por favor intenta más tarde."
            )
            return

        # Get or create session
        session = await get_active_session(db, candidate.id, campaign.id)
        if not session:
            session = await create_session(db, candidate.id, campaign.id)

        # Process through the agent
        try:
            reply = await process_message(db, session, campaign, user_message)
        except Exception as exc:
            logger.error("Error processing message for session %s: %s", session.id, exc)
            reply = "Ocurrió un error técnico. Por favor intenta de nuevo en unos momentos."

    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
