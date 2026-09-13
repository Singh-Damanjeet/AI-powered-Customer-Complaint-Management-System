"""Final hardening regressions for routing, patch safety, and demo inputs."""

import asyncio
from pathlib import Path

from app.agents.router import ComplaintIntent, classify_intent_value, route_by_intent
from app.agents.state import initial_complaint_graph_state
from app.schemas.complaint import ComplaintData, ComplaintPatch
from app.services.complaint_merge_service import apply_patch
from app.services.document_parser import DocumentParserService


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run(coroutine):
    return asyncio.run(coroutine)


def populated_complaint() -> ComplaintData:
    return ComplaintData(
        complaint_source="Customer email",
        customer_name="ABC Pharma",
        complainant_name="Asha Rao",
        complainant_contact="asha@example.com",
        product_type="FDF",
        product_name="Metformin Hydrochloride Tablets",
        product_strength_grade="500 mg",
        batch_lot_number="MT24003",
        manufacturing_date="2026-07-18",
        expiry_date="2028-06-30",
        quantity_affected=120,
        quantity_unit="tablets",
        complaint_type="Discoloration",
        complaint_date="2026-07-20",
        received_date="2026-07-20",
        detailed_description=(
            "Brown discoloration was observed on multiple tablets. "
            "No adverse events have been reported."
        ),
    )


def test_phase11_patch_changes_exactly_one_requested_field() -> None:
    before = populated_complaint()
    after, changed_fields = apply_patch(
        before,
        ComplaintPatch(quantity_affected=700),
    )

    assert changed_fields == ["quantity_affected"]
    before_values = before.model_dump(mode="json")
    after_values = after.model_dump(mode="json")
    changed_values = [
        field_name
        for field_name in ComplaintData.model_fields
        if before_values[field_name] != after_values[field_name]
    ]
    assert changed_values == ["quantity_affected"]
    for field_name in ComplaintData.model_fields:
        if field_name != "quantity_affected":
            assert after_values[field_name] == before_values[field_name]


def test_phase11_intent_matrix_keeps_log_edit_document_and_unknown_separate() -> None:
    current = populated_complaint().model_dump(mode="json")
    cases = (
        ("Log a new complaint for ABC Pharma.", None, ComplaintIntent.LOG_COMPLAINT),
        ("Create complaint for a packaging defect.", None, ComplaintIntent.LOG_COMPLAINT),
        ("Change quantity to 500.", current, ComplaintIntent.EDIT_COMPLAINT),
        ("Actually batch is ABC123.", current, ComplaintIntent.EDIT_COMPLAINT),
        ("Please tell me a joke.", None, ComplaintIntent.UNKNOWN),
    )

    for message, complaint, expected in cases:
        assert classify_intent_value(message, current_complaint=complaint) is expected

    document_state = initial_complaint_graph_state(
        "Process uploaded complaint document",
        document_filename="complaint.pdf",
        document_content=b"document",
    )
    document_state["intent"] = ComplaintIntent.DOCUMENT_COMPLAINT.value
    assert route_by_intent(document_state) == "extract_document"


def test_phase11_sample_documents_parse_in_all_supported_formats() -> None:
    parser = DocumentParserService()
    expected_files = (
        "metformin_discoloration.pdf",
        "foreign_material.docx",
        "packaging_issue.txt",
        "complaint_email.eml",
    )

    for filename in expected_files:
        content = (PROJECT_ROOT / "sample_documents" / filename).read_bytes()
        text = run(parser.parse(filename, content))
        assert text

