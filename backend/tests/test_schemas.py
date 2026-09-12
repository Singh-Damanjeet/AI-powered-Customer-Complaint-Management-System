from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import (
    ComplaintAgentResponse,
    ComplaintData,
    ComplaintPatch,
    Priority,
    ProductType,
    RiskAssessment,
    Severity,
)


def complete_complaint() -> ComplaintData:
    return ComplaintData(
        complaint_source="Email",
        customer_name="Acme Pharma",
        product_name="Example API",
        product_strength_grade="USP Grade",
        batch_lot_number="B-2026-001",
        manufacturing_date=date(2026, 1, 10),
        expiry_date=date(2028, 1, 9),
        quantity_affected=Decimal("12.5"),
        quantity_unit="kg",
        complaint_type="Foreign particles",
        complaint_date=date(2026, 2, 1),
        detailed_description="Customer reported visible particles in the received material.",
        product_type=ProductType.API,
        received_date=date(2026, 1, 20),
        complainant_name="Asha Rao",
        complainant_contact="asha.rao@example.com",
    )


def test_complaint_data_validates_all_supported_fields() -> None:
    complaint = complete_complaint()

    assert complaint.product_type is ProductType.API
    assert complaint.quantity_affected == Decimal("12.5")
    assert complaint.manufacturing_date == date(2026, 1, 10)


def test_unknown_complaint_values_are_none() -> None:
    complaint = ComplaintData()

    assert complaint.customer_name is None
    assert complaint.product_name is None
    assert complaint.manufacturing_date is None
    assert complaint.quantity_affected is None
    assert complaint.complainant_contact is None


def test_empty_factual_strings_are_rejected_instead_of_used_as_missing() -> None:
    with pytest.raises(ValidationError):
        ComplaintData(customer_name="")


def test_complaint_patch_excludes_omitted_fields() -> None:
    patch = ComplaintPatch(customer_name="Updated Customer")

    assert patch.as_update_dict() == {"customer_name": "Updated Customer"}
    assert "product_name" not in patch.as_update_dict()


def test_explicit_null_is_preserved_as_an_intentional_patch() -> None:
    patch = ComplaintPatch(complainant_contact=None)

    assert patch.as_update_dict() == {"complainant_contact": None}


def test_risk_assessment_accepts_supported_values() -> None:
    assessment = RiskAssessment(
        severity="Major",
        priority="High",
        rationale="The complaint may affect product quality and requires review.",
        recommended_actions=["Open QA investigation"],
        qa_investigation_required=True,
        product_replacement_recommended=False,
    )

    assert assessment.severity is Severity.MAJOR
    assert assessment.priority is Priority.HIGH


@pytest.mark.parametrize("field", ["severity", "priority"])
def test_malformed_risk_values_are_rejected(field: str) -> None:
    values = {
        "severity": Severity.MINOR,
        "priority": Priority.LOW,
        "rationale": "Initial assessment.",
        "recommended_actions": [],
        "qa_investigation_required": False,
        "product_replacement_recommended": False,
    }
    values[field] = "Not a supported value"

    with pytest.raises(ValidationError):
        RiskAssessment(**values)


def test_agent_response_has_the_required_envelope() -> None:
    response = ComplaintAgentResponse(
        complaint=complete_complaint(),
        risk_assessment=RiskAssessment(),
        assistant_message="Complaint captured.",
        changed_fields=["customer_name"],
    )

    assert response.complaint.customer_name == "Acme Pharma"
    assert response.risk_assessment.severity is Severity.UNKNOWN
    assert response.changed_fields == ["customer_name"]
