import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON, Enum, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class SessionStatus(str, enum.Enum):
    INITIATED = "initiated"
    CONSENT = "consent"
    REQUIREMENTS = "requirements"
    SCREENING = "screening"
    CLOSING = "closing"
    FEEDBACK = "feedback"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ESCALATED = "escalated"


class ScreeningSession(Base):
    """One candidate's interview session for a campaign.

    conversation_history is a list of {"role": "user"|"assistant", "content": str}
    messages, suitable for direct use with the Anthropic Messages API.
    """
    __tablename__ = "screening_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)

    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.INITIATED)

    # Full conversation as Anthropic messages format
    conversation_history: Mapped[list] = mapped_column(JSON, default=list)

    # Tracks which screening question index we're on (0-indexed)
    current_question_index: Mapped[int] = mapped_column(Integer, default=0)
    # How many follow-ups have been asked for current question
    followup_count: Mapped[int] = mapped_column(Integer, default=0)

    # Requirements check results {"requirement_key": bool}
    requirements_check: Mapped[dict] = mapped_column(JSON, default=dict)

    # Escalations raised during the session
    escalations: Mapped[list] = mapped_column(JSON, default=list)

    # Candidate's name as captured during onboarding
    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Re-engagement tracking
    reengagement_sent_24h: Mapped[bool] = mapped_column(default=False)
    reengagement_sent_48h: Mapped[bool] = mapped_column(default=False)
    reengagement_sent_72h: Mapped[bool] = mapped_column(default=False)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="sessions")
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="sessions")
    evaluation: Mapped["Evaluation | None"] = relationship("Evaluation", back_populates="session", uselist=False)
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="session")
