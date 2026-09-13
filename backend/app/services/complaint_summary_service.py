"""Structured, source-grounded complaint summaries."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from pydantic import ValidationError

from app.agents.prompts.bonus_insights import (
    SUMMARY_SYSTEM_PROMPT,
    build_summary_prompt,
)
from app.schemas.complaint import ComplaintData
from app.schemas.insights import ComplaintSummary
from app.services.ai_errors import AIResponseValidationError
from app.services.groq_service import GroqResponseError, GroqService
from app.services.structured_ai import generate_structured_response


_DATE_PATTERN = re.compile(
    r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b"
)


class _UngroundedSummaryError(ValueError):
    """Internal marker for a summary containing an unsupported date."""


def _date_variants(value: date) -> set[str]:
    return {
        value.isoformat(),
        value.strftime("%Y/%m/%d"),
        value.strftime("%d/%m/%Y"),
        value.strftime("%m/%d/%Y"),
        value.strftime("%d-%m-%Y"),
        value.strftime("%m-%d-%Y"),
    }


def _summary_dates_are_grounded(summary: str, complaint: ComplaintData) -> bool:
    """Reject numeric dates that cannot be tied to a known complaint date."""

    known_dates = {
        variant
        for field_name in (
            "manufacturing_date",
            "expiry_date",
            "complaint_date",
            "received_date",
        )
        for value in [getattr(complaint, field_name)]
        if isinstance(value, date)
        for variant in _date_variants(value)
    }
    for token in _DATE_PATTERN.findall(summary):
        if token not in known_dates:
            return False
    return True


class ComplaintSummaryService:
    """Generate a concise summary through the existing structured AI adapter."""

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

    async def summarize(self, complaint: ComplaintData) -> ComplaintSummary:
        """Return a validated, concise summary of known complaint facts."""

        validated = ComplaintData.model_validate(complaint)
        groq_service = self.groq_service or GroqService()
        last_error: Exception | None = None
        for _ in range(self.max_attempts):
            try:
                result = await generate_structured_response(
                    groq_service,
                    build_summary_prompt(validated),
                    ComplaintSummary,
                    system_prompt=SUMMARY_SYSTEM_PROMPT,
                    temperature=0.0,
                )
                summary = ComplaintSummary.model_validate(result)
                if not _summary_dates_are_grounded(summary.summary, validated):
                    raise _UngroundedSummaryError(
                        "Summary contains a date not present in the complaint."
                    )
                return summary
            except (GroqResponseError, ValidationError, _UngroundedSummaryError) as exc:
                last_error = exc

        raise AIResponseValidationError(
            "Complaint summary returned invalid structured data after retry."
        ) from last_error

    # Compatibility aliases for orchestration callers.
    generate = summarize
    generate_summary = summarize
    process = summarize


__all__ = ["ComplaintSummaryService"]
