"""Tests for the Phase 5 complaint LangGraph orchestration."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.api.ai import get_log_complaint_service
from app.agents.graph import build_complaint_graph
from app.agents.router import ComplaintIntent, classify_intent_value, route_by_intent
from app.agents.state import (
    ComplaintGraphState,
    initial_complaint_graph_state,
)
from app.main import app
from app.schemas.complaint import ComplaintData, RiskAssessment
from app.services.complaint_graph_service import (
    ComplaintGraphService,
    ComplaintWorkflowError,
    UnsupportedComplaintIntentError,
)
from app.services.groq_service import GroqProviderError
from app.services.log_complaint_service import LogComplaintService


def run(coroutine):
    return asyncio.run(coroutine)


class FakeExtractionService:
    def __init__(self, result) -> None:
        self.result = result
        self.messages: list[str] = []

    async def extract(self, message: str):
        self.messages.append(message)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeRiskService:
    def __init__(self, result) -> None:
        self.result = result
        self.complaints: list[ComplaintData] = []

    async def assess_risk(self, *, complaint: ComplaintData, original_text: str):
        self.complaints.append(complaint)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def extracted_complaint() -> ComplaintData:
    return ComplaintData(
        customer_name="ABC Pharma",
        product_name="Metformin",
        product_strength_grade="500 mg",
        batch_lot_number="MT24003",
        quantity_affected=120,
        quantity_unit="tablets",
        complaint_type="Discoloration",
        detailed_description="Brown discoloration was reported on tablets.",
    )


def assessed_risk() -> RiskAssessment:
    return RiskAssessment(
        severity="Major",
        priority="High",
        rationale="The reported quality defect requires QA review.",
        recommended_actions=["Review retained samples"],
        qa_investigation_required=True,
        product_replacement_recommended=False,
    )


def test_initial_graph_state_has_safe_defaults_and_no_dependencies() -> None:
    state = initial_complaint_graph_state("A complaint was reported.")

    assert state["user_message"] == "A complaint was reported."
    assert state["errors"] == []
    assert state["changed_fields"] == []
    assert "complaint" not in state
    assert "risk_assessment" not in state
    assert "document_text" not in state

    typed_state: ComplaintGraphState = initial_complaint_graph_state(
        "Document complaint", document_text="complaint text"
    )
    assert typed_state["document_text"] == "complaint text"


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Log a complaint for damaged tablets", ComplaintIntent.LOG_COMPLAINT),
        ("Customer ABC reported discoloration", ComplaintIntent.LOG_COMPLAINT),
        ("Change batch number to X", ComplaintIntent.EDIT_COMPLAINT),
        ("Actually quantity is 500", ComplaintIntent.EDIT_COMPLAINT),
        ("Please tell me a joke", ComplaintIntent.UNKNOWN),
    ],
)
def test_intent_classification_is_deterministic(message: str, expected: ComplaintIntent) -> None:
    assert classify_intent_value(message) is expected


def test_document_context_routes_to_document_placeholder() -> None:
    state = initial_complaint_graph_state(
        "Process this complaint", document_text="Complaint from an email"
    )
    state["intent"] = classify_intent_value(
        state["user_message"], document_text=state["document_text"]
    ).value

    assert state["intent"] == ComplaintIntent.DOCUMENT_COMPLAINT.value
    assert route_by_intent(state) == "unsupported_for_now"


def test_complete_log_graph_runs_extraction_validation_risk_and_response() -> None:
    extraction = FakeExtractionService(extracted_complaint())
    risk = FakeRiskService(assessed_risk())
    graph = build_complaint_graph(extraction_service=extraction, risk_service=risk)

    result = run(
        graph.ainvoke(
            initial_complaint_graph_state(
                "ABC Pharma reported brown discoloration on 120 Metformin "
                "500 mg tablets from batch MT24003."
            )
        )
    )

    assert result["intent"] == ComplaintIntent.LOG_COMPLAINT.value
    assert result["workflow_status"] == "COMPLETED"
    assert result["complaint"]["customer_name"] == "ABC Pharma"
    assert result["risk_assessment"]["severity"] == "Major"
    assert "preliminary assessment is Major severity with High priority" in result[
        "assistant_message"
    ]
    assert result["changed_fields"] == []
    assert extraction.messages
    assert len(risk.complaints) == 1


def test_graph_service_returns_agent_response_without_persistence() -> None:
    graph = build_complaint_graph(
        extraction_service=FakeExtractionService(extracted_complaint()),
        risk_service=FakeRiskService(assessed_risk()),
    )
    response = run(
        ComplaintGraphService(graph=graph).run(
            "Customer ABC reported brown discoloration."
        )
    )

    assert response.complaint.product_name == "Metformin"
    assert response.risk_assessment.severity == "Major"
    assert response.changed_fields == []


def test_existing_api_executes_normal_requests_through_langgraph() -> None:
    extraction = FakeExtractionService(extracted_complaint())
    risk = FakeRiskService(assessed_risk())
    service = LogComplaintService(
        extraction_service=extraction,
        risk_service=risk,
    )
    app.dependency_overrides[get_log_complaint_service] = lambda: service
    client = TestClient(app)
    try:
        result = client.post(
            "/api/ai/log-complaint",
            json={"message": "Customer ABC reported brown discoloration."},
        )
    finally:
        app.dependency_overrides.pop(get_log_complaint_service, None)

    assert result.status_code == 200
    assert result.json()["complaint"]["product_name"] == "Metformin"
    assert result.json()["risk_assessment"]["priority"] == "High"
    assert extraction.messages == ["Customer ABC reported brown discoloration."]
    assert len(risk.complaints) == 1


def test_edit_and_unknown_requests_do_not_enter_log_workflow() -> None:
    extraction = FakeExtractionService(extracted_complaint())
    risk = FakeRiskService(assessed_risk())
    graph = build_complaint_graph(extraction_service=extraction, risk_service=risk)

    edit_result = run(
        graph.ainvoke(initial_complaint_graph_state("Change batch number to X"))
    )
    unknown_result = run(
        graph.ainvoke(initial_complaint_graph_state("Please tell me a joke"))
    )

    assert edit_result["workflow_status"] == "UNSUPPORTED"
    assert edit_result["assistant_message"] == (
        "Editing is not available in the current workflow yet."
    )
    assert unknown_result["workflow_status"] == "UNSUPPORTED"
    assert extraction.messages == []
    assert risk.complaints == []


def test_extraction_failure_stops_before_risk_node() -> None:
    extraction = FakeExtractionService(GroqProviderError("provider unavailable"))
    risk = FakeRiskService(assessed_risk())
    graph = build_complaint_graph(extraction_service=extraction, risk_service=risk)

    result = run(
        graph.ainvoke(initial_complaint_graph_state("Customer reported a complaint."))
    )

    assert result["workflow_status"] == "ERROR"
    assert result["error_code"] == "AI_UNAVAILABLE"
    assert risk.complaints == []

    with pytest.raises(ComplaintWorkflowError, match="AI service is unavailable"):
        run(
            ComplaintGraphService(graph=graph).run(
                "Customer reported a complaint."
            )
        )


def test_invalid_extracted_state_is_caught_by_validation_node() -> None:
    extraction = FakeExtractionService({"unexpected": "value"})
    risk = FakeRiskService(assessed_risk())
    graph = build_complaint_graph(extraction_service=extraction, risk_service=risk)

    result = run(
        graph.ainvoke(initial_complaint_graph_state("Customer reported a complaint."))
    )

    assert result["workflow_status"] == "ERROR"
    assert result["error_code"] == "INVALID_COMPLAINT"
    assert risk.complaints == []


def test_risk_failure_preserves_validated_complaint() -> None:
    extraction = FakeExtractionService(extracted_complaint())
    risk = FakeRiskService(GroqProviderError("provider unavailable"))
    graph = build_complaint_graph(extraction_service=extraction, risk_service=risk)

    result = run(
        graph.ainvoke(initial_complaint_graph_state("Customer reported a complaint."))
    )

    assert result["workflow_status"] == "ERROR"
    assert result["error_code"] == "AI_UNAVAILABLE"
    assert result["complaint"]["product_name"] == "Metformin"
    assert "risk_assessment" not in result


def test_hallucination_protection_is_preserved_by_graph() -> None:
    complaint = ComplaintData(detailed_description="Customer reported cracked tablets.")
    graph = build_complaint_graph(
        extraction_service=FakeExtractionService(complaint),
        risk_service=FakeRiskService(assessed_risk()),
    )

    result = run(
        graph.ainvoke(initial_complaint_graph_state("Customer reported cracked tablets."))
    )

    assert result["complaint"]["customer_name"] is None
    assert result["complaint"]["product_name"] is None
    assert result["complaint"]["batch_lot_number"] is None
    assert result["complaint"]["detailed_description"] == (
        "Customer reported cracked tablets."
    )


def test_graph_service_exposes_clean_unsupported_error() -> None:
    graph = build_complaint_graph(
        extraction_service=FakeExtractionService(extracted_complaint()),
        risk_service=FakeRiskService(assessed_risk()),
    )

    with pytest.raises(
        UnsupportedComplaintIntentError,
        match="Editing is not available",
    ):
        run(ComplaintGraphService(graph=graph).run("Change batch number to X"))
