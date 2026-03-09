import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class AuditLog(Base):
    """Immutable audit trail — every significant event is recorded here.

    Records are append-only; no update or delete paths should exist.
    PRD Principle 3: full traceability of all evaluations and decisions.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("screening_sessions.id"), nullable=True, index=True)
    operator_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("operators.id"), nullable=True)

    # Event types: consent_given | message_received | message_sent | evaluation_created
    #              human_decision | escalation | reengagement_sent | session_abandoned
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Arbitrary structured payload — captures full context
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    # Immutable timestamp — set at insert, never updated
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    session: Mapped["ScreeningSession | None"] = relationship("ScreeningSession", back_populates="audit_logs")
