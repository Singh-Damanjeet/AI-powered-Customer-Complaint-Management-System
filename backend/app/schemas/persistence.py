"""Pydantic contracts for persisted complaint API responses."""

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, model_validator

from app.schemas.complaint import (
    AuditSource,
    ComplaintData,
    ComplaintStatus,
    NonEmptyText,
    Priority,
    ProductType,
    RiskAssessment,
    Severity,
)


class ComplaintCreateRequest(ComplaintData):
    """Complaint creation payload with an optional persisted assessment.

    Flat complaint payloads are the primary API shape. For clients that use
    the Phase 1 response envelope, ``{"complaint": {...}}`` is also accepted
    and normalized before field validation.
    """

    risk_assessment: RiskAssessment | None = None
    model_name: NonEmptyText | None = None

    @model_validator(mode="before")
    @classmethod
    def unwrap_complaint_envelope(cls, value: Any) -> Any:
        """Accept an optional nested complaint object without weakening types."""

        if not isinstance(value, dict) or "complaint" not in value:
            return value

        complaint = value["complaint"]
        if not isinstance(complaint, dict):
            return value

        normalized = dict(complaint)
        for field_name in ("risk_assessment", "model_name"):
            if field_name in value:
                normalized[field_name] = value[field_name]
        return normalized


class AIAssessmentResponse(RiskAssessment):
    """Persisted AI-assessment record returned with a complaint."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    id: int
    complaint_id: int
    model_name: NonEmptyText | None = None
    created_at: datetime


class ComplaintResponse(ComplaintData):
    """Persisted complaint response with its latest assessment."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    id: int
    complaint_number: NonEmptyText
    severity: Severity
    priority: Priority
    status: ComplaintStatus
    created_at: datetime
    updated_at: datetime
    ai_assessment: AIAssessmentResponse | None = None


# Common read-name alias for callers that prefer REST naming.
ComplaintRead = ComplaintResponse


__all__ = [
    "AIAssessmentResponse",
    "AuditSource",
    "ComplaintCreateRequest",
    "ComplaintRead",
    "ComplaintResponse",
    "ComplaintStatus",
    "ProductType",
]
