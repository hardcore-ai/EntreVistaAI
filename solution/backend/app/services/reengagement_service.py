"""Re-engagement service — sends follow-up messages to candidates who went silent.

Scheduled jobs check for inactive sessions and send up to 3 reminders:
  24h → first nudge
  48h → second nudge
  72h → final reminder, then mark as abandoned
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import ScreeningSession, SessionStatus, AuditLog
from app.agents.prompts import REENGAGEMENT_24H, REENGAGEMENT_48H, REENGAGEMENT_FINAL

logger = logging.getLogger(__name__)


async def process_reengagement(db: AsyncSession, send_telegram_message_fn) -> None:
    """Find stale sessions and send re-engagement messages.

    `send_telegram_message_fn(telegram_user_id, text)` — injected to avoid
    circular imports with the Telegram bot module.
    """
    now = datetime.utcnow()
    first_threshold = now - timedelta(hours=settings.reengagement_first_hours)
    second_threshold = now - timedelta(hours=settings.reengagement_second_hours)
    final_threshold = now - timedelta(hours=settings.reengagement_final_hours)

    active_statuses = [
        SessionStatus.CONSENT,
        SessionStatus.REQUIREMENTS,
        SessionStatus.SCREENING,
        SessionStatus.CLOSING,
        SessionStatus.FEEDBACK,
    ]

    result = await db.execute(
        select(ScreeningSession)
        .where(ScreeningSession.status.in_(active_statuses))
        .options(
            selectinload(ScreeningSession.candidate),
            selectinload(ScreeningSession.campaign).selectinload("company"),
        )
    )
    sessions = result.scalars().all()

    for session in sessions:
        last_activity = session.last_activity_at
        candidate = session.candidate
        if not candidate:
            continue

        telegram_id = candidate.telegram_user_id
        name = session.candidate_name or "candidato"
        job_title = session.campaign.title if session.campaign else "el puesto"

        try:
            if not session.reengagement_sent_72h and last_activity <= final_threshold:
                await send_telegram_message_fn(
                    telegram_id,
                    REENGAGEMENT_FINAL.format(name=name, job_title=job_title),
                )
                session.reengagement_sent_72h = True
                session.status = SessionStatus.ABANDONED
                session.last_activity_at = datetime.utcnow()
                await _audit(db, session.id, "reengagement_sent", {"type": "72h_final_abandoned"})

            elif not session.reengagement_sent_48h and last_activity <= second_threshold:
                await send_telegram_message_fn(
                    telegram_id,
                    REENGAGEMENT_48H.format(name=name, job_title=job_title),
                )
                session.reengagement_sent_48h = True
                await _audit(db, session.id, "reengagement_sent", {"type": "48h"})

            elif not session.reengagement_sent_24h and last_activity <= first_threshold:
                await send_telegram_message_fn(
                    telegram_id,
                    REENGAGEMENT_24H.format(name=name, job_title=job_title),
                )
                session.reengagement_sent_24h = True
                await _audit(db, session.id, "reengagement_sent", {"type": "24h"})

        except Exception as exc:
            logger.error("Re-engagement failed for session %s: %s", session.id, exc)

    await db.commit()


async def _audit(db: AsyncSession, session_id, event_type: str, payload: dict) -> None:
    db.add(AuditLog(session_id=session_id, event_type=event_type, payload=payload))
