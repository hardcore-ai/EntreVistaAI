"""Evaluations API — the HITL review queue.

Recruiters use this to review AI recommendations and make final decisions.
PRD Principle 1: "La IA recomienda, el humano decide."
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentOperator
from app.models import (
    Evaluation, EvaluationStatus, ScreeningSession, Campaign, AuditLog,
)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


class HumanDecisionRequest(BaseModel):
    decision: str           # "approved" | "rejected"
    notes: str | None = None


class CompetencyScoreOut(BaseModel):
    competency: str
    score: float
    weight: float
    rationale: str
    quotes: list[str]


class EvaluationOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    overall_score: float | None
    ai_recommendation: str | None
    summary: str
    strengths: list[str]
    concerns: list[str]
    competency_scores: list[dict]
    status: EvaluationStatus
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    human_decision: str | None
    human_notes: str | None
    human_disagrees: bool
    created_at: datetime
    # Candidate info
    candidate_name: str | None = None
    session_status: str | None = None
    campaign_title: str | None = None
    conversation_history: list[dict] = []

    model_config = {"from_attributes": True}


@router.get("", response_model=list[EvaluationOut])
async def list_evaluations(
    db: DB,
    current: CurrentOperator,
    status: str | None = None,
    campaign_id: uuid.UUID | None = None,
):
    """List evaluations for the current operator's company — the HITL review queue."""
    query = (
        select(Evaluation)
        .join(ScreeningSession, Evaluation.session_id == ScreeningSession.id)
        .join(Campaign, ScreeningSession.campaign_id == Campaign.id)
        .where(Campaign.company_id == current.company_id)
        .options(
            selectinload(Evaluation.session).selectinload(ScreeningSession.candidate),
            selectinload(Evaluation.session).selectinload(ScreeningSession.campaign),
        )
        .order_by(Evaluation.created_at.desc())
    )

    if status:
        query = query.where(Evaluation.status == EvaluationStatus(status))
    if campaign_id:
        query = query.where(ScreeningSession.campaign_id == campaign_id)

    result = await db.execute(query)
    evaluations = result.scalars().all()
    return [_enrich(e) for e in evaluations]


@router.get("/{evaluation_id}", response_model=EvaluationOut)
async def get_evaluation(evaluation_id: uuid.UUID, db: DB, current: CurrentOperator):
    evaluation = await _get_evaluation_or_404(db, evaluation_id, current.company_id)
    return _enrich(evaluation)


@router.post("/{evaluation_id}/decide", response_model=EvaluationOut)
async def human_decision(
    evaluation_id: uuid.UUID,
    payload: HumanDecisionRequest,
    db: DB,
    current: CurrentOperator,
):
    """Record human recruiter's decision — HITL action."""
    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="La decisión debe ser 'approved' o 'rejected'.")

    evaluation = await _get_evaluation_or_404(db, evaluation_id, current.company_id)

    if evaluation.status not in (EvaluationStatus.PENDING, EvaluationStatus.ESCALATED):
        raise HTTPException(status_code=400, detail="Esta evaluación ya fue revisada.")

    evaluation.status = EvaluationStatus.APPROVED if payload.decision == "approved" else EvaluationStatus.REJECTED
    evaluation.human_decision = payload.decision
    evaluation.human_notes = payload.notes
    evaluation.reviewed_by = current.id
    evaluation.reviewed_at = datetime.utcnow()

    # Track disagreement for calibration
    ai_rec = evaluation.ai_recommendation or ""
    ai_positive = ai_rec in ("highly_recommended", "recommended")
    human_positive = payload.decision == "approved"
    evaluation.human_disagrees = ai_positive != human_positive

    # Audit
    db.add(AuditLog(
        session_id=evaluation.session_id,
        operator_id=current.id,
        event_type="human_decision",
        payload={
            "decision": payload.decision,
            "ai_recommendation": evaluation.ai_recommendation,
            "disagrees": evaluation.human_disagrees,
            "notes": payload.notes,
        },
    ))

    await db.commit()
    await db.refresh(evaluation)
    return _enrich(evaluation)


# ─── helpers ──────────────────────────────────────────────────────────────────

async def _get_evaluation_or_404(db: DB, evaluation_id: uuid.UUID, company_id: uuid.UUID) -> Evaluation:
    result = await db.execute(
        select(Evaluation)
        .join(ScreeningSession, Evaluation.session_id == ScreeningSession.id)
        .join(Campaign, ScreeningSession.campaign_id == Campaign.id)
        .where(Evaluation.id == evaluation_id, Campaign.company_id == company_id)
        .options(
            selectinload(Evaluation.session).selectinload(ScreeningSession.candidate),
            selectinload(Evaluation.session).selectinload(ScreeningSession.campaign),
        )
    )
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada.")
    return evaluation


def _enrich(evaluation: Evaluation) -> EvaluationOut:
    data = EvaluationOut.model_validate(evaluation)
    if evaluation.session:
        data.candidate_name = evaluation.session.candidate_name
        data.session_status = evaluation.session.status.value if evaluation.session.status else None
        data.conversation_history = evaluation.session.conversation_history or []
        if evaluation.session.campaign:
            data.campaign_title = evaluation.session.campaign.title
    return data
