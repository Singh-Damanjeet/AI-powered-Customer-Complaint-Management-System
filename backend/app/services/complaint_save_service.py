"""Transactional complaint save orchestration and audit batching."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.ai_assessment import AIAssessment
from app.models.audit_log import ComplaintAuditLog
from app.models.complaint import Complaint
from app.models.enums import AuditSource, ComplaintStatus
from app.repositories.complaint_repository import ComplaintRepository
from app.schemas.complaint import ComplaintData, RiskAssessment
from app.schemas.persistence import (
    AuditEventCreate,
    ComplaintCreateRequest,
    ComplaintSaveRequest,
)
from app.services.complaint_service import (
    ComplaintPersistenceError,
    generate_complaint_number,
)


def _audit_value(value: object) -> str | None:
    """Serialize audit values without losing dates, enums, or JSON values."""

    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, default=_audit_json_default, sort_keys=True)
    return str(value)


def _audit_json_default(value: object) -> str:
    """Provide stable JSON conversion for nested audit values."""

    serialized = _audit_value(value)
    if serialized is None:
        return "null"
    return serialized


def _assessment_model(
    complaint_id: int,
    assessment: RiskAssessment,
    model_name: str | None,
) -> AIAssessment:
    """Map a validated risk assessment to an immutable persistence snapshot."""

    configured_model = get_settings().groq_model
    return AIAssessment(
        complaint_id=complaint_id,
        severity=assessment.severity,
        priority=assessment.priority,
        rationale=assessment.rationale,
        recommended_actions=list(assessment.recommended_actions),
        qa_investigation_required=assessment.qa_investigation_required,
        product_replacement_recommended=assessment.product_replacement_recommended,
        model_name=model_name or configured_model or "not_assessed",
    )


def _temporary_complaint_number() -> str:
    """Return a unique placeholder used until the database ID is allocated."""

    return f"TMP-{uuid4().hex}"


class ComplaintSaveService:
    """Persist one complaint, assessment, and audit batch atomically."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ComplaintRepository(session)

    def save(
        self,
        request: ComplaintSaveRequest | ComplaintCreateRequest | ComplaintData,
    ) -> Complaint:
        """Validate and persist a compatible complaint save request."""

        normalized = ComplaintSaveRequest.model_validate(request)
        return self.save_complaint(
            normalized.complaint,
            normalized.risk_assessment,
            normalized.audit_events,
            model_name=normalized.model_name,
        )

    def save_complaint(
        self,
        complaint_data: ComplaintData,
        risk_assessment: RiskAssessment | None = None,
        audit_events: Iterable[AuditEventCreate] = (),
        *,
        model_name: str | None = None,
    ) -> Complaint:
        """Create all save records in one transaction and return the reload."""

        validated_complaint = ComplaintData.model_validate(complaint_data)
        validated_assessment = (
            RiskAssessment.model_validate(risk_assessment)
            if risk_assessment is not None
            else RiskAssessment()
        )
        validated_events = [
            AuditEventCreate.model_validate(event) for event in audit_events
        ]
        complaint = Complaint(
            **validated_complaint.model_dump(mode="python"),
            complaint_number=_temporary_complaint_number(),
            severity=validated_assessment.severity,
            priority=validated_assessment.priority,
            status=ComplaintStatus.DRAFT,
        )

        try:
            self.repository.add_complaint(complaint)
            # The database-generated primary key supplies a readable,
            # collision-free sequence component while the unique constraint
            # remains the final database guard.
            complaint.complaint_number = generate_complaint_number(complaint.id)
            self.session.flush()
            self.repository.add_assessment(
                _assessment_model(complaint.id, validated_assessment, model_name)
            )

            audit_batch = self._with_required_creation_event(
                complaint.complaint_number,
                validated_events,
            )
            for event in audit_batch:
                self.repository.add_audit_log(self._audit_model(complaint.id, event))
            self.repository.add_audit_log(
                ComplaintAuditLog(
                    complaint_id=complaint.id,
                    action="COMPLAINT_SAVED",
                    field_name=None,
                    old_value=None,
                    new_value=complaint.complaint_number,
                    source=AuditSource.SYSTEM,
                )
            )
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise ComplaintPersistenceError("Unable to persist complaint.") from exc

        persisted = self.repository.get_by_id(complaint.id)
        if persisted is None:
            raise ComplaintPersistenceError(
                "Complaint was committed but could not be reloaded."
            )
        return persisted

    @staticmethod
    def _with_required_creation_event(
        complaint_number: str,
        events: list[AuditEventCreate],
    ) -> list[AuditEventCreate]:
        """Ensure legacy/direct saves still have one creation event."""

        has_creation_event = any(
            event.action in {"AI_COMPLAINT_CREATED", "COMPLAINT_CREATED"}
            for event in events
        )
        if has_creation_event:
            return events
        return [
            AuditEventCreate(
                action="COMPLAINT_CREATED",
                new_value=complaint_number,
                source="AI",
            ),
            *events,
        ]

    @staticmethod
    def _audit_model(complaint_id: int, event: AuditEventCreate) -> ComplaintAuditLog:
        """Map a validated request event to the append-only ORM model."""

        return ComplaintAuditLog(
            complaint_id=complaint_id,
            action=event.action,
            field_name=event.field_name,
            old_value=_audit_value(event.old_value),
            new_value=_audit_value(event.new_value),
            source=AuditSource(event.source.value),
        )


def save_complaint(
    session: Session,
    complaint_data: ComplaintData,
    risk_assessment: RiskAssessment | None = None,
    audit_events: Iterable[AuditEventCreate] = (),
    *,
    model_name: str | None = None,
) -> Complaint:
    """Convenience boundary for callers that prefer a function interface."""

    return ComplaintSaveService(session).save_complaint(
        complaint_data,
        risk_assessment,
        audit_events,
        model_name=model_name,
    )


__all__ = ["ComplaintSaveService", "save_complaint"]
