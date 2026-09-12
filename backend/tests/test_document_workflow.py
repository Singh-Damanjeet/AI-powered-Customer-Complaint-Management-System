"""Tests for document intake, graph orchestration, and document-to-edit flow."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.agents.graph import build_complaint_graph
from app.agents.state import initial_complaint_graph_state
from app.api.ai import get_complaint_graph_service
from app.main import app
from app.schemas.complaint import ComplaintData, ComplaintPatch, RiskAssessment
from app.services.complaint_extraction_service import ComplaintExtractionService
from app.services.complaint_graph_service import ComplaintGraphService
from app.services.document_complaint_service import DocumentComplaintService
from app.services.document_parser import DocumentParserService
from app.services.edit_complaint_service import EditComplaintService
from app.services.risk_service import RiskService


def run(coroutine):
    return asyncio.run(coroutine)


class FakeDocumentParser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[tuple[str, bytes]] = []

    async def parse(self, filename: str, content: bytes) -> str:
        self.calls.append((filename, content))
        return self.text


class FakeExtractionService:
    def __init__(self, complaint: ComplaintData) -> None:
        self.complaint = complaint
        self.calls: list[str] = []

    async def extract(self, text: str) -> ComplaintData:
        self.calls.append(text)
        return self.complaint


class FakeEditTool:
    def __init__(self, patch: ComplaintPatch) -> None:
        self.patch = patch

    async def extract_patch(self, current_complaint, user_instruction):
        return self.patch


class RecordingRiskService(RiskService):
    def __init__(self, result: RiskAssessment) -> None:
        super().__init__()
        self.result = result
        self.calls: list[tuple[ComplaintData, str]] = []

    async def assess_risk(self, *, complaint: ComplaintData, original_text: str):
        self.calls.append((complaint, original_text))
        return self.result


class FakeStructuredAI:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)

    def generate_structured_response(self, user_prompt, response_model, **kwargs):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def complaint() -> ComplaintData:
    return ComplaintData(
        complaint_source="Email",
        customer_name="ABC Pharma",
        product_name="Metformin",
        product_strength_grade="500 mg",
        batch_lot_number="MT24003",
        quantity_affected=120,
        quantity_unit="tablets",
        complaint_type="Discoloration",
        detailed_description="Brown discoloration was observed on tablets.",
    )


def assessment() -> RiskAssessment:
    return RiskAssessment(
        severity="Major",
        priority="High",
        rationale="The reported defect requires QA review.",
        recommended_actions=["Review retained samples"],
        qa_investigation_required=True,
        product_replacement_recommended=False,
    )


def test_document_complaint_service_reuses_parser_and_extraction_service() -> None:
    parser = FakeDocumentParser("ABC Pharma reported a complaint.")
    extraction = FakeExtractionService(complaint())
    service = DocumentComplaintService(parser=parser, extraction_service=extraction)

    document_text, extracted = run(service.process("complaint.txt", b"source"))

    assert document_text == "ABC Pharma reported a complaint."
    assert extracted == complaint()
    assert parser.calls == [("complaint.txt", b"source")]
    assert extraction.calls == [document_text]


def test_document_graph_parses_extracts_validates_and_assesses_risk() -> None:
    document_text = (
        "ABC Pharma reported brown discoloration on 120 Metformin 500 mg tablets "
        "from batch MT24003."
    )
    parser = FakeDocumentParser(document_text)
    extraction = FakeExtractionService(complaint())
    risk = RecordingRiskService(assessment())
    graph = build_complaint_graph(
        document_parser_service=parser,
        extraction_service=extraction,
        risk_service=risk,
    )

    result = run(
        graph.ainvoke(
            initial_complaint_graph_state(
                "Process uploaded complaint document",
                document_filename="complaint.txt",
                document_content=b"document bytes",
            )
        )
    )

    assert result["intent"] == "DOCUMENT_COMPLAINT"
    assert result["workflow_status"] == "COMPLETED"
    assert result["document_text"] == document_text
    assert result["document_content"] is None
    assert result["complaint"]["customer_name"] == "ABC Pharma"
    assert result["risk_assessment"]["severity"] == "Major"
    assert result["changed_fields"] == []
    assert "uploaded document" in result["assistant_message"]
    assert parser.calls == [("complaint.txt", b"document bytes")]
    assert extraction.calls == [document_text]
    assert risk.calls == [(complaint(), document_text)]


def test_document_extraction_keeps_unsupported_facts_null() -> None:
    text = "Customer reported cracked tablets."
    extracted_by_ai = ComplaintData(
        customer_name="Invented Pharma",
        product_name="Invented Product",
        batch_lot_number="BATCH-999",
        quantity_affected=999,
        complaint_type="Physical Damage",
        detailed_description="Customer reported cracked tablets.",
    )
    ai = FakeStructuredAI([extracted_by_ai, assessment()])
    graph = build_complaint_graph(
        document_parser_service=FakeDocumentParser(text),
        extraction_service=ComplaintExtractionService(ai),
        risk_service=RiskService(ai),
    )

    result = run(
        graph.ainvoke(
            initial_complaint_graph_state(
                "Process uploaded complaint document",
                document_filename="complaint.txt",
                document_content=b"source",
            )
        )
    )
    extracted = ComplaintData.model_validate(result["complaint"])

    assert extracted.customer_name is None
    assert extracted.product_name is None
    assert extracted.batch_lot_number is None
    assert extracted.quantity_affected is None
    assert extracted.complaint_type == "Physical Damage"
    assert extracted.detailed_description == text


def test_document_created_complaint_can_be_edited_and_risk_reassessed() -> None:
    original = complaint()
    risk = RecordingRiskService(assessment())
    graph = build_complaint_graph(
        document_parser_service=FakeDocumentParser("parsed complaint"),
        extraction_service=FakeExtractionService(original),
        edit_service=EditComplaintService(
            edit_tool=FakeEditTool(ComplaintPatch(quantity_affected=200))
        ),
        risk_service=risk,
    )
    graph_service = ComplaintGraphService(graph=graph)

    uploaded = run(graph_service.run_document("complaint.txt", b"source"))
    edited = run(
        graph_service.run(
            "Actually change the quantity affected to 200.",
            current_complaint=uploaded.complaint,
        )
    )

    assert uploaded.complaint == original
    assert edited.complaint.quantity_affected == 200
    assert edited.changed_fields == ["quantity_affected"]
    for field_name in ComplaintData.model_fields:
        if field_name != "quantity_affected":
            assert getattr(edited.complaint, field_name) == getattr(original, field_name)
    assert len(risk.calls) == 2
    assert risk.calls[1][0].quantity_affected == 200


def test_document_endpoint_returns_parser_validation_errors_without_ai_call() -> None:
    extraction = FakeExtractionService(complaint())
    graph = build_complaint_graph(
        document_parser_service=DocumentParserService(max_size_bytes=4),
        extraction_service=extraction,
        risk_service=RecordingRiskService(assessment()),
    )
    app.dependency_overrides[get_complaint_graph_service] = lambda: ComplaintGraphService(
        graph=graph
    )
    try:
        unsupported = TestClient(app).post(
            "/api/agent/document",
            files={"file": ("complaint.exe", b"not accepted", "application/octet-stream")},
        )
        empty = TestClient(app).post(
            "/api/agent/document",
            files={"file": ("complaint.txt", b"", "text/plain")},
        )
        too_large = TestClient(app).post(
            "/api/agent/document",
            files={"file": ("complaint.txt", b"12345", "text/plain")},
        )
    finally:
        app.dependency_overrides.pop(get_complaint_graph_service, None)

    assert unsupported.status_code == 415
    assert empty.status_code == 422
    assert too_large.status_code == 413
    assert extraction.calls == []


def test_document_endpoint_runs_multipart_graph_workflow() -> None:
    parser = FakeDocumentParser("parsed document complaint")
    extraction = FakeExtractionService(complaint())
    graph = build_complaint_graph(
        document_parser_service=parser,
        extraction_service=extraction,
        risk_service=RecordingRiskService(assessment()),
    )
    app.dependency_overrides[get_complaint_graph_service] = lambda: ComplaintGraphService(
        graph=graph
    )
    try:
        response = TestClient(app).post(
            "/api/agent/document",
            files={"file": ("complaint.txt", b"uploaded", "text/plain")},
        )
    finally:
        app.dependency_overrides.pop(get_complaint_graph_service, None)

    assert response.status_code == 200
    assert response.json()["complaint"]["customer_name"] == "ABC Pharma"
    assert response.json()["changed_fields"] == []
    assert parser.calls == [("complaint.txt", b"uploaded")]


def test_document_graph_rejects_parser_error_without_leaking_binary_content() -> None:
    parser = DocumentParserService()
    graph = build_complaint_graph(
        document_parser_service=parser,
        extraction_service=FakeExtractionService(complaint()),
        risk_service=RecordingRiskService(assessment()),
    )

    with pytest.raises(ValueError, match="Unsupported document type"):
        run(ComplaintGraphService(graph=graph).run_document("complaint.exe", b"source"))
