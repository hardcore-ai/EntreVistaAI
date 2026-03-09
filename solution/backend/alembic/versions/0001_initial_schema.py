"""Initial schema

Revision ID: 0001
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # companies
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("plan", sa.String(50), default="pilot"),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # operators
    op.create_table(
        "operators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), default="recruiter"),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("last_login", sa.DateTime, nullable=True),
    )

    # rubrics
    op.create_table(
        "rubrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role_type", sa.String(100)),
        sa.Column("competencies", postgresql.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # campaigns
    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("rubric_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rubrics.id"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("operators.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("role_description", sa.Text, default=""),
        sa.Column("requirements", postgresql.JSON, default=list),
        sa.Column("knowledge_base", sa.Text, default=""),
        sa.Column("telegram_link_token", sa.String(100), unique=True, nullable=False),
        sa.Column("status", sa.String(50), default="active"),
        sa.Column("retention_days", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("closed_at", sa.DateTime, nullable=True),
    )

    # candidates
    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger, unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # screening_sessions
    op.create_table(
        "screening_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("status", sa.String(50), default="initiated"),
        sa.Column("conversation_history", postgresql.JSON, default=list),
        sa.Column("current_question_index", sa.Integer, default=0),
        sa.Column("followup_count", sa.Integer, default=0),
        sa.Column("requirements_check", postgresql.JSON, default=dict),
        sa.Column("escalations", postgresql.JSON, default=list),
        sa.Column("candidate_name", sa.String(255), nullable=True),
        sa.Column("reengagement_sent_24h", sa.Boolean, default=False),
        sa.Column("reengagement_sent_48h", sa.Boolean, default=False),
        sa.Column("reengagement_sent_72h", sa.Boolean, default=False),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("last_activity_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )

    # evaluations
    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("screening_sessions.id"), unique=True),
        sa.Column("overall_score", sa.Float, nullable=True),
        sa.Column("competency_scores", postgresql.JSON, default=list),
        sa.Column("summary", sa.Text, default=""),
        sa.Column("strengths", postgresql.JSON, default=list),
        sa.Column("concerns", postgresql.JSON, default=list),
        sa.Column("ai_recommendation", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), default="pending_review"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("operators.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("human_decision", sa.String(50), nullable=True),
        sa.Column("human_notes", sa.Text, nullable=True),
        sa.Column("human_disagrees", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # nps_feedback
    op.create_table(
        "nps_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("screening_sessions.id"), unique=True),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("feedback_text", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("screening_sessions.id"), nullable=True, index=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operators.id"), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False, index=True),
        sa.Column("payload", postgresql.JSON, default=dict),
        sa.Column("timestamp", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("nps_feedback")
    op.drop_table("evaluations")
    op.drop_table("screening_sessions")
    op.drop_table("candidates")
    op.drop_table("campaigns")
    op.drop_table("rubrics")
    op.drop_table("operators")
    op.drop_table("companies")
