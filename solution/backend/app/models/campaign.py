import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Rubric(Base):
    """Evaluation rubric — competencies and scoring criteria for a campaign."""
    __tablename__ = "rubrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_type: Mapped[str] = mapped_column(String(100))  # bpo | tech | sales | logistics
    # competencies: [{"name": str, "weight": float, "description": str, "levels": {1..5: str}}]
    competencies: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaigns: Mapped[list["Campaign"]] = relationship("Campaign", back_populates="rubric")


class Campaign(Base):
    """A hiring campaign — creates a unique Telegram link and drives the interview process."""
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    rubric_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rubrics.id"), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("operators.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    role_description: Mapped[str] = mapped_column(Text, default="")
    # Basic requirements checklist (e.g. minimum age, location, availability)
    requirements: Mapped[list] = mapped_column(JSON, default=list)
    # Knowledge base docs / FAQ for the AI agent
    knowledge_base: Mapped[str] = mapped_column(Text, default="")

    telegram_link_token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active | paused | closed

    # Retention policy override (days). None → use company default.
    retention_days: Mapped[int | None] = mapped_column(nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="campaigns")
    rubric: Mapped["Rubric | None"] = relationship("Rubric", back_populates="campaigns")
    sessions: Mapped[list["ScreeningSession"]] = relationship("ScreeningSession", back_populates="campaign")
