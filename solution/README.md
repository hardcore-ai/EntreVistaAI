# EntreVista AI — Solución Técnica

Implementación completa del PRD `specs/prd.md`.

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| LLM | Claude claude-sonnet-4-6 (Anthropic) |
| Canal candidato | Telegram (python-telegram-bot) |
| Backend | Python 3.11 + FastAPI + SQLAlchemy async |
| Base de datos | PostgreSQL 16 |
| Caché / sesiones | Redis 7 |
| Scheduler | APScheduler (re-engagement) |
| Dashboard | Next.js 15 + TypeScript + Tailwind CSS |
| Contenedores | Docker + Docker Compose |

## Arquitectura

```
Candidato (Telegram)
       │
       ▼
┌──────────────────────┐
│  Telegram Webhook    │  FastAPI POST /telegram/webhook
│  python-telegram-bot │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  SessionService      │  Máquina de estados de la entrevista
│  (session_service)   │
└──────────┬───────────┘
           │
    ┌──────┴────────┐
    ▼               ▼
┌───────────┐  ┌────────────┐
│Interviewer│  │ Evaluator  │
│  Agent    │  │  Agent     │
│(Claude AI)│  │(Claude AI) │
└───────────┘  └────────────┘
           │
           ▼
┌──────────────────────┐
│  PostgreSQL          │  Sessions, Evaluations, AuditLogs
└──────────────────────┘
           │
           ▼
┌──────────────────────┐
│  Recruiter Dashboard │  Next.js — Cola HITL, Campañas, Analytics
└──────────────────────┘
```

## Módulos Implementados (PRD §9)

| Módulo PRD | Implementación |
|-----------|---------------|
| Motor Conversacional Agéntico | `app/agents/interviewer.py` + `app/telegram/` |
| Motor de Evaluación y Rúbricas | `app/agents/evaluator.py` + `app/models/evaluation.py` |
| Dashboard del Reclutador | `frontend/src/app/dashboard/` |
| Motor de Consentimiento y Compliance | `app/agents/prompts.py` (CONSENT_MESSAGE) + `app/models/audit.py` |
| Gestión de Candidatos y Feedback | `app/models/candidate.py` + NPS en `session_service.py` |

## Quick Start

```bash
# 1. Configura variables de entorno
cp .env.example .env
# Edita .env con tus credenciales:
# - ANTHROPIC_API_KEY
# - TELEGRAM_BOT_TOKEN

# 2. Inicia todos los servicios
docker compose up --build

# 3. El backend corre en: http://localhost:8000
#    El dashboard corre en: http://localhost:3000
#    API docs (Swagger): http://localhost:8000/docs
```

## Flujo de la Entrevista

```
/start → [CONSENT] → [REQUIREMENTS] → [SCREENING] → [CLOSING] → [FEEDBACK] → COMPLETED
                                                                              ↓
                                                                     EvaluatorAgent
                                                                              ↓
                                                                    Recruiter Dashboard
                                                                    (Cola HITL — HITL)
```

## Estados de sesión

| Estado | Descripción |
|--------|-------------|
| `initiated` | Primer contacto |
| `consent` | Presentando términos, esperando aceptación |
| `requirements` | Verificando requisitos básicos |
| `screening` | Entrevista de competencias activa |
| `closing` | Agradecimiento + NPS numérico |
| `feedback` | Feedback abierto post-entrevista |
| `completed` | Entrevista finalizada → evaluación generada |
| `abandoned` | Candidato no respondió en 72h |
| `escalated` | Candidato solicitó hablar con humano |

## Principios PRD implementados

| Principio | Implementación |
|-----------|---------------|
| HITL | `POST /api/v1/evaluations/{id}/decide` — el agente nunca auto-aprueba |
| Transparencia | `CONSENT_MESSAGE` — identidad de IA + consentimiento antes de iniciar |
| Trazabilidad | `AuditLog` — cada evento es inmutable con payload completo |
| Anti-alucinación | `OUT_OF_SCOPE_RESPONSE` + guardrails en system prompt |
| Privacidad | Sin datos sensibles, retención configurable, multi-tenancy |
| Experiencia candidato | NPS post-screening, re-engagement hasta 72h, sin tiempo límite |

## API Reference

Ver `http://localhost:8000/docs` para la documentación Swagger completa.

Endpoints principales:
- `POST /auth/token` — Login de reclutador
- `POST /auth/register` — Registro de empresa + admin
- `GET /api/v1/campaigns` — Listar campañas
- `POST /api/v1/campaigns` — Crear campaña
- `GET /api/v1/evaluations?status=pending_review` — Cola HITL
- `POST /api/v1/evaluations/{id}/decide` — Aprobar/rechazar candidato
- `POST /telegram/webhook` — Recibe mensajes de Telegram

## Re-engagement (Scheduler)

El proceso `scheduler` corre cada 30 minutos y envía recordatorios automáticos:
- **24h** de inactividad: primer recordatorio
- **48h**: segundo recordatorio
- **72h**: mensaje final + sesión marcada como `abandoned`

## Estructura del Proyecto

```
solution/
├── .env.example
├── docker-compose.yml
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── alembic/           # Migraciones de base de datos
│   └── app/
│       ├── main.py        # FastAPI app + Telegram webhook
│       ├── config.py      # Settings (Pydantic)
│       ├── database.py    # SQLAlchemy async engine
│       ├── agents/
│       │   ├── interviewer.py   # Agente conversacional principal
│       │   ├── evaluator.py     # Generador de evaluaciones estructuradas
│       │   └── prompts.py       # Todos los prompts del sistema
│       ├── models/        # SQLAlchemy ORM models
│       ├── services/      # Lógica de negocio + orquestación
│       ├── api/routes/    # REST API endpoints
│       ├── telegram/      # Telegram bot handlers
│       └── scheduler.py   # Jobs de re-engagement
└── frontend/
    └── src/app/
        ├── login/              # Autenticación
        └── dashboard/
            ├── page.tsx        # KPI Overview
            ├── campaigns/      # Gestión de campañas
            └── candidates/     # Cola HITL + detalle
```
