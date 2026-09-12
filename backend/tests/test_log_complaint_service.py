import asyncio

from app.schemas.complaint import ComplaintAgentResponse, ComplaintData, RiskAssessment
from app.services.groq_service import GroqProviderError
from app.services.log_complaint_service import LogComplaintService


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


def test_log_service_returns_agent_response_without_persistence() -> None:
    complaint = ComplaintData(
        complaint_source="Email",
        customer_name="ABC Pharma",
        product_name="Metformin",
        product_strength_grade="500 mg",
        batch_lot_number="MT24003",
        quantity_affected=120,
        quantity_unit="tablets",
        complaint_type="Discoloration",
        detailed_description="Brown discoloration reported on Metformin tablets.",
    )
    risk = RiskAssessment(
        severity="Major",
        priority="Medium",
        rationale="The reported product-quality defect requires QA review.",
        recommended_actions=["Review retained samples", "Assess other units from the same batch"],
        qa_investigation_required=True,
        product_replacement_recommended=False,
    )
    ai = FakeStructuredAI([complaint, risk])

    response = run(
        LogComplaintService(groq_service=ai).process(
            "ABC Pharma reported brown discoloration on 120 Metformin 500mg tablets "
            "from batch MT24003."
        )
    )

    assert isinstance(response, ComplaintAgentResponse)
    assert response.complaint.customer_name == "ABC Pharma"
    assert response.risk_assessment.priority == "Medium"
    assert response.changed_fields == []
    assert response.assistant_message == (
        "I've extracted the complaint details and completed an initial AI risk "
        "assessment. The assessment requires QA review."
    )
    assert len(ai.calls) == 2
    assert ai.calls[0]["response_model"] is ComplaintData
    assert ai.calls[1]["response_model"] is RiskAssessment
    assert "ComplaintData" in ai.calls[0]["system_prompt"]
    assert "RiskSignals" in ai.calls[1]["system_prompt"]


def test_log_service_does_not_save_when_ai_fails() -> None:
    ai = FakeStructuredAI([GroqProviderError("provider unavailable")])

    try:
        run(LogComplaintService(groq_service=ai).process("A complaint was reported."))
    except GroqProviderError:
        pass
    else:
        raise AssertionError("Expected provider error")

