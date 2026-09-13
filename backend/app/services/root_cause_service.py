"""Potential investigation-area recommendations for complaint review."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from app.agents.prompts.bonus_insights import (
    INVESTIGATION_SYSTEM_PROMPT,
    build_investigation_prompt,
)
from app.schemas.complaint import ComplaintData, RiskAssessment
from app.schemas.insights import RootCauseRecommendation
from app.services.ai_errors import AIResponseValidationError
from app.services.groq_service import GroqResponseError, GroqService
from app.services.structured_ai import generate_structured_response


_UNSAFE_FINDING_PATTERN = re.compile(
    r"\b(?:root\s+cause\s+(?:is|was|has\s+been)|confirmed\s+root\s+cause|"
    r"root\s+cause\s+(?:is\s+)?(?:definitely|proven)|definitely\s+caused\s+by|"
    r"proven\s+to\s+be)\b",
    re.IGNORECASE,
)


class _UnsafeInvestigationLanguageError(ValueError):
    """Internal marker for an AI response that states a finding as fact."""


def _bounded_payload(result: Any) -> Any:
    """Keep a permissive test/provider payload within the UI-sized contract."""

    if not isinstance(result, dict) or not isinstance(result.get("suggestions"), list):
        return result
    return {**result, "suggestions": result["suggestions"][:5]}


def _contains_unsafe_finding(recommendation: RootCauseRecommendation) -> bool:
    text = " ".join(
        f"{suggestion.category} {suggestion.rationale}"
        for suggestion in recommendation.suggestions
    )
    return _UNSAFE_FINDING_PATTERN.search(text) is not None


class RootCauseService:
    """Generate hypotheses without presenting any actual root cause finding."""

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
    ) -> RootCauseRecommendation:
        """Return a short list of potential investigation areas."""

        validated_complaint = ComplaintData.model_validate(complaint)
        validated_risk = RiskAssessment.model_validate(risk_assessment)
        groq_service = self.groq_service or GroqService()
        last_error: Exception | None = None
        for _ in range(self.max_attempts):
            try:
                result = await generate_structured_response(
                    groq_service,
                    build_investigation_prompt(validated_complaint, validated_risk),
                    RootCauseRecommendation,
                    system_prompt=INVESTIGATION_SYSTEM_PROMPT,
                    temperature=0.0,
                )
                recommendation = RootCauseRecommendation.model_validate(
                    _bounded_payload(result)
                )
                if _contains_unsafe_finding(recommendation):
                    raise _UnsafeInvestigationLanguageError(
                        "Investigation output stated a root cause as fact."
                    )
                return recommendation
            except (
                GroqResponseError,
                ValidationError,
                _UnsafeInvestigationLanguageError,
            ) as exc:
                last_error = exc

        raise AIResponseValidationError(
            "Investigation recommendations returned invalid structured data after retry."
        ) from last_error

    generate = recommend
    generate_suggestions = recommend
    suggest = recommend
    process = recommend


# Descriptive alias used by some callers while preserving one implementation.
RootCauseRecommendationService = RootCauseService


__all__ = [
    "RootCauseRecommendationService",
    "RootCauseService",
]
