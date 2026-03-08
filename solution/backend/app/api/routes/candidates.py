"""Candidates API — candidate profiles and session history."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentOperator
from app.models import ScreeningSession, Campaign, Candidate, SessionStatus

router = APIRouter(prefix="/candidates", tags=["candidates"])


class SessionOut(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    campaign_title: str | None = None
    status: str
    candidate_name: str | None
    started_at: datetime
    completed_at: datetime | None
    current_question_index: int
    has_evaluation: bool = False
    overall_score: float | None = None
    ai_recommendation: str | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[SessionOut])
async def list_candidates(
    db: DB,
    current: CurrentOperator,
    campaign_id: uuid.UUID | None = None,
    status: str | None = None,
):
    """List sessions (one row per interview attempt) for the company."""
    query = (
        select(ScreeningSession)
        .join(Campaign, ScreeningSession.campaign_id == Campaign.id)
        .where(Campaign.company_id == current.company_id)
        .options(
            selectinload(ScreeningSession.candidate),
            selectinload(ScreeningSession.campaign),
            selectinload(ScreeningSession.evaluation),
        )
        .order_by(ScreeningSession.started_at.desc())
    )

    if campaign_id:
        query = query.where(ScreeningSession.campaign_id == campaign_id)
    if status:
        query = query.where(ScreeningSession.status == SessionStatus(status))

    result = await db.execute(query)
    sessions = result.scalars().all()
    return [_session_out(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionOut)
async def get_candidate_session(session_id: uuid.UUID, db: DB, current: CurrentOperator):
    session = await _get_session_or_404(db, session_id, current.company_id)
    return _session_out(session)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _session_out(session: ScreeningSession) -> SessionOut:
    campaign_title = session.campaign.title if session.campaign else None
    has_eval = session.evaluation is not None
    score = session.evaluation.overall_score if has_eval else None
    rec = session.evaluation.ai_recommendation if has_eval else None

    return SessionOut(
        id=session.id,
        campaign_id=session.campaign_id,
        campaign_title=campaign_title,
        status=session.status.value,
        candidate_name=session.candidate_name,
        started_at=session.started_at,
        completed_at=session.completed_at,
        current_question_index=session.current_question_index,
        has_evaluation=has_eval,
        overall_score=score,
        ai_recommendation=rec,
    )


async def _get_session_or_404(db: DB, session_id: uuid.UUID, company_id: uuid.UUID) -> ScreeningSession:
    result = await db.execute(
        select(ScreeningSession)
        .join(Campaign, ScreeningSession.campaign_id == Campaign.id)
        .where(ScreeningSession.id == session_id, Campaign.company_id == company_id)
        .options(
            selectinload(ScreeningSession.candidate),
            selectinload(ScreeningSession.campaign),
            selectinload(ScreeningSession.evaluation),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Candidato no encontrado.")
    return session
