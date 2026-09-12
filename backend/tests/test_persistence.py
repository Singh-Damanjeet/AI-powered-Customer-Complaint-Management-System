from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models import AIAssessment, Complaint, ComplaintAuditLog
from app.models.enums import AuditSource, ComplaintStatus
from app.repositories.complaint_repository import ComplaintRepository
from app.schemas.complaint import Priority, ProductType, Severity
from app.schemas.persistence import ComplaintCreateRequest
from app.services.complaint_service import ComplaintService, to_complaint_response


def build_engine(database_url: str = "sqlite://"):
    """Build a SQLite engine suitable for isolated repository tests."""

    return create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool if database_url == "sqlite://" else None,
    )


@pytest.fixture
def session() -> Session:
    engine = build_engine()
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    database = session_factory()
    try:
        yield database
    finally:
        database.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def sample_request() -> ComplaintCreateRequest:
    return ComplaintCreateRequest(
        complaint_source="Customer email",
        customer_name="Acme Pharma",
        complainant_name="Asha Rao",
        complainant_contact="asha.rao@example.com",
        product_type=ProductType.API,
        product_name="Example API",
        product_strength_grade="USP Grade",
        batch_lot_number="B-2026-001",
        manufacturing_date=date(2026, 1, 10),
        expiry_date=date(2028, 1, 9),
        quantity_affected="12.5",
        quantity_unit="kg",
        complaint_type="Foreign particles",
        complaint_date=date(2026, 2, 1),
        received_date=date(2026, 2, 2),
        detailed_description="Customer reported visible particles in the material.",
    )


def test_repository_persists_and_loads_related_records(session: Session) -> None:
    repository = ComplaintRepository(session)
    complaint = Complaint(
        complaint_number="CMP-REPOSITORY-001",
        status=ComplaintStatus.DRAFT,
        severity=Severity.UNKNOWN,
        priority=Priority.UNKNOWN,
    )
    repository.add_complaint(complaint)
    repository.add_assessment(
        AIAssessment(
            complaint_id=complaint.id,
            severity=Severity.MAJOR,
            priority=Priority.HIGH,
            rationale="Quality impact is possible.",
            recommended_actions=["Open QA investigation"],
            qa_investigation_required=True,
            product_replacement_recommended=False,
            model_name="test-model",
        )
    )
    repository.add_audit_log(
        ComplaintAuditLog(
            complaint_id=complaint.id,
            action="CREATE",
            source=AuditSource.SYSTEM,
            new_value=complaint.complaint_number,
        )
    )
    session.commit()

    loaded = repository.get_by_id(complaint.id)

    assert loaded is not None
    assert loaded.complaint_number == "CMP-REPOSITORY-001"
    assert len(loaded.ai_assessments) == 1
    assert loaded.ai_assessments[0].model_name == "test-model"
    assert loaded.audit_logs[0].source is AuditSource.SYSTEM


def test_service_commits_complaint_assessment_and_audit_atomically(session: Session) -> None:
    request = sample_request()
    request.risk_assessment = {
        "severity": "Major",
        "priority": "High",
        "rationale": "The reported issue may affect product quality.",
        "recommended_actions": ["Open QA investigation"],
        "qa_investigation_required": True,
        "product_replacement_recommended": False,
    }
    request.model_name = "test-model"

    created = ComplaintService(session).create(request)
    response = to_complaint_response(created)

    assert created.id is not None
    assert created.complaint_number.startswith("CMP-")
    assert created.status is ComplaintStatus.DRAFT
    assert created.severity is Severity.MAJOR
    assert response.ai_assessment is not None
    assert response.ai_assessment.priority is Priority.HIGH
    assert response.ai_assessment.model_name == "test-model"
    assert session.scalar(
        select(ComplaintAuditLog).where(ComplaintAuditLog.complaint_id == created.id)
    ) is not None


def test_committed_complaint_survives_new_session(tmp_path) -> None:
    database_path = tmp_path / "complaints.db"
    engine = build_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    first_session = session_factory()
    created = ComplaintService(first_session).create(sample_request())
    complaint_id = created.id
    first_session.close()
    engine.dispose()

    restarted_engine = build_engine(f"sqlite:///{database_path}")
    second_session = sessionmaker(bind=restarted_engine)()
    try:
        reloaded = ComplaintService(second_session).get(complaint_id)
        response = to_complaint_response(reloaded)

        assert response.id == complaint_id
        assert response.customer_name == "Acme Pharma"
        assert response.ai_assessment is not None
        assert response.ai_assessment.model_name == "not_assessed"
    finally:
        second_session.close()
        Base.metadata.drop_all(restarted_engine)
        restarted_engine.dispose()


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


def test_complaint_api_create_get_and_list(api_client: TestClient) -> None:
    payload = sample_request().model_dump(mode="json")

    create_response = api_client.post("/api/complaints", json=payload)

    assert create_response.status_code == 201
    created = create_response.json()
    complaint_id = created["id"]
    assert created["status"] == "DRAFT"
    assert created["ai_assessment"]["severity"] == "Unknown"

    get_response = api_client.get(f"/api/complaints/{complaint_id}")
    list_response = api_client.get("/api/complaints")

    assert get_response.status_code == 200
    assert get_response.json()["complaint_number"] == created["complaint_number"]
    assert get_response.json()["ai_assessment"]["model_name"] == "not_assessed"
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_complaint_api_returns_not_found(api_client: TestClient) -> None:
    response = api_client.get("/api/complaints/999")

    assert response.status_code == 404
