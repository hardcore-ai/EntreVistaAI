from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from fastapi import Depends
from sqlalchemy import select

from app.api.deps import DB, verify_password, create_access_token, hash_password, CurrentOperator
from app.models import Operator, Company
from pydantic import BaseModel, EmailStr
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


class Token(BaseModel):
    access_token: str
    token_type: str


class RegisterRequest(BaseModel):
    company_name: str
    email: EmailStr
    name: str
    password: str


class OperatorOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    company_id: uuid.UUID

    model_config = {"from_attributes": True}


@router.post("/token", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    result = await db.execute(
        select(Operator).where(Operator.email == form_data.username, Operator.is_active == True)
    )
    operator = result.scalar_one_or_none()

    if not operator or not verify_password(form_data.password, operator.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    operator.last_login = datetime.utcnow()
    await db.commit()

    token = create_access_token({"sub": str(operator.id), "company_id": str(operator.company_id)})
    return Token(access_token=token, token_type="bearer")


@router.post("/register", response_model=OperatorOut, status_code=201)
async def register(payload: RegisterRequest, db: DB):
    """Self-service registration — creates a company + admin operator."""
    # Check email uniqueness
    existing = await db.execute(select(Operator).where(Operator.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El email ya está registrado.")

    company = Company(
        name=payload.company_name,
        slug=payload.company_name.lower().replace(" ", "-")[:100],
    )
    db.add(company)
    await db.flush()

    operator = Operator(
        company_id=company.id,
        email=payload.email,
        name=payload.name,
        role="admin",
        password_hash=hash_password(payload.password),
    )
    db.add(operator)
    await db.commit()
    await db.refresh(operator)
    return operator


@router.get("/me", response_model=OperatorOut)
async def me(current: CurrentOperator):
    return current
