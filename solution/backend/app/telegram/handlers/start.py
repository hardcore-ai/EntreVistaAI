"""Handler for the /start command.

When a candidate clicks a deep-link like t.me/EntrevistaBot?start=CAMPAIGN_TOKEN,
Telegram fires /start CAMPAIGN_TOKEN. We capture the token and kick off the interview.
"""

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

GENERIC_START_MESSAGE = """¡Hola! Soy EntreVista AI 🤖

Soy un asistente de inteligencia artificial para entrevistas de preselección.

Para iniciar una entrevista, necesitas usar el enlace específico de la vacante que te compartió el reclutador.

Si tienes preguntas, contacta directamente a la empresa."""


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user

    # Extract deep-link token from /start payload
    args = context.args or []
    campaign_token = args[0] if args else None

    if not campaign_token:
        await update.message.reply_text(GENERIC_START_MESSAGE, parse_mode=ParseMode.MARKDOWN)
        return

    # Store token in user_data for subsequent messages
    context.user_data["campaign_token"] = campaign_token

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
                "Lo sentimos, esta vacante ya no está disponible o el enlace no es válido."
            )
            return

        # Check for existing active session (re-engagement resume)
        session = await get_active_session(db, candidate.id, campaign.id)
        is_resuming = session is not None

        if not session:
            session = await create_session(db, candidate.id, campaign.id)

        # Send the initial message (consent screen for new sessions, resume message for existing)
        if is_resuming:
            name = session.candidate_name or tg_user.first_name or "candidato"
            resume_msg = (
                f"¡Hola de nuevo, {name}! 👋 Tu entrevista para *{campaign.title}* sigue activa.\n\n"
                "Continuemos desde donde lo dejamos. ¿Estás listo/a?"
            )
            await update.message.reply_text(resume_msg, parse_mode=ParseMode.MARKDOWN)
        else:
            # Trigger the agent for the first time (will return consent message)
            reply = await process_message(db, session, campaign, "/start")
            await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
