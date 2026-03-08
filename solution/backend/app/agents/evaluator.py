"""EvaluatorAgent — generates structured evaluation after a completed screening.

Called once per session when status transitions to COMPLETED.
Output is stored in the Evaluation table and surfaced in the recruiter dashboard.

PRD Principle 3: "Every score has a citation" — all competency scores
include verbatim quotes from the candidate's responses.
"""

import json
import logging
from dataclasses import dataclass

import anthropic

from app.config import settings
from app.agents.prompts import EVALUATOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


@dataclass
class EvaluationResult:
    overall_score: float
    ai_recommendation: str
    summary: str
    strengths: list[str]
    concerns: list[str]
    competency_scores: list[dict]


async def generate_evaluation(
    conversation_history: list[dict],
    campaign_data: dict,
) -> EvaluationResult:
    """Analyze the full conversation and produce a structured evaluation."""
    competencies = campaign_data.get("competencies", [])

    competencies_description = _build_competencies_description(competencies)

    system_prompt = EVALUATOR_SYSTEM_PROMPT.format(
        job_title=campaign_data["title"],
        company_name=campaign_data["company_name"],
        competencies_description=competencies_description,
    )

    # Build a clean transcript for the evaluator
    transcript = _build_transcript(conversation_history)

    resp = await client.messages.create(
        model=settings.claude_model,
        max_tokens=2000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"""Evalúa la siguiente transcripción de entrevista.
Responde ÚNICAMENTE con JSON válido siguiendo el schema especificado.

TRANSCRIPCIÓN:
{transcript}
""",
            }
        ],
    )

    raw = resp.content[0].text.strip()

    # Strip markdown code fences if present
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("EvaluatorAgent: failed to parse JSON response: %s", raw[:500])
        # Return a safe default rather than crashing
        data = _default_evaluation(competencies)

    return EvaluationResult(
        overall_score=float(data.get("overall_score", 0)),
        ai_recommendation=data.get("ai_recommendation", "needs_review"),
        summary=data.get("summary", ""),
        strengths=data.get("strengths", []),
        concerns=data.get("concerns", []),
        competency_scores=data.get("competency_scores", []),
    )


def _build_transcript(conversation_history: list[dict]) -> str:
    lines = []
    for msg in conversation_history:
        role = "Candidato" if msg["role"] == "user" else "EntreVista AI"
        lines.append(f"[{role}]: {msg['content']}")
    return "\n".join(lines)


def _build_competencies_description(competencies: list[dict]) -> str:
    if not competencies:
        return "Evalúa las habilidades blandas y técnicas relevantes demostradas durante la entrevista."
    lines = []
    for c in competencies:
        lines.append(
            f"- {c['name']} (peso {c.get('weight', 1.0):.0%}): {c.get('description', '')}"
        )
    return "\n".join(lines)


def _default_evaluation(competencies: list[dict]) -> dict:
    return {
        "overall_score": 0,
        "ai_recommendation": "needs_review",
        "summary": "No se pudo generar la evaluación automática. Revisión manual requerida.",
        "strengths": [],
        "concerns": ["Error en generación de evaluación automática"],
        "competency_scores": [
            {
                "competency": c.get("name", "Competencia"),
                "score": 0,
                "weight": c.get("weight", 1.0),
                "rationale": "Evaluación automática no disponible.",
                "quotes": [],
            }
            for c in competencies
        ],
    }
