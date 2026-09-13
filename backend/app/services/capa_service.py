"""Structured proposed CAPA actions for QA review."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from app.agents.prompts.bonus_insights import CAPA_SYSTEM_PROMPT, build_capa_prompt
from app.schemas.complaint import ComplaintData, RiskAssessment
from app.schemas.insights import CAPARecommendations, RootCauseRecommendation
from app.services.ai_errors import AIResponseValidationError
from app.services.groq_service import GroqResponseError, GroqService
from app.services.structured_ai import generate_structured_response


_UNSAFE_ACTION_PATTERN = re.compile(
    r"\b(?:has\s+been|was|were|is|are)\s+(?:implemented|completed|approved|"
    r"closed)\b|\b(?:confirmed|established)\s+root\s+cause\b",
    re.IGNORECASE,
)
_MAX_ACTIONS_PER_CATEGORY = 8


class _UnsafeCAPAActionError(ValueError):
    """Internal marker for an AI response that claims completed work."""


def _bounded_payload(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    return {
        **result,
        **{
            field_name: result.get(field_name, [])[:_MAX_ACTIONS_PER_CATEGORY]
            for field_name in (
                "immediate_actions",
                "investigation_actions",
                "preventive_actions",
            )
            if isinstance(result.get(field_name), list)
        },
    }


def _actions_are_safe(recommendations: CAPARecommendations) -> bool:
    actions = (
        *recommendations.immediate_actions,
        *recommendations.investigation_actions,
        *recommendations.preventive_actions,
    )
    return not any(_UNSAFE_ACTION_PATTERN.search(action) for action in actions)


class CAPAService:
    """Generate proposed actions, explicitly separate from approved CAPA."""

    def __init__(
        self,
        groq_service: GroqService | Any | None = None,
        *,
        max_attempts: int = 2,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        self.groq_service = groq_service
        self.max_attempts = max_attempts

    async def recommend(
        self,
        complaint: ComplaintData,
        risk_assessment: RiskAssessment,
        investigation_suggestions: RootCauseRecommendation | None = None,
    ) -> CAPARecommendations:
        """Return QA-reviewable action suggestions in three categories."""

        validated_complaint = ComplaintData.model_validate(complaint)
        validated_risk = RiskAssessment.model_validate(risk_assessment)
        validated_suggestions = (
            RootCauseRecommendation.model_validate(investigation_suggestions)
            if investigation_suggestions is not None
            else None
        )
        groq_service = self.groq_service or GroqService()
        last_error: Exception | None = None
        for _ in range(self.max_attempts):
            try:
                result = await generate_structured_response(
                    groq_service,
                    build_capa_prompt(
                        validated_complaint,
                        validated_risk,
                        validated_suggestions,
                    ),
                    CAPARecommendations,
                    system_prompt=CAPA_SYSTEM_PROMPT,
                    temperature=0.0,
                )
                recommendations = CAPARecommendations.model_validate(
                    _bounded_payload(result)
                )
                if not _actions_are_safe(recommendations):
                    raise _UnsafeCAPAActionError(
                        "CAPA output claimed completed or approved work."
                    )
                return recommendations
            except (GroqResponseError, ValidationError, _UnsafeCAPAActionError) as exc:
                last_error = exc

        raise AIResponseValidationError(
            "CAPA recommendations returned invalid structured data after retry."
        ) from last_error

    generate = recommend
    generate_recommendations = recommend
    suggest = recommend
    process = recommend


CapaService = CAPAService
CAPARecommendationService = CAPAService


__all__ = ["CAPARecommendationService", "CAPAService", "CapaService"]
