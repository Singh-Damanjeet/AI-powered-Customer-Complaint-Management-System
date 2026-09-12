"""Complaint persistence orchestration."""

from enum import Enum
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.ai_assessment import AIAssessment
from app.models.audit_log import ComplaintAuditLog
from app.models.complaint import Complaint
from app.models.enums import AuditSource, ComplaintStatus
from app.repositories.complaint_repository import ComplaintRepository
from app.schemas.complaint import ComplaintData, RiskAssessment
from app.schemas.persistence import (
    AIAssessmentResponse,
    ComplaintCreateRequest,
    ComplaintResponse,
)


class ComplaintNotFoundError(LookupError):
    """Raised when a requested complaint does not exist."""


class ComplaintPersistenceError(RuntimeError):
    """Raised when a complaint transaction cannot be committed."""


def generate_complaint_number() -> str:
    """Generate a collision-resistant human-readable complaint number."""

    return f"CMP-{uuid4().hex[:12].upper()}"


def _assessment_model(
    complaint_id: int,
    assessment: RiskAssessment,
    model_name: str | None,
) -> AIAssessment:
    """Map a validated risk assessment to its persistence model."""

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


def _audit_value(value: object) -> str | None:
    """Convert a scalar value to a stable audit-log representation."""

    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


class ComplaintService:
    """Coordinate complaint, assessment, and audit persistence atomically."""

    def __init__(self, session: Session) -> None:
        self.repository = ComplaintRepository(session)
        self.session = session

    def create(self, request: ComplaintCreateRequest | ComplaintData) -> Complaint:
        """Persist a complaint and its initial assessment in one transaction."""

        create_request = (
            request
            if isinstance(request, ComplaintCreateRequest)
            else ComplaintCreateRequest.model_validate(request.model_dump(mode="python"))
        )
        assessment = create_request.risk_assessment or RiskAssessment()
        complaint_values = create_request.model_dump(
            exclude={"risk_assessment", "model_name"},
            mode="python",
        )
        complaint = Complaint(
            **complaint_values,
            complaint_number=generate_complaint_number(),
            severity=assessment.severity,
            priority=assessment.priority,
            status=ComplaintStatus.DRAFT,
        )

        try:
            self.repository.add_complaint(complaint)
            self.repository.add_assessment(
                _assessment_model(complaint.id, assessment, create_request.model_name)
            )
            self.repository.add_audit_log(
                ComplaintAuditLog(
                    complaint_id=complaint.id,
                    action="CREATE",
                    field_name=None,
                    old_value=None,
                    new_value=_audit_value(complaint.complaint_number),
                    source=AuditSource.SYSTEM,
                )
            )
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ComplaintPersistenceError("Unable to persist complaint.") from exc

        persisted = self.repository.get_by_id(complaint.id)
        if persisted is None:
            raise ComplaintPersistenceError("Complaint was committed but could not be reloaded.")
        return persisted

    def get(self, complaint_id: int) -> Complaint:
        """Load one complaint or raise a domain-level not-found error."""

        complaint = self.repository.get_by_id(complaint_id)
        if complaint is None:
            raise ComplaintNotFoundError(f"Complaint {complaint_id} was not found.")
        return complaint

    def list(self, *, offset: int = 0, limit: int = 100) -> list[Complaint]:
        """Load a paginated complaint collection."""

        return self.repository.list(offset=offset, limit=limit)


def to_complaint_response(complaint: Complaint) -> ComplaintResponse:
    """Convert an ORM complaint and its latest assessment to an API response."""

    response = ComplaintResponse.model_validate(complaint, from_attributes=True)
    assessments = complaint.ai_assessments
    if assessments:
        latest = max(
            assessments,
            key=lambda assessment: (assessment.created_at, assessment.id),
        )
        response.ai_assessment = AIAssessmentResponse.model_validate(
            latest,
            from_attributes=True,
        )
    return response
