import asyncio
from decimal import Decimal

import pytest

from app.schemas.complaint import ComplaintData, Priority, RiskAssessment, Severity
from app.schemas.risk import RiskSignals
from app.services.ai_errors import AIResponseValidationError
from app.services.groq_service import GroqProviderError, GroqResponseError
from app.services.risk_service import RiskService


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


def complaint(**values) -> ComplaintData:
    defaults = {
        "product_name": "Metformin",
        "batch_lot_number": "MT24003",
        "complaint_type": "Quality defect",
        "detailed_description": "A product quality issue was reported.",
    }
    defaults.update(values)
    return ComplaintData(**defaults)


def test_risk_signals_cover_pharmaceutical_quality_indicators() -> None:
    service = RiskService(large_quantity_threshold=Decimal("100"))

    signals = service.detect_risk_signals(
        complaint(
            quantity_affected=120,
        ),
        (
            "A patient experienced severe vomiting after use. A metal fragment "
            "was found in the bottle. There is microbial contamination. The "
            "bottle has a wrong strength and a broken seal. Several cracked "
            "tablets were also reported."
        ),
    )

    assert signals.adverse_event_signal is True
    assert signals.serious_health_signal is True
    assert signals.foreign_material_signal is True
    assert signals.contamination_signal is True
    assert signals.wrong_strength_signal is True
    assert signals.packaging_integrity_signal is True
    assert signals.product_damage_signal is True
    assert signals.large_quantity_signal is True
    assert "metal fragment" in signals.matched_terms


def test_explicit_adverse_event_negation_does_not_trigger_signal() -> None:
    signals = RiskService().detect_risk_signals(
        complaint(),
        "No adverse events have been reported.",
    )

    assert signals.adverse_event_signal is False
    assert "adverse event" not in signals.matched_terms


def test_packaging_labeling_and_wrong_strength_signals_are_separate() -> None:
    signals = RiskService().detect_risk_signals(
        complaint(),
        "Several blister packs were open and seals were damaged. The bottle "
        "has an incorrect label and appears to have the wrong strength.",
    )

    assert signals.packaging_integrity_signal is True
    assert signals.labeling_signal is True
    assert signals.wrong_strength_signal is True


def test_missing_information_is_included_for_ai_uncertainty() -> None:
    signals = RiskService().detect_risk_signals(
        ComplaintData(detailed_description="Customer reported a defect."),
        "Customer reported a defect.",
    )

    assert "product_name" in signals.missing_information
    assert "batch_lot_number" in signals.missing_information
    assert "quantity_affected" in signals.missing_information
    assert "complaint_type" in signals.missing_information


def test_quantity_threshold_is_configurable_and_not_regulatory() -> None:
    service = RiskService(large_quantity_threshold=Decimal("1000"))

    signals = service.detect_risk_signals(
        complaint(quantity_affected=120),
        "120 tablets were affected.",
    )

    assert signals.large_quantity_signal is False


def test_ai_risk_assessment_is_validated_and_always_requires_qa_review() -> None:
    ai = FakeStructuredAI(
        [
            RiskAssessment(
                severity=Severity.MINOR,
                priority=Priority.LOW,
                rationale="The supplied information indicates a limited cosmetic issue.",
                recommended_actions=["Review retained samples"],
                qa_investigation_required=False,
                product_replacement_recommended=False,
            )
        ]
    )
    service = RiskService(ai)

    assessment = run(
        service.assess_risk(
            complaint(complaint_type="Discoloration"),
            "Customer reported minor brown discoloration with no adverse events.",
        )
    )

    assert assessment.severity is Severity.MINOR
    assert assessment.priority is Priority.LOW
    assert assessment.qa_investigation_required is True
    assert assessment.recommended_actions == ["Review retained samples"]
    assert ai.calls[0]["response_model"] is RiskAssessment
    assert "preliminary pharmaceutical complaint risk assessment" in ai.calls[0]["system_prompt"]
    assert "adverse_event_signal" in ai.calls[0]["user_prompt"]


def test_invalid_risk_output_is_retried_and_rejected() -> None:
    ai = FakeStructuredAI(
        [
            {"severity": "Super Dangerous", "priority": "Immediate"},
            {"severity": "Super Dangerous", "priority": "Immediate"},
        ]
    )

    with pytest.raises(AIResponseValidationError, match="after retry"):
        run(RiskService(ai).assess_risk(complaint(), "A quality complaint was reported."))

    assert len(ai.calls) == 2


def test_provider_failure_is_not_misreported_as_a_validation_failure() -> None:
    ai = FakeStructuredAI([GroqProviderError("provider unavailable")])

    with pytest.raises(GroqProviderError):
        run(RiskService(ai).assess_risk(complaint(), "A quality complaint was reported."))


def test_risk_signals_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError):
        RiskSignals(unexpected_signal=True)
