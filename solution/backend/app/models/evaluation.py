import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON, Enum, Text, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class EvaluationStatus(str, enum.Enum):
    PENDING = "pending_review"    # Waiting for human review
    APPROVED = "approved"         # Human approved the candidate
    REJECTED = "rejected"         # Human rejected the candidate
    ESCALATED = "escalated"       # Needs more human attention


class Evaluation(Base):
    """Structured output of the AI evaluator after a screening session is complete.

    Every score MUST have evidence_quotes — "every score has a citation" (PRD Principle 3).
    Human review is mandatory before any decision (HITL — Principle 1).
    """
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("screening_sessions.id"), unique=True)

    # Overall score (0-100)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Per-competency scores: [{"competency": str, "score": 1-5, "weight": float, "quotes": [str], "rationale": str}]
    competency_scores: Mapped[list] = mapped_column(JSON, default=list)

    # Structured executive summary
    summary: Mapped[str] = mapped_column(Text, default="")
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    concerns: Mapped[list] = mapped_column(JSON, default=list)

    # AI recommendation: "highly_recommended" | "recommended" | "needs_review" | "not_recommended"
    ai_recommendation: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ─── HITL ───────────────────────────────────────────────────────────────
    status: Mapped[EvaluationStatus] = mapped_column(Enum(EvaluationStatus), default=EvaluationStatus.PENDING)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("operators.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    human_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)  # approved | rejected
    human_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Did the human disagree with the AI recommendation?
    human_disagrees: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["ScreeningSession"] = relationship("ScreeningSession", back_populates="evaluation")


class NPSFeedback(Base):
    """Candidate satisfaction feedback after completing the screening."""
    __tablename__ = "nps_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("screening_sessions.id"), unique=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
