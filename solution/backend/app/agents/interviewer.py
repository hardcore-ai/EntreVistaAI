"""InterviewerAgent — the core conversational AI for candidate screening.

Architecture:
- State machine drives the conversation (see SessionStatus enum).
- Each user message is processed by Claude with the full conversation history.
- The agent decides the next response AND signals state transitions via structured output.
- Guardrails are applied before returning any message to the candidate.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import anthropic

from app.config import settings
from app.agents.prompts import (
    INTERVIEWER_SYSTEM_PROMPT,
    CONSENT_MESSAGE,
    CONSENT_DECLINED_MESSAGE,
    REQUIREMENTS_INTRO,
    REQUIREMENTS_FAILED_MESSAGE,
    SCREENING_INTRO,
    CLOSING_MESSAGE,
    NPS_FOLLOWUP,
    THANK_YOU_MESSAGE,
    OUT_OF_SCOPE_RESPONSE,
    ESCALATION_RESPONSE,
)

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

MAX_SCREENING_QUESTIONS = 5
MAX_FOLLOWUPS_PER_QUESTION = 2


@dataclass
class AgentResponse:
    """What the agent returns after processing a candidate message."""
    message: str                    # Text to send to the candidate
    new_state: str                  # Next session state
    metadata: dict[str, Any]        # Extra info (state transitions, flags)
    should_escalate: bool = False   # Trigger human escalation alert


def _build_competencies_description(competencies: list[dict]) -> str:
    if not competencies:
        return "Experiencia y habilidades relevantes para el puesto."
    lines = []
    for c in competencies:
        levels_str = ""
        if "levels" in c:
            levels_str = " | ".join(
                f"Nivel {k}: {v}" for k, v in sorted(c["levels"].items())
            )
        lines.append(
            f"- **{c['name']}** (peso: {c.get('weight', 1.0):.0%}): "
            f"{c.get('description', '')}. {levels_str}"
        )
    return "\n".join(lines)


def _build_requirements_description(requirements: list[dict]) -> str:
    if not requirements:
        return ""
    return "\n".join(f"- {r.get('label', r)}: {r.get('question', '')}" for r in requirements)


class InterviewerAgent:
    """Stateless agent — all state comes from the session object passed in."""

    async def process_message(
        self,
        user_message: str,
        session_state: str,
        conversation_history: list[dict],
        campaign_data: dict,
        current_question_index: int = 0,
        followup_count: int = 0,
        candidate_name: str | None = None,
    ) -> AgentResponse:
        """Main entry point — routes to the appropriate handler based on state."""

        state_handlers = {
            "initiated": self._handle_initiated,
            "consent": self._handle_consent,
            "requirements": self._handle_requirements,
            "screening": self._handle_screening,
            "closing": self._handle_closing,
            "feedback": self._handle_feedback,
        }

        handler = state_handlers.get(session_state, self._handle_unknown_state)
        return await handler(
            user_message=user_message,
            conversation_history=conversation_history,
            campaign_data=campaign_data,
            current_question_index=current_question_index,
            followup_count=followup_count,
            candidate_name=candidate_name,
        )

    # ─── State Handlers ───────────────────────────────────────────────────────

    async def _handle_initiated(self, user_message: str, campaign_data: dict, **kwargs) -> AgentResponse:
        """State: INITIATED — first contact, show consent message."""
        consent_text = CONSENT_MESSAGE.format(
            company_name=campaign_data["company_name"],
            job_title=campaign_data["title"],
            retention_days=campaign_data.get("retention_days", 90),
        )
        return AgentResponse(
            message=consent_text,
            new_state="consent",
            metadata={"trigger": "first_contact"},
        )

    async def _handle_consent(
        self,
        user_message: str,
        campaign_data: dict,
        conversation_history: list[dict],
        candidate_name: str | None,
        **kwargs,
    ) -> AgentResponse:
        """State: CONSENT — capture explicit yes/no."""
        normalized = user_message.strip().lower()

        # Affirmative patterns
        affirmative = any(w in normalized for w in ["sí", "si", "yes", "acepto", "ok", "claro", "adelante", "de acuerdo"])
        negative = any(w in normalized for w in ["no", "rechaz", "cancel", "salir"])

        if negative:
            return AgentResponse(
                message=CONSENT_DECLINED_MESSAGE,
                new_state="abandoned",
                metadata={"reason": "consent_declined"},
            )

        if not affirmative:
            # Ask again
            return AgentResponse(
                message="Para continuar necesito tu confirmación. Por favor responde *Sí* para aceptar o *No* para salir.",
                new_state="consent",
                metadata={},
            )

        # Consent given — ask for name
        return AgentResponse(
            message="¡Perfecto! Antes de comenzar, ¿cuál es tu nombre?",
            new_state="requirements",
            metadata={"consent_given": True},
        )

    async def _handle_requirements(
        self,
        user_message: str,
        campaign_data: dict,
        conversation_history: list[dict],
        candidate_name: str | None,
        **kwargs,
    ) -> AgentResponse:
        """State: REQUIREMENTS — collect name then check basic requirements via LLM."""
        requirements = campaign_data.get("requirements", [])

        # First sub-step: capture name
        if not candidate_name:
            extracted_name = user_message.strip().split()[0].capitalize() if user_message.strip() else "candidato"
            intro = REQUIREMENTS_INTRO.format(name=extracted_name)

            if not requirements:
                # No requirements — go straight to screening
                return AgentResponse(
                    message=intro + "\n\n" + SCREENING_INTRO,
                    new_state="screening",
                    metadata={"candidate_name": extracted_name, "requirements_passed": True},
                )

            first_req = requirements[0]
            return AgentResponse(
                message=f"{intro}\n\n{first_req.get('question', '')}",
                new_state="requirements",
                metadata={"candidate_name": extracted_name, "requirement_index": 0},
            )

        # Subsequent: use LLM to evaluate requirement answer and decide next step
        response = await self._requirements_llm(
            user_message=user_message,
            conversation_history=conversation_history,
            requirements=requirements,
            campaign_data=campaign_data,
            candidate_name=candidate_name,
        )
        return response

    async def _requirements_llm(
        self,
        user_message: str,
        conversation_history: list[dict],
        requirements: list[dict],
        campaign_data: dict,
        candidate_name: str,
    ) -> AgentResponse:
        """Use LLM to evaluate requirements and decide next action."""
        req_descriptions = _build_requirements_description(requirements)
        system = f"""Eres un asistente de reclutamiento evaluando requisitos básicos.
Candidato: {candidate_name}
Puesto: {campaign_data['title']}
Requisitos a verificar:
{req_descriptions}

Basándote en el historial de conversación, determina:
1. ¿Qué requisitos ya se han verificado y con qué resultado?
2. ¿Hay más requisitos por verificar?
3. Si todos los requisitos están cubiertos, ¿cumple el candidato con todos?

Responde SOLO en JSON:
{{
  "next_action": "ask_next_requirement" | "all_passed" | "failed",
  "next_question": "<pregunta para el siguiente requisito, si aplica>",
  "failed_requirement": "<nombre del requisito que falló, si aplica>",
  "message_to_candidate": "<mensaje natural en español para enviar al candidato>"
}}"""

        messages = conversation_history + [{"role": "user", "content": user_message}]

        resp = await client.messages.create(
            model=settings.claude_model,
            max_tokens=500,
            system=system,
            messages=messages,
        )
        raw = resp.content[0].text.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: assume passed
            data = {"next_action": "all_passed", "message_to_candidate": SCREENING_INTRO}

        action = data.get("next_action", "all_passed")

        if action == "failed":
            return AgentResponse(
                message=REQUIREMENTS_FAILED_MESSAGE.format(name=candidate_name),
                new_state="abandoned",
                metadata={"reason": "requirements_failed", "failed_requirement": data.get("failed_requirement")},
            )

        if action == "ask_next_requirement":
            return AgentResponse(
                message=data.get("message_to_candidate", ""),
                new_state="requirements",
                metadata={},
            )

        # all_passed → move to screening
        return AgentResponse(
            message=SCREENING_INTRO,
            new_state="screening",
            metadata={"requirements_passed": True},
        )

    async def _handle_screening(
        self,
        user_message: str,
        campaign_data: dict,
        conversation_history: list[dict],
        current_question_index: int,
        followup_count: int,
        candidate_name: str | None,
        **kwargs,
    ) -> AgentResponse:
        """State: SCREENING — core interview loop with dynamic follow-ups."""
        competencies = campaign_data.get("competencies", [])

        system_prompt = INTERVIEWER_SYSTEM_PROMPT.format(
            company_name=campaign_data["company_name"],
            job_title=campaign_data["title"],
            role_description=campaign_data.get("role_description", ""),
            competencies_description=_build_competencies_description(competencies),
            knowledge_base=campaign_data.get("knowledge_base", "No hay información adicional disponible."),
            current_state="SCREENING",
            current_question_index=current_question_index,
            followup_count=followup_count,
        )

        # Build instruction for the LLM on what to do next
        questions_remaining = MAX_SCREENING_QUESTIONS - current_question_index
        can_followup = followup_count < MAX_FOLLOWUPS_PER_QUESTION

        decision_instruction = f"""
Basándote en la respuesta del candidato, decide:
1. ¿La respuesta tiene suficiente evidencia específica para evaluar la competencia?
2. ¿Debo hacer una repregunta para obtener más detalles? ({followup_count} repreguntas hechas, máximo {MAX_FOLLOWUPS_PER_QUESTION})
3. ¿Debo pasar a la siguiente pregunta de competencia? (pregunta {current_question_index + 1} de {MAX_SCREENING_QUESTIONS})
4. ¿Ya terminé todas las preguntas y debo pasar al cierre?

Responde en JSON:
{{
  "action": "followup" | "next_question" | "end_screening" | "escalate" | "out_of_scope",
  "message": "<tu respuesta natural al candidato en español>",
  "escalation_reason": "<solo si action=escalate>"
}}

Reglas:
- Si el candidato pregunta por salario/beneficios/políticas no en la base de conocimiento → action=out_of_scope
- Si el candidato pide hablar con una persona → action=escalate
- Si la respuesta es muy vaga y puedes profundizar ({can_followup}) → action=followup
- Si ya hay {MAX_SCREENING_QUESTIONS} preguntas hechas → action=end_screening
- Si {questions_remaining} preguntas restantes → continúa con la siguiente competencia
"""

        messages = conversation_history + [
            {"role": "user", "content": user_message},
            {"role": "user", "content": decision_instruction},
        ]

        resp = await client.messages.create(
            model=settings.claude_model,
            max_tokens=600,
            system=system_prompt,
            messages=conversation_history + [{"role": "user", "content": user_message + "\n\n" + decision_instruction}],
        )

        raw = resp.content[0].text.strip()

        try:
            # Claude may wrap JSON in markdown
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            data = json.loads(raw)
        except (json.JSONDecodeError, IndexError):
            # Graceful degradation — treat as a normal response
            data = {"action": "next_question", "message": raw}

        action = data.get("action", "next_question")
        message = data.get("message", "")

        if action == "out_of_scope":
            message = OUT_OF_SCOPE_RESPONSE
            return AgentResponse(
                message=message,
                new_state="screening",
                metadata={"current_question_index": current_question_index, "followup_count": followup_count},
            )

        if action == "escalate":
            return AgentResponse(
                message=ESCALATION_RESPONSE,
                new_state="escalated",
                metadata={
                    "escalation_reason": data.get("escalation_reason", "candidate_requested"),
                    "current_question_index": current_question_index,
                },
                should_escalate=True,
            )

        if action == "followup":
            return AgentResponse(
                message=message,
                new_state="screening",
                metadata={
                    "current_question_index": current_question_index,
                    "followup_count": followup_count + 1,
                },
            )

        if action == "end_screening":
            closing = CLOSING_MESSAGE.format(name=candidate_name or "")
            return AgentResponse(
                message=message + "\n\n" + closing,
                new_state="closing",
                metadata={"current_question_index": current_question_index + 1},
            )

        # next_question
        new_index = current_question_index + 1
        if new_index >= MAX_SCREENING_QUESTIONS:
            closing = CLOSING_MESSAGE.format(name=candidate_name or "")
            return AgentResponse(
                message=message + "\n\n" + closing,
                new_state="closing",
                metadata={"current_question_index": new_index},
            )

        return AgentResponse(
            message=message,
            new_state="screening",
            metadata={
                "current_question_index": new_index,
                "followup_count": 0,
            },
        )

    async def _handle_closing(
        self,
        user_message: str,
        candidate_name: str | None,
        **kwargs,
    ) -> AgentResponse:
        """State: CLOSING — capture NPS score (1-5)."""
        score = None
        for char in user_message:
            if char in "12345":
                score = int(char)
                break

        if score is None:
            return AgentResponse(
                message="Por favor, indica tu calificación con un número del 1 al 5.",
                new_state="closing",
                metadata={},
            )

        return AgentResponse(
            message=NPS_FOLLOWUP,
            new_state="feedback",
            metadata={"nps_score": score},
        )

    async def _handle_feedback(
        self,
        user_message: str,
        candidate_name: str | None,
        **kwargs,
    ) -> AgentResponse:
        """State: FEEDBACK — capture optional open-ended feedback, then complete."""
        feedback_text = None if user_message.strip().lower() in ["listo", "no", "nada", "ok", ""] else user_message

        return AgentResponse(
            message=THANK_YOU_MESSAGE.format(name=candidate_name or ""),
            new_state="completed",
            metadata={"feedback_text": feedback_text},
        )

    async def _handle_unknown_state(self, **kwargs) -> AgentResponse:
        return AgentResponse(
            message="Ha ocurrido un error en la sesión. Por favor, inicia una nueva entrevista.",
            new_state="abandoned",
            metadata={"reason": "unknown_state"},
        )
