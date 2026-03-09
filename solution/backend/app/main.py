"""FastAPI application entry point.

Mounts:
  - REST API (auth, campaigns, candidates, evaluations)
  - Telegram webhook receiver
"""

import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update

from app.config import settings
from app.api.routes import auth_router, campaigns_router, candidates_router, evaluations_router
from app.telegram import build_application, set_webhook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Build Telegram bot application (shared singleton)
tg_app = build_application()

app = FastAPI(
    title="EntreVista AI",
    description="Plataforma de entrevistas agénticas para LATAM",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── REST API Routers ─────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(campaigns_router, prefix="/api/v1")
app.include_router(candidates_router, prefix="/api/v1")
app.include_router(evaluations_router, prefix="/api/v1")


# ─── Telegram Webhook ─────────────────────────────────────────────────────────
@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}


# ─── Lifecycle ────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await tg_app.initialize()
    if settings.environment == "production":
        await set_webhook(tg_app)
    else:
        logger.info("Development mode — use polling or set TELEGRAM_WEBHOOK_URL for webhook.")


@app.on_event("shutdown")
async def shutdown():
    await tg_app.shutdown()


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
