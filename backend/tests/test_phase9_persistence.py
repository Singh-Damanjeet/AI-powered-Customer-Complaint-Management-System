"""Phase 9 save, audit-history, and assessment-history tests."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models import AIAssessment, Complaint, ComplaintAuditLog
from app.models.enums import AuditSource
from app.repositories.complaint_repository import ComplaintRepository
from app.schemas.complaint import ComplaintData, RiskAssessment
from app.schemas.persistence import (
    AuditEventCreate,
    ComplaintSaveRequest,
)
from app.services.complaint_save_service import ComplaintSaveService
from app.services.complaint_service import ComplaintPersistenceError


def build_engine():
    """Build a disposable SQLite engine for transaction tests."""

    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def session() -> Session:
    engine = build_engine()
    Base.metadata.create_all(engine)
    database = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield database
    finally:
        database.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def complaint_data() -> ComplaintData:
    return ComplaintData(
        complaint_source="Customer email",
        customer_name="ABC Pharma",
        product_type="API",
        product_name="Metformin API",
        product_strength_grade="USP",
        batch_lot_number="MT24003",
        manufacturing_date=date(2026, 1, 10),
        expiry_date=date(2028, 1, 9),
        quantity_affected=120,
        quantity_unit="kg",
        complaint_type="Discoloration",
        complaint_date=date(2026, 2, 1),
        detailed_description="Brown discoloration was reported.",
    )


def risk() -> RiskAssessment:
    return RiskAssessment(
        severity="Major",
        priority="High",
        rationale="Potential product quality impact.",
        recommended_actions=["Initiate QA investigation"],
        qa_investigation_required=True,
        product_replacement_recommended=False,
    )


def save_request() -> ComplaintSaveRequest:
    return ComplaintSaveRequest(
        complaint=complaint_data(),
        risk_assessment=risk(),
        audit_events=[
            AuditEventCreate(
                action="AI_EDITED_FIELD",
                field_name="quantity_affected",
                old_value=120,
                new_value=500,
                source=AuditSource.AI,
            ),
            AuditEventCreate(
                action="DOCUMENT_EXTRACTED",
                new_value="complaint.pdf",
                source=AuditSource.AI,
            ),
        ],
        model_name="phase9-test-model",
    )


def test_save_creates_complaint_assessment_and_ordered_audit_batch(
    session: Session,
) -> None:
    saved = ComplaintSaveService(session).save(save_request())

    assert saved.id is not None
    assert saved.complaint_number.startswith("CMP-")
    assert saved.complaint_number.split("-")[-1].isdigit()
    assert saved.severity.value == "Major"
    assert saved.priority.value == "High"

    events = ComplaintRepository(session).list_audit_logs(saved.id)
    assert [event.action for event in events] == [
        "COMPLAINT_CREATED",
        "AI_EDITED_FIELD",
        "DOCUMENT_EXTRACTED",
        "COMPLAINT_SAVED",
    ]
    assert all(event.complaint_id == saved.id for event in events)
    assert events[1].old_value == "120"
    assert events[1].new_value == "500"
    assert events[0].source is AuditSource.AI
    assert events[-1].source is AuditSource.SYSTEM

    assessments = ComplaintRepository(session).list_assessments(saved.id)
    assert len(assessments) == 1
    assert assessments[0].model_name == "phase9-test-model"


def test_each_save_gets_a_distinct_readable_complaint_number(session: Session) -> None:
    first = ComplaintSaveService(session).save(save_request())
    second = ComplaintSaveService(session).save(save_request())

    assert first.complaint_number != second.complaint_number
    assert first.complaint_number.startswith("CMP-")
    assert second.complaint_number.startswith("CMP-")


@pytest.mark.parametrize("failure_target", ["assessment", "audit"])
def test_save_rolls_back_complaint_and_related_rows_on_failure(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
    failure_target: str,
) -> None:
    if failure_target == "assessment":
        def fail_assessment(self, assessment):
            raise RuntimeError("assessment write failed")

        monkeypatch.setattr(ComplaintRepository, "add_assessment", fail_assessment)
    else:
        original_add_audit = ComplaintRepository.add_audit_log

        def fail_audit(self, audit_log):
            if audit_log.action == "DOCUMENT_EXTRACTED":
                raise RuntimeError("audit write failed")
            return original_add_audit(self, audit_log)

        monkeypatch.setattr(ComplaintRepository, "add_audit_log", fail_audit)

    with pytest.raises(ComplaintPersistenceError):
        ComplaintSaveService(session).save(save_request())

    assert session.scalar(select(func.count()).select_from(Complaint)) == 0
    assert session.scalar(select(func.count()).select_from(AIAssessment)) == 0
    assert session.scalar(select(func.count()).select_from(ComplaintAuditLog)) == 0


def test_repository_preserves_multiple_assessment_snapshots(session: Session) -> None:
    saved = ComplaintSaveService(session).save(save_request())
    repository = ComplaintRepository(session)
    repository.add_assessment(
        AIAssessment(
            complaint_id=saved.id,
            severity="Critical",
            priority="High",
            rationale="A later reassessment identified a critical signal.",
            recommended_actions=["Escalate to QA"],
            qa_investigation_required=True,
            product_replacement_recommended=True,
            model_name="phase9-follow-up-model",
        )
    )
    session.commit()

    assessments = repository.list_assessments(saved.id)

    assert len(assessments) == 2
    assert {assessment.model_name for assessment in assessments} == {
        "phase9-test-model",
        "phase9-follow-up-model",
    }


@pytest.fixture
def api_client():
    engine = build_engine()
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database():
        database = session_factory()
        try:
            yield database
        finally:
            database.close()

    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_history_endpoints_return_only_the_selected_complaint(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/complaints",
        json=save_request().model_dump(mode="json"),
    )
    assert response.status_code == 201
    complaint_id = response.json()["id"]

    audit_response = api_client.get(f"/api/complaints/{complaint_id}/audit")
    assessments_response = api_client.get(
        f"/api/complaints/{complaint_id}/assessments"
    )
    missing_audit_response = api_client.get("/api/complaints/999/audit")

    assert audit_response.status_code == 200
    audit_items = audit_response.json()["items"]
    assert [item["action"] for item in audit_items] == [
        "COMPLAINT_CREATED",
        "AI_EDITED_FIELD",
        "DOCUMENT_EXTRACTED",
        "COMPLAINT_SAVED",
    ]
    assert assessments_response.status_code == 200
    assert len(assessments_response.json()) == 1
    assert assessments_response.json()[0]["model_name"] == "phase9-test-model"
    assert missing_audit_response.status_code == 404
