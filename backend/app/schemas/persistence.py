"""Pydantic contracts for persisted complaint API responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class AuditEventCreate(BaseModel):
    """Validated client-supplied audit event waiting to be persisted."""

    model_config = ConfigDict(extra="forbid")

    action: NonEmptyText
    field_name: NonEmptyText | None = None
    old_value: Any = None
    new_value: Any = None
    source: AuditSource = AuditSource.AI


class ComplaintCreateRequest(ComplaintData):
    """Complaint creation payload with an optional persisted assessment.

    Flat complaint payloads are the primary API shape. For clients that use
    the Phase 1 response envelope, ``{"complaint": {...}}`` is also accepted
    and normalized before field validation.
    """

    risk_assessment: RiskAssessment | None = None
    audit_events: list[AuditEventCreate] = Field(default_factory=list)
    model_name: NonEmptyText | None = None

    @model_validator(mode="before")
    @classmethod
    def unwrap_complaint_envelope(cls, value: Any) -> Any:
        """Accept an optional nested complaint object without weakening types."""

        if not isinstance(value, dict) or "complaint" not in value:
            return value

        complaint = value["complaint"]
        if isinstance(complaint, BaseModel):
            complaint = complaint.model_dump(mode="python")
        if not isinstance(complaint, dict):
            return value

        normalized = dict(complaint)
        for field_name in ("risk_assessment", "audit_events", "model_name"):
            if field_name in value:
                normalized[field_name] = value[field_name]
        return normalized

    @property
    def complaint_data(self) -> ComplaintData:
        """Return the complaint-only portion of the compatible request."""

        return ComplaintData.model_validate(
            self.model_dump(
                exclude={"risk_assessment", "audit_events", "model_name"},
                mode="python",
            )
        )


class ComplaintSaveRequest(BaseModel):
    """Clean nested save contract with compatibility for legacy flat payloads."""

    model_config = ConfigDict(extra="forbid")

    complaint: ComplaintData
    risk_assessment: RiskAssessment | None = None
    audit_events: list[AuditEventCreate] = Field(default_factory=list)
    model_name: NonEmptyText | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_flat_payload(cls, value: Any) -> Any:
        """Accept the Phase 2 flat payload while documenting a nested API shape."""

        if isinstance(value, BaseModel):
            value = value.model_dump(mode="python")
        if not isinstance(value, dict) or "complaint" in value:
            return value

        normalized = dict(value)
        complaint_values = {
            field_name: normalized.pop(field_name)
            for field_name in ComplaintData.model_fields
            if field_name in normalized
        }
        normalized["complaint"] = complaint_values
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


class SavedComplaintResponse(ComplaintResponse):
    """Response returned after a complaint and its audit batch are committed."""


class AuditLogResponse(BaseModel):
    """Immutable audit event returned by complaint history endpoints."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    id: int
    complaint_id: int
    action: NonEmptyText
    field_name: NonEmptyText | None = None
    old_value: str | None = None
    new_value: str | None = None
    source: AuditSource
    created_at: datetime


class AuditLogCollectionResponse(BaseModel):
    """Chronologically ordered complaint audit history."""

    items: list[AuditLogResponse] = Field(default_factory=list)


# Common read-name alias for callers that prefer REST naming.
ComplaintRead = ComplaintResponse


__all__ = [
    "AIAssessmentResponse",
    "AuditEventCreate",
    "AuditLogCollectionResponse",
    "AuditLogResponse",
    "AuditSource",
    "ComplaintCreateRequest",
    "ComplaintRead",
    "ComplaintResponse",
    "ComplaintSaveRequest",
    "ComplaintStatus",
    "ProductType",
    "SavedComplaintResponse",
]
