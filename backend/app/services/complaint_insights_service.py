"""Orchestration for optional complaint insights."""

from __future__ import annotations

import inspect
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.complaint import ComplaintData, RiskAssessment
from app.schemas.insights import (
    CAPARecommendations,
    ComplaintAIInsights,
    ComplaintCompleteness,
    ComplaintSummary,
    DuplicateDetectionResult,
    RootCauseRecommendation,
)
from app.services.complaint_summary_service import ComplaintSummaryService
from app.services.completeness_service import CompletenessService, is_known_value
from app.services.capa_service import CAPAService
from app.services.duplicate_detection_service import DuplicateDetectionService
from app.services.root_cause_service import RootCauseService


async def _maybe_await(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


def _service_method(service: Any, *names: str):
    """Resolve a small compatibility set of service operation names."""

    for name in names:
        method = getattr(service, name, None)
        if callable(method):
            return method
    raise AttributeError(f"Service does not provide any of: {', '.join(names)}")


def _has_known_facts(complaint: ComplaintData) -> bool:
    return any(is_known_value(value) for value in complaint.model_dump(mode="python").values())


def _append_error(errors: list[str], error_code: str) -> None:
    if error_code not in errors:
        errors.append(error_code)


class ComplaintInsightsService:
    """Run deterministic and optional AI insights without affecting core work."""

    def __init__(
        self,
        session: Session | None = None,
        groq_service: Any | None = None,
        *,
        completeness_service: CompletenessService | Any | None = None,
        duplicate_detection_service: DuplicateDetectionService | Any | None = None,
        summary_service: ComplaintSummaryService | Any | None = None,
        root_cause_service: RootCauseService | Any | None = None,
        capa_service: CAPAService | Any | None = None,
        minimum_ai_score: int = 40,
    ) -> None:
        if not 0 <= minimum_ai_score <= 100:
            raise ValueError("minimum_ai_score must be between 0 and 100.")
        self.completeness_service = completeness_service or CompletenessService()
        self.duplicate_detection_service = (
            duplicate_detection_service
            if duplicate_detection_service is not None
            else DuplicateDetectionService(session) if session is not None else None
        )
        self.summary_service = summary_service or ComplaintSummaryService(groq_service)
        self.root_cause_service = root_cause_service or RootCauseService(groq_service)
        self.capa_service = capa_service or CAPAService(groq_service)
        self.minimum_ai_score = minimum_ai_score

    async def analyze(
        self,
        complaint: ComplaintData,
        risk_assessment: RiskAssessment,
        exclude_complaint_id: int | str | None = None,
    ) -> ComplaintAIInsights:
        """Return available insights, isolating failures in optional features."""

        validated_complaint = ComplaintData.model_validate(complaint)
        validated_risk = RiskAssessment.model_validate(risk_assessment)
        completeness: ComplaintCompleteness = _service_method(
            self.completeness_service,
            "check",
            "calculate",
            "assess",
        )(validated_complaint)
        errors: list[str] = []

        duplicates = DuplicateDetectionResult()
        if self.duplicate_detection_service is not None:
            try:
                duplicate_result = await _maybe_await(
                    _service_method(
                        self.duplicate_detection_service,
                        "find_matches",
                        "detect",
                        "check",
                    )(
                        validated_complaint,
                        exclude_complaint_id=exclude_complaint_id,
                    )
                )
                duplicates = DuplicateDetectionResult.model_validate(duplicate_result)
            except Exception:
                _append_error(errors, "duplicates_unavailable")

        summary: ComplaintSummary | None = None
        if _has_known_facts(validated_complaint) and self.summary_service is not None:
            try:
                summary = ComplaintSummary.model_validate(
                    await _maybe_await(
                        _service_method(
                            self.summary_service,
                            "summarize",
                            "generate",
                            "process",
                        )(validated_complaint)
                    )
                )
            except Exception:
                _append_error(errors, "summary_unavailable")

        investigation_suggestions: RootCauseRecommendation | None = None
        capa_recommendations: CAPARecommendations | None = None
        if (
            completeness.score >= self.minimum_ai_score
            and _has_known_facts(validated_complaint)
        ):
            if self.root_cause_service is not None:
                try:
                    investigation_suggestions = RootCauseRecommendation.model_validate(
                        await _maybe_await(
                            _service_method(
                                self.root_cause_service,
                                "recommend",
                                "generate",
                                "process",
                            )(
                                validated_complaint,
                                validated_risk,
                            )
                        )
                    )
                except Exception:
                    _append_error(errors, "root_cause_unavailable")

            if self.capa_service is not None:
                try:
                    capa_recommendations = CAPARecommendations.model_validate(
                        await _maybe_await(
                            _service_method(
                                self.capa_service,
                                "recommend",
                                "generate",
                                "process",
                            )(
                                validated_complaint,
                                validated_risk,
                                investigation_suggestions,
                            )
                        )
                    )
                except Exception:
                    _append_error(errors, "capa_unavailable")

        return ComplaintAIInsights(
            completeness=completeness,
            duplicates=duplicates,
            summary=summary,
            investigation_suggestions=investigation_suggestions,
            capa_recommendations=capa_recommendations,
            insight_errors=errors,
        )

    def fallback(
        self,
        complaint: ComplaintData,
        risk_assessment: RiskAssessment,
        exclude_complaint_id: int | str | None = None,
    ) -> ComplaintAIInsights:
        """Return deterministic insights if an injected optional stage fails."""

        validated_complaint = ComplaintData.model_validate(complaint)
        # Validate risk as part of the fallback contract even though it is not
        # used for deterministic calculations.
        RiskAssessment.model_validate(risk_assessment)
        duplicates = DuplicateDetectionResult()
        errors = ["insights_unavailable"]
        if self.duplicate_detection_service is not None:
            try:
                result = _service_method(
                    self.duplicate_detection_service,
                    "find_matches",
                    "detect",
                    "check",
                )(
                    validated_complaint,
                    exclude_complaint_id=exclude_complaint_id,
                )
                if inspect.isawaitable(result):
                    # A fallback is deliberately synchronous. An async custom
                    # duplicate service cannot be safely driven from here.
                    result = None
                if result is not None:
                    duplicates = DuplicateDetectionResult.model_validate(result)
            except Exception:
                _append_error(errors, "duplicates_unavailable")
        return ComplaintAIInsights(
            completeness=_service_method(
                self.completeness_service,
                "check",
                "calculate",
                "assess",
            )(validated_complaint),
            duplicates=duplicates,
            insight_errors=errors,
        )

    analyze_insights = analyze

__all__ = ["ComplaintInsightsService"]
