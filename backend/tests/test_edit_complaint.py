"""Tests for Phase 6 sparse complaint editing and reassessment."""

import asyncio
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.agents.graph import build_complaint_graph
from app.agents.router import ComplaintIntent, classify_intent_value
from app.agents.state import initial_complaint_graph_state
from app.api.ai import get_complaint_graph_service
from app.main import app
from app.schemas.complaint import ComplaintData, ComplaintPatch, RiskAssessment
from app.services.complaint_merge_service import apply_patch
from app.services.complaint_graph_service import ComplaintGraphService, ComplaintWorkflowError
from app.services.edit_complaint_service import EditComplaintService
from app.services.groq_service import GroqProviderError
from app.agents.tools.edit_complaint import EditComplaintTool
from app.services.risk_service import RiskService


def run(coroutine):
    return asyncio.run(coroutine)


class FakeStructuredAI:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def generate_structured_response(self, user_prompt, response_model, **kwargs):
        self.calls.append(
            {
                "user_prompt": user_prompt,
                "response_model": response_model,
                **kwargs,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeExtractionService:
    def __init__(self, complaint: ComplaintData) -> None:
        self.complaint = complaint

    async def extract(self, message: str) -> ComplaintData:
        return self.complaint


class FakeEditTool:
    def __init__(self, patch: ComplaintPatch | Exception) -> None:
        self.patch = patch

    async def extract_patch(self, current_complaint, user_instruction):
        if isinstance(self.patch, Exception):
            raise self.patch
        return self.patch


class RecordingRiskService(RiskService):
    def __init__(self, result: RiskAssessment) -> None:
        super().__init__()
        self.result = result
        self.calls: list[tuple[ComplaintData, str]] = []

    async def assess_risk(self, *, complaint: ComplaintData, original_text: str):
        self.calls.append((complaint, original_text))
        return self.result


def current_complaint() -> ComplaintData:
    return ComplaintData(
        complaint_source="Email",
        customer_name="ABC Pharma",
        complainant_name="Jane Doe",
        complainant_contact="jane@example.com",
        product_type="FDF",
        product_name="Metformin",
        product_strength_grade="500 mg",
        batch_lot_number="MT24003",
        manufacturing_date=date(2025, 1, 15),
        expiry_date=date(2028, 6, 30),
        quantity_affected=120,
        quantity_unit="tablets",
        complaint_type="Discoloration",
        complaint_date=date(2026, 1, 10),
        received_date=date(2026, 1, 11),
        detailed_description="Brown discoloration reported.",
    )


def risk_assessment() -> RiskAssessment:
    return RiskAssessment(
        severity="Major",
        priority="High",
        rationale="The updated complaint requires QA review.",
        recommended_actions=["Review retained samples"],
        qa_investigation_required=True,
        product_replacement_recommended=False,
    )


def test_edit_tool_returns_only_grounded_sparse_fields() -> None:
    ai = FakeStructuredAI(
        [
            {
                "batch_lot_number": "MT24004",
                "quantity_affected": 80,
                "customer_name": "ABC Pharma",
            }
        ]
    )
    patch = run(
        EditComplaintTool(ai).extract_patch(
            current_complaint(),
            "Change batch to MT24004 and quantity to 80.",
        )
    )

    assert patch.model_fields_set == {"batch_lot_number", "quantity_affected"}
    assert patch.batch_lot_number == "MT24004"
    assert patch.quantity_affected == Decimal("80")
    assert "ComplaintPatch" in ai.calls[0]["system_prompt"]
    assert ai.calls[0]["response_model"] is ComplaintPatch


def test_explicit_null_is_preserved_but_omitted_nulls_are_dropped() -> None:
    ai = FakeStructuredAI(
        [{"expiry_date": None, "customer_name": None, "product_name": None}]
    )

    patch = run(
        EditComplaintTool(ai).extract_patch(
            current_complaint(),
            "Remove the expiry date because it was not provided.",
        )
    )

    assert patch.model_fields_set == {"expiry_date"}
    assert patch.as_update_dict() == {"expiry_date": None}


def test_ambiguous_replacement_does_not_create_a_factual_value() -> None:
    ai = FakeStructuredAI([{"batch_lot_number": "whatever"}])

    patch = run(
        EditComplaintTool(ai).extract_patch(
            current_complaint(),
            "Change the batch to whatever you think is best.",
        )
    )

    assert patch.model_fields_set == set()
    assert patch.as_update_dict() == {}


def test_apply_patch_preserves_omitted_fields_and_supports_explicit_clear() -> None:
    original = current_complaint()
    updated, changed_fields = apply_patch(
        original,
        ComplaintPatch(quantity_affected=500),
    )

    assert updated.quantity_affected == Decimal("500")
    assert updated.batch_lot_number == original.batch_lot_number
    assert updated.expiry_date == original.expiry_date
    assert changed_fields == ["quantity_affected"]

    cleared, clear_fields = apply_patch(
        original,
        ComplaintPatch(expiry_date=None),
    )
    assert cleared.expiry_date is None
    assert clear_fields == ["expiry_date"]


def test_no_op_patch_has_no_changed_fields() -> None:
    updated, changed_fields = apply_patch(
        current_complaint(),
        ComplaintPatch(quantity_affected=120),
    )

    assert updated.quantity_affected == Decimal("120")
    assert changed_fields == []


def test_description_addition_preserves_existing_context() -> None:
    service = EditComplaintService(
        edit_tool=FakeEditTool(
            ComplaintPatch(detailed_description="Several tablets were cracked.")
        )
    )

    updated, changed_fields = run(
        service.process(
            current_complaint(),
            "Also mention that several tablets were cracked.",
        )
    )

    assert updated.detailed_description == (
        "Brown discoloration reported. Several tablets were cracked."
    )
    assert changed_fields == ["detailed_description"]


def test_edit_intent_uses_current_complaint_context() -> None:
    existing = current_complaint().model_dump(mode="json")

    assert classify_intent_value(
        "Actually quantity is 75.", current_complaint=existing
    ) is ComplaintIntent.EDIT_COMPLAINT
    assert classify_intent_value(
        "One patient also experienced severe vomiting.",
        current_complaint=existing,
    ) is ComplaintIntent.EDIT_COMPLAINT
    assert classify_intent_value(
        "Log a new complaint for another customer.", current_complaint=existing
    ) is ComplaintIntent.LOG_COMPLAINT


def test_edit_graph_converges_on_validation_and_always_reassesses_risk() -> None:
    original = current_complaint()
    edit_service = EditComplaintService(
        edit_tool=FakeEditTool(ComplaintPatch(quantity_affected=500))
    )
    risk_service = RecordingRiskService(risk_assessment())
    graph = build_complaint_graph(
        edit_service=edit_service,
        risk_service=risk_service,
    )

    result = run(
        graph.ainvoke(
            initial_complaint_graph_state(
                "Change quantity to 500.",
                complaint=original.model_dump(mode="json"),
            )
        )
    )

    assert result["intent"] == ComplaintIntent.EDIT_COMPLAINT.value
    assert result["workflow_status"] == "COMPLETED"
    assert result["complaint"]["quantity_affected"] == "500"
    assert result["complaint"]["batch_lot_number"] == "MT24003"
    assert result["complaint_patch"] == {"quantity_affected": "500"}
    assert result["changed_fields"] == ["quantity_affected"]
    assert "updated the affected quantity" in result["assistant_message"]
    assert len(risk_service.calls) == 1


def test_edit_graph_preserves_all_unrelated_populated_fields() -> None:
    original = current_complaint()
    graph = build_complaint_graph(
        edit_service=EditComplaintService(
            edit_tool=FakeEditTool(ComplaintPatch(batch_lot_number="MT24004"))
        ),
        risk_service=RecordingRiskService(risk_assessment()),
    )
    result = run(
        graph.ainvoke(
            initial_complaint_graph_state(
                "Change the batch to MT24004.",
                complaint=original.model_dump(mode="json"),
            )
        )
    )
    updated = ComplaintData.model_validate(result["complaint"])

    for field_name in ComplaintData.model_fields:
        if field_name != "batch_lot_number":
            assert getattr(updated, field_name) == getattr(original, field_name)
    assert updated.batch_lot_number == "MT24004"


def test_risk_sensitive_edit_reassesses_updated_description() -> None:
    original = current_complaint().model_copy(
        update={"detailed_description": "No adverse events reported."}
    )
    ai = FakeStructuredAI([risk_assessment()])
    risk_service = RiskService(ai)
    edit_service = EditComplaintService(
        edit_tool=FakeEditTool(
            ComplaintPatch(
                detailed_description="One patient experienced severe vomiting."
            )
        )
    )
    graph = build_complaint_graph(edit_service=edit_service, risk_service=risk_service)

    result = run(
        graph.ainvoke(
            initial_complaint_graph_state(
                "Actually one patient experienced severe vomiting.",
                complaint=original.model_dump(mode="json"),
            )
        )
    )

    assert result["complaint"]["detailed_description"] == (
        "One patient experienced severe vomiting."
    )
    assert '"adverse_event_signal": true' in ai.calls[0]["user_prompt"]
    assert '"serious_health_signal": true' in ai.calls[0]["user_prompt"]


def test_ambiguous_edit_returns_clear_message_and_refreshes_risk() -> None:
    original = current_complaint()
    risk_service = RecordingRiskService(risk_assessment())
    graph = build_complaint_graph(
        edit_service=EditComplaintService(edit_tool=FakeEditTool(ComplaintPatch())),
        risk_service=risk_service,
    )
    result = run(
        graph.ainvoke(
            initial_complaint_graph_state(
                "Change the batch to a better one.",
                complaint=original.model_dump(mode="json"),
            )
        )
    )

    assert result["complaint"] == original.model_dump(mode="json")
    assert result["changed_fields"] == []
    assert "batch number" in result["assistant_message"]
    assert "no replacement value" in result["assistant_message"]
    assert len(risk_service.calls) == 1


def test_edit_failure_preserves_original_state_and_skips_risk() -> None:
    original = current_complaint()
    risk_service = RecordingRiskService(risk_assessment())
    graph = build_complaint_graph(
        edit_service=EditComplaintService(
            edit_tool=FakeEditTool(GroqProviderError("provider unavailable"))
        ),
        risk_service=risk_service,
    )

    result = run(
        graph.ainvoke(
            initial_complaint_graph_state(
                "Change quantity to 500.",
                complaint=original.model_dump(mode="json"),
            )
        )
    )

    assert result["workflow_status"] == "ERROR"
    assert result["complaint"] == original.model_dump(mode="json")
    assert result["changed_fields"] == []
    assert risk_service.calls == []

    with pytest.raises(ComplaintWorkflowError, match="AI service is unavailable"):
        run(
            ComplaintGraphService(graph=graph).run(
                "Change quantity to 500.",
                current_complaint=original,
            )
        )


def test_agent_message_endpoint_supports_edit_without_database_write() -> None:
    original = current_complaint()
    graph = build_complaint_graph(
        edit_service=EditComplaintService(
            edit_tool=FakeEditTool(ComplaintPatch(quantity_affected=500))
        ),
        risk_service=RecordingRiskService(risk_assessment()),
    )
    app.dependency_overrides[get_complaint_graph_service] = lambda: ComplaintGraphService(
        graph=graph
    )
    try:
        result = TestClient(app).post(
            "/api/agent/message",
            json={
                "message": "Update quantity to 500.",
                "complaint": original.model_dump(mode="json"),
            },
        )
    finally:
        app.dependency_overrides.pop(get_complaint_graph_service, None)

    assert result.status_code == 200
    assert result.json()["complaint"]["quantity_affected"] == "500"
    assert result.json()["changed_fields"] == ["quantity_affected"]


def test_agent_message_endpoint_keeps_new_complaint_logging() -> None:
    extraction = FakeExtractionService(current_complaint())
    graph = build_complaint_graph(
        extraction_service=extraction,
        risk_service=RecordingRiskService(risk_assessment()),
    )
    app.dependency_overrides[get_complaint_graph_service] = lambda: ComplaintGraphService(
        graph=graph
    )
    try:
        result = TestClient(app).post(
            "/api/agent/message",
            json={"message": "Log a new complaint for ABC Pharma."},
        )
    finally:
        app.dependency_overrides.pop(get_complaint_graph_service, None)

    assert result.status_code == 200
    assert result.json()["complaint"]["product_name"] == "Metformin"
    assert result.json()["changed_fields"] == []
