"""SessionService — manages the lifecycle of a screening session.

Coordinates between:
  - The InterviewerAgent (generates responses)
  - The database (persists state)
  - The AuditLog (immutable event record)
  - The EvaluatorAgent (triggered on completion)
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.interviewer import InterviewerAgent
from app.agents.evaluator import generate_evaluation
from app.models import (
    ScreeningSession, SessionStatus, Campaign, Candidate,
    Evaluation, EvaluationStatus, NPSFeedback, AuditLog,
)

logger = logging.getLogger(__name__)

agent = InterviewerAgent()


async def get_or_create_candidate(
    db: AsyncSession,
    telegram_user_id: int,
    name: str | None = None,
    username: str | None = None,
) -> Candidate:
    result = await db.execute(
        select(Candidate).where(Candidate.telegram_user_id == telegram_user_id)
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        candidate = Candidate(
            telegram_user_id=telegram_user_id,
            name=name,
            username=username,
        )
        db.add(candidate)
        await db.flush()

    return candidate


async def get_campaign_by_token(db: AsyncSession, token: str) -> Campaign | None:
    result = await db.execute(
        select(Campaign)
        .where(Campaign.telegram_link_token == token, Campaign.is_active == True)
        .options(selectinload(Campaign.rubric), selectinload(Campaign.company))
    )
    return result.scalar_one_or_none()


async def get_active_session(db: AsyncSession, candidate_id: uuid.UUID, campaign_id: uuid.UUID) -> ScreeningSession | None:
    result = await db.execute(
        select(ScreeningSession)
        .where(
            ScreeningSession.candidate_id == candidate_id,
            ScreeningSession.campaign_id == campaign_id,
            ScreeningSession.status.notin_([
                SessionStatus.COMPLETED,
                SessionStatus.ABANDONED,
            ]),
        )
        .order_by(ScreeningSession.started_at.desc())
    )
    return result.scalar_one_or_none()


async def create_session(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> ScreeningSession:
    session = ScreeningSession(
        candidate_id=candidate_id,
        campaign_id=campaign_id,
        status=SessionStatus.INITIATED,
        conversation_history=[],
    )
    db.add(session)
    await db.flush()
    await _audit(db, session.id, "session_created", {"campaign_id": str(campaign_id)})
    return session


async def process_message(
    db: AsyncSession,
    session: ScreeningSession,
    campaign: Campaign,
    user_message: str,
) -> str:
    """Process one candidate message, persist state, and return the reply text."""

    # Build campaign context dict for the agent
    campaign_data = _build_campaign_data(campaign)

    # Call the agent
    agent_response = await agent.process_message(
        user_message=user_message,
        session_state=session.status.value,
        conversation_history=session.conversation_history,
        campaign_data=campaign_data,
        current_question_index=session.current_question_index,
        followup_count=session.followup_count,
        candidate_name=session.candidate_name,
    )

    # Update conversation history
    updated_history = session.conversation_history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": agent_response.message},
    ]
    session.conversation_history = updated_history
    session.last_activity_at = datetime.utcnow()

    # Apply metadata from agent response
    meta = agent_response.metadata
    if "candidate_name" in meta:
        session.candidate_name = meta["candidate_name"]
        # Also update Candidate record
        if session.candidate:
            session.candidate.name = meta["candidate_name"]
    if "current_question_index" in meta:
        session.current_question_index = meta["current_question_index"]
    if "followup_count" in meta:
        session.followup_count = meta["followup_count"]

    # Transition state
    old_state = session.status.value
    new_state = agent_response.new_state
    _transition_state(session, new_state)

    # Audit the exchange
    await _audit(db, session.id, "message_exchange", {
        "user_message": user_message[:500],
        "agent_message": agent_response.message[:500],
        "old_state": old_state,
        "new_state": new_state,
    })

    # Handle NPS data captured in closing
    if "nps_score" in meta and new_state == "feedback":
        await _save_nps(db, session.id, meta["nps_score"], None)

    if "feedback_text" in meta and new_state == "completed":
        # Update existing NPS with open feedback
        result = await db.execute(
            select(NPSFeedback).where(NPSFeedback.session_id == session.id)
        )
        nps = result.scalar_one_or_none()
        if nps and meta.get("feedback_text"):
            nps.feedback_text = meta["feedback_text"]

    # If escalation triggered, log it
    if agent_response.should_escalate:
        session.escalations = (session.escalations or []) + [{
            "reason": meta.get("escalation_reason"),
            "at": datetime.utcnow().isoformat(),
            "question_index": session.current_question_index,
        }]
        await _audit(db, session.id, "escalation", {"reason": meta.get("escalation_reason")})

    # If session completed, run evaluator
    if new_state == "completed":
        session.completed_at = datetime.utcnow()
        await db.flush()
        await _run_evaluator(db, session, campaign_data)

    await db.commit()
    return agent_response.message


def _transition_state(session: ScreeningSession, new_state: str) -> None:
    valid_states = {s.value for s in SessionStatus}
    if new_state in valid_states:
        session.status = SessionStatus(new_state)


def _build_campaign_data(campaign: Campaign) -> dict:
    competencies = []
    if campaign.rubric:
        competencies = campaign.rubric.competencies or []

    return {
        "id": str(campaign.id),
        "title": campaign.title,
        "company_name": campaign.company.name if campaign.company else "la empresa",
        "role_description": campaign.role_description or "",
        "requirements": campaign.requirements or [],
        "knowledge_base": campaign.knowledge_base or "",
        "competencies": competencies,
        "retention_days": campaign.retention_days or 90,
    }


async def _run_evaluator(
    db: AsyncSession,
    session: ScreeningSession,
    campaign_data: dict,
) -> None:
    try:
        result = await generate_evaluation(
            conversation_history=session.conversation_history,
            campaign_data=campaign_data,
        )
        evaluation = Evaluation(
            session_id=session.id,
            overall_score=result.overall_score,
            ai_recommendation=result.ai_recommendation,
            summary=result.summary,
            strengths=result.strengths,
            concerns=result.concerns,
            competency_scores=result.competency_scores,
            status=EvaluationStatus.PENDING,
        )
        db.add(evaluation)
        await _audit(db, session.id, "evaluation_created", {
            "overall_score": result.overall_score,
            "recommendation": result.ai_recommendation,
        })
        logger.info("Evaluation created for session %s", session.id)
    except Exception as exc:
        logger.error("Evaluator failed for session %s: %s", session.id, exc)
        await _audit(db, session.id, "evaluation_error", {"error": str(exc)})


async def _save_nps(
    db: AsyncSession,
    session_id: uuid.UUID,
    score: int,
    feedback_text: str | None,
) -> None:
    nps = NPSFeedback(session_id=session_id, score=score, feedback_text=feedback_text)
    db.add(nps)


async def _audit(
    db: AsyncSession,
    session_id: uuid.UUID | None,
    event_type: str,
    payload: dict,
) -> None:
    log = AuditLog(
        session_id=session_id,
        event_type=event_type,
        payload=payload,
        timestamp=datetime.utcnow(),
    )
    db.add(log)
