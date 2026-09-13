"""Database access methods for complaints and related records."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.ai_assessment import AIAssessment
from app.models.audit_log import ComplaintAuditLog
from app.models.complaint import Complaint


class ComplaintRepository:
    """Repository that keeps SQLAlchemy operations out of API handlers."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add_complaint(self, complaint: Complaint) -> Complaint:
        """Stage a complaint and flush it to obtain its database ID."""

        self.session.add(complaint)
        self.session.flush()
        return complaint

    def add_assessment(self, assessment: AIAssessment) -> AIAssessment:
        """Stage an assessment snapshot."""

        self.session.add(assessment)
        self.session.flush()
        return assessment

    def add_audit_log(self, audit_log: ComplaintAuditLog) -> ComplaintAuditLog:
        """Stage an audit event."""

        self.session.add(audit_log)
        self.session.flush()
        return audit_log

    def get_by_id(self, complaint_id: int) -> Complaint | None:
        """Return one complaint with its related records loaded."""

        statement = (
            select(Complaint)
            .where(Complaint.id == complaint_id)
            .options(
                selectinload(Complaint.ai_assessments),
                selectinload(Complaint.audit_logs),
            )
        )
        return self.session.scalar(statement)

    def list(self, *, offset: int = 0, limit: int = 100) -> list[Complaint]:
        """Return complaints ordered from newest to oldest."""

        statement = (
            select(Complaint)
            .order_by(Complaint.created_at.desc(), Complaint.id.desc())
            .offset(offset)
            .limit(limit)
            .options(selectinload(Complaint.ai_assessments))
        )
        return list(self.session.scalars(statement).all())

    def get_latest_assessment(self, complaint_id: int) -> AIAssessment | None:
        """Return the most recently stored assessment for a complaint."""

        statement = (
            select(AIAssessment)
            .where(AIAssessment.complaint_id == complaint_id)
            .order_by(AIAssessment.created_at.desc(), AIAssessment.id.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def list_audit_logs(self, complaint_id: int) -> list[ComplaintAuditLog]:
        """Return immutable audit events in chronological order."""

        statement = (
            select(ComplaintAuditLog)
            .where(ComplaintAuditLog.complaint_id == complaint_id)
            .order_by(ComplaintAuditLog.created_at.asc(), ComplaintAuditLog.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def list_assessments(self, complaint_id: int) -> list[AIAssessment]:
        """Return all assessment snapshots, newest first."""

        statement = (
            select(AIAssessment)
            .where(AIAssessment.complaint_id == complaint_id)
            .order_by(AIAssessment.created_at.desc(), AIAssessment.id.desc())
        )
        return list(self.session.scalars(statement).all())
