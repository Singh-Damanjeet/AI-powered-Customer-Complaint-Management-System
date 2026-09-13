"""Read/query boundary for persisted complaints."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.repositories.complaint_repository import ComplaintRepository
from app.schemas.complaint import ComplaintData
from app.schemas.persistence import (
    AIAssessmentResponse,
    ComplaintCreateRequest,
    ComplaintResponse,
)


class ComplaintNotFoundError(LookupError):
    """Raised when a requested complaint does not exist."""


class ComplaintPersistenceError(RuntimeError):
    """Raised when a complaint transaction cannot be committed."""


def generate_complaint_number(sequence: int | None = None) -> str:
    """Generate a readable number with a collision-resistant sequence part.

    The optional sequence lets the save transaction use the database-generated
    complaint ID. The UUID fallback keeps this helper useful to callers that
    need a number before an ID exists.
    """

    sequence = sequence if sequence is not None else uuid4().int % 10000
    year = datetime.now(timezone.utc).year
    return f"CMP-{year}-{sequence:04d}"


class ComplaintService:
    """Coordinate complaint, assessment, and audit persistence atomically."""

    def __init__(self, session: Session) -> None:
        self.repository = ComplaintRepository(session)
        self.session = session

    def create(self, request: ComplaintCreateRequest | ComplaintData) -> Complaint:
        """Persist via the Phase 9 transactional save service."""

        from app.services.complaint_save_service import ComplaintSaveService

        return ComplaintSaveService(self.session).save(request)

    def get(self, complaint_id: int) -> Complaint:
        """Load one complaint or raise a domain-level not-found error."""

        complaint = self.repository.get_by_id(complaint_id)
        if complaint is None:
            raise ComplaintNotFoundError(f"Complaint {complaint_id} was not found.")
        return complaint

    def list(self, *, offset: int = 0, limit: int = 100) -> list[Complaint]:
        """Load a paginated complaint collection."""

        return self.repository.list(offset=offset, limit=limit)

    def list_audit_logs(self, complaint_id: int):
        """Return chronological audit history for an existing complaint."""

        self.get(complaint_id)
        return self.repository.list_audit_logs(complaint_id)

    def list_assessments(self, complaint_id: int):
        """Return all assessment snapshots, newest first."""

        self.get(complaint_id)
        return self.repository.list_assessments(complaint_id)


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
