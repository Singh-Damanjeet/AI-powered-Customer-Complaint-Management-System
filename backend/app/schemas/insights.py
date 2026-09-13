"""Typed contracts for optional complaint intelligence features."""

from enum import Enum
from typing import Annotated, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


InsightText: TypeAlias = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class CompletenessStatus(str, Enum):
    """Application-level intake completeness bands."""

    COMPLETE = "COMPLETE"
    MOSTLY_COMPLETE = "MOSTLY_COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    INSUFFICIENT = "INSUFFICIENT"


class ComplaintCompleteness(BaseModel):
    """Deterministic completeness result for an in-memory complaint."""

    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    status: CompletenessStatus
    missing_fields: list[InsightText] = Field(default_factory=list)
    missing_critical_fields: list[InsightText] = Field(default_factory=list)
    message: InsightText


class DuplicateMatch(BaseModel):
    """One saved complaint that shares explainable complaint signals."""

    model_config = ConfigDict(extra="forbid")

    complaint_id: int
    complaint_number: InsightText
    similarity_score: int = Field(ge=0, le=100)
    matched_fields: list[InsightText] = Field(default_factory=list)
    reason: InsightText


class DuplicateDetectionResult(BaseModel):
    """Possible duplicate candidates returned by the structured matcher."""

    model_config = ConfigDict(extra="forbid")

    possible_duplicate: bool = False
    matches: list[DuplicateMatch] = Field(default_factory=list, max_length=5)


class ComplaintSummary(BaseModel):
    """Concise QA-oriented summary generated from validated complaint facts."""

    model_config = ConfigDict(extra="forbid")

    summary: InsightText


class InvestigationSuggestion(BaseModel):
    """A hypothesis for investigation, never a confirmed root cause."""

    model_config = ConfigDict(extra="forbid")

    category: InsightText
    rationale: InsightText


class RootCauseRecommendation(BaseModel):
    """Potential investigation areas suggested by AI."""

    model_config = ConfigDict(extra="forbid")

    suggestions: list[InvestigationSuggestion] = Field(
        default_factory=list,
        max_length=5,
    )


class CAPARecommendations(BaseModel):
    """Proposed CAPA-oriented actions requiring QA review."""

    model_config = ConfigDict(extra="forbid")

    immediate_actions: list[InsightText] = Field(default_factory=list)
    investigation_actions: list[InsightText] = Field(default_factory=list)
    preventive_actions: list[InsightText] = Field(default_factory=list)


class ComplaintAIInsights(BaseModel):
    """Aggregated optional insights returned alongside mandatory workflow data."""

    model_config = ConfigDict(extra="forbid")

    completeness: ComplaintCompleteness
    duplicates: DuplicateDetectionResult = Field(
        default_factory=DuplicateDetectionResult,
    )
    summary: ComplaintSummary | None = None
    investigation_suggestions: RootCauseRecommendation | None = None
    capa_recommendations: CAPARecommendations | None = None
    insight_errors: list[InsightText] = Field(default_factory=list)


__all__ = [
    "CAPARecommendations",
    "CompletenessStatus",
    "ComplaintAIInsights",
    "ComplaintCompleteness",
    "ComplaintSummary",
    "DuplicateDetectionResult",
    "DuplicateMatch",
    "InvestigationSuggestion",
    "RootCauseRecommendation",
]
