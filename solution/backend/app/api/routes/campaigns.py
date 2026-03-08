import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentOperator
from app.models import Campaign, Rubric, ScreeningSession, SessionStatus

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class RubricCompetency(BaseModel):
    name: str
    weight: float = 1.0
    description: str = ""
    levels: dict[str, str] = {}


class CampaignCreate(BaseModel):
    title: str
    role_description: str = ""
    requirements: list[dict] = []
    knowledge_base: str = ""
    rubric_name: str | None = None
    competencies: list[RubricCompetency] = []
    retention_days: int | None = None


class CampaignUpdate(BaseModel):
    title: str | None = None
    role_description: str | None = None
    requirements: list[dict] | None = None
    knowledge_base: str | None = None
    status: str | None = None
    retention_days: int | None = None


class CampaignOut(BaseModel):
    id: uuid.UUID
    title: str
    role_description: str
    requirements: list
    knowledge_base: str
    telegram_link_token: str
    status: str
    retention_days: int | None
    created_at: datetime
    stats: dict = {}

    model_config = {"from_attributes": True}


@router.post("", response_model=CampaignOut, status_code=201)
async def create_campaign(payload: CampaignCreate, db: DB, current: CurrentOperator):
    # Create rubric if competencies provided
    rubric = None
    if payload.competencies:
        rubric = Rubric(
            name=payload.rubric_name or f"Rúbrica {payload.title}",
            competencies=[c.model_dump() for c in payload.competencies],
        )
        db.add(rubric)
        await db.flush()

    token = secrets.token_urlsafe(16)
    campaign = Campaign(
        company_id=current.company_id,
        created_by=current.id,
        rubric_id=rubric.id if rubric else None,
        title=payload.title,
        role_description=payload.role_description,
        requirements=payload.requirements,
        knowledge_base=payload.knowledge_base,
        telegram_link_token=token,
        retention_days=payload.retention_days,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    result = CampaignOut.model_validate(campaign)
    return result


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(db: DB, current: CurrentOperator):
    result = await db.execute(
        select(Campaign)
        .where(Campaign.company_id == current.company_id)
        .order_by(Campaign.created_at.desc())
        .options(selectinload(Campaign.sessions))
    )
    campaigns = result.scalars().all()

    out = []
    for c in campaigns:
        data = CampaignOut.model_validate(c)
        data.stats = _compute_stats(c.sessions)
        out.append(data)
    return out


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: uuid.UUID, db: DB, current: CurrentOperator):
    campaign = await _get_campaign_or_404(db, campaign_id, current.company_id)
    result = CampaignOut.model_validate(campaign)
    result.stats = _compute_stats(campaign.sessions)
    return result


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(campaign_id: uuid.UUID, payload: CampaignUpdate, db: DB, current: CurrentOperator):
    campaign = await _get_campaign_or_404(db, campaign_id, current.company_id)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(campaign, field, value)

    if payload.status == "closed":
        campaign.closed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(campaign)
    return CampaignOut.model_validate(campaign)


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: uuid.UUID, db: DB, current: CurrentOperator):
    campaign = await _get_campaign_or_404(db, campaign_id, current.company_id)
    campaign.is_active = False
    campaign.status = "closed"
    campaign.closed_at = datetime.utcnow()
    await db.commit()


# ─── helpers ──────────────────────────────────────────────────────────────────

async def _get_campaign_or_404(db: DB, campaign_id: uuid.UUID, company_id: uuid.UUID) -> Campaign:
    result = await db.execute(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.company_id == company_id)
        .options(selectinload(Campaign.sessions), selectinload(Campaign.company))
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada.")
    return campaign


def _compute_stats(sessions: list[ScreeningSession]) -> dict:
    total = len(sessions)
    if total == 0:
        return {"total": 0, "completed": 0, "abandoned": 0, "pending_review": 0, "completion_rate": 0}

    completed = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
    abandoned = sum(1 for s in sessions if s.status == SessionStatus.ABANDONED)
    pending = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)  # has evaluation pending

    return {
        "total": total,
        "completed": completed,
        "abandoned": abandoned,
        "pending_review": pending,
        "completion_rate": round(completed / total * 100, 1) if total else 0,
    }
