import asyncio
from datetime import date
from decimal import Decimal

import pytest

from app.schemas.complaint import ComplaintData, ProductType
from app.services.ai_errors import AIResponseValidationError
from app.services.complaint_extraction_service import (
    ComplaintExtractionService,
    normalize_complaint_type,
)
from app.services.groq_service import GroqResponseError


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


def run(coroutine):
    return asyncio.run(coroutine)


def test_extracts_and_safely_normalizes_complaint_facts() -> None:
    ai = FakeStructuredAI(
        [
            ComplaintData(
                complaint_source="Email",
                customer_name="ABC Pharma",
                product_name="Metformin",
                product_strength_grade="500mg",
                batch_lot_number="MT24003",
                quantity_affected=120,
                quantity_unit="tabs",
                complaint_type="brown spots",
                detailed_description="Brown discoloration reported on Metformin tablets.",
            )
        ]
    )

    complaint = run(
        ComplaintExtractionService(ai).extract(
            "ABC Pharma reported brown discoloration on 120 Metformin 500mg "
            "tablets from batch MT24003."
        )
    )

    assert complaint.customer_name == "ABC Pharma"
    assert complaint.product_name == "Metformin"
    assert complaint.product_strength_grade == "500 mg"
    assert complaint.batch_lot_number == "MT24003"
    assert complaint.quantity_affected == Decimal("120")
    assert complaint.quantity_unit == "tablets"
    assert complaint.complaint_type == "Discoloration"
    assert complaint.manufacturing_date is None
    assert complaint.expiry_date is None
    assert ai.calls[0]["response_model"] is ComplaintData
    assert "only facts explicitly stated" in ai.calls[0]["system_prompt"]


def test_missing_information_remains_none() -> None:
    ai = FakeStructuredAI(
        [
            ComplaintData(
                complaint_type="Physical Damage",
                detailed_description="Customer reported damaged tablets from batch A123.",
                batch_lot_number="A123",
            )
        ]
    )

    complaint = run(ComplaintExtractionService(ai).extract("Customer reported damaged tablets from batch A123."))

    assert complaint.customer_name is None
    assert complaint.product_name is None
    assert complaint.product_strength_grade is None
    assert complaint.manufacturing_date is None
    assert complaint.expiry_date is None
    assert complaint.quantity_affected is None
    assert complaint.complaint_source is None


def test_ungrounded_ai_facts_are_removed_for_hallucination_resistance() -> None:
    ai = FakeStructuredAI(
        [
            ComplaintData(
                customer_name="Invented Customer",
                product_name="Invented Product",
                batch_lot_number="INVENTED-001",
                quantity_affected=999,
                manufacturing_date=date(2024, 1, 1),
                expiry_date=date(2026, 1, 1),
                detailed_description="Customer reported cracked tablets.",
            )
        ]
    )

    complaint = run(
        ComplaintExtractionService(ai).extract("Customer reported cracked tablets.")
    )

    assert complaint.customer_name is None
    assert complaint.product_name is None
    assert complaint.batch_lot_number is None
    assert complaint.quantity_affected is None
    assert complaint.manufacturing_date is None
    assert complaint.expiry_date is None
    assert complaint.detailed_description == "Customer reported cracked tablets."


def test_explicit_dates_are_returned_as_dates() -> None:
    ai = FakeStructuredAI(
        [
            ComplaintData(
                product_name="Paracetamol",
                manufacturing_date=date(2025, 1, 15),
                expiry_date=date(2027, 1, 14),
                detailed_description="Dates were provided in the complaint.",
            )
        ]
    )

    complaint = run(
        ComplaintExtractionService(ai).extract(
            "Paracetamol was manufactured on 2025-01-15 and expires on 2027-01-14."
        )
    )

    assert complaint.manufacturing_date == date(2025, 1, 15)
    assert complaint.expiry_date == date(2027, 1, 14)


def test_quantity_and_unit_are_preserved_as_typed_values() -> None:
    ai = FakeStructuredAI(
        [
            ComplaintData(
                quantity_affected=65,
                quantity_unit="capsule",
                detailed_description="Approximately 65 capsules were affected.",
            )
        ]
    )

    complaint = run(
        ComplaintExtractionService(ai).extract("Approximately 65 capsules were affected.")
    )

    assert complaint.quantity_affected == Decimal("65")
    assert complaint.quantity_unit == "capsules"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("brown spots", "Discoloration"),
        ("color variation", "Discoloration"),
        ("cracked tablets", "Physical Damage"),
        ("damaged tablets", "Physical Damage"),
        ("foreign object", "Foreign Material"),
        ("unknown material", "Foreign Material"),
        ("missing label", "Labeling"),
        ("broken seal", "Packaging"),
        ("damaged blister", "Packaging"),
        ("Other", "Other"),
    ],
)
def test_complaint_type_normalization_is_small_and_predictable(source: str, expected: str) -> None:
    assert normalize_complaint_type(source) == expected


def test_ai_indicated_unknown_product_type_becomes_null() -> None:
    ai = FakeStructuredAI(
        [
            ComplaintData(
                product_type=ProductType.UNKNOWN,
                detailed_description="Product category was not supplied.",
            )
        ]
    )

    complaint = run(ComplaintExtractionService(ai).extract("Product category was not supplied."))

    assert complaint.product_type is None


def test_empty_input_is_rejected_without_calling_ai() -> None:
    ai = FakeStructuredAI([])

    with pytest.raises(ValueError, match="non-empty"):
        run(ComplaintExtractionService(ai).extract("   "))

    assert ai.calls == []


def test_malformed_extraction_is_retried_then_succeeds() -> None:
    ai = FakeStructuredAI(
        [
            GroqResponseError("malformed response"),
            ComplaintData(product_name="Metformin"),
        ]
    )

    complaint = run(ComplaintExtractionService(ai).extract("Customer mentioned Metformin."))

    assert complaint.product_name == "Metformin"
    assert len(ai.calls) == 2


def test_malformed_extraction_after_retry_is_cleanly_rejected() -> None:
    ai = FakeStructuredAI(
        [
            GroqResponseError("malformed response"),
            GroqResponseError("malformed response"),
        ]
    )

    with pytest.raises(AIResponseValidationError, match="after retry"):
        run(ComplaintExtractionService(ai).extract("Customer mentioned a complaint."))

    assert len(ai.calls) == 2
