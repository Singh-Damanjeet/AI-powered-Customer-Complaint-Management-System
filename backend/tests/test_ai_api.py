from fastapi.testclient import TestClient

from app.main import app
from app.schemas.complaint import ComplaintAgentResponse, ComplaintData, RiskAssessment
from app.services.ai_errors import AIResponseValidationError
from app.services.groq_service import GroqProviderError
from app.services.log_complaint_service import LogComplaintService
from app.api.ai import get_log_complaint_service


def response() -> ComplaintAgentResponse:
    return ComplaintAgentResponse(
        complaint=ComplaintData(
            customer_name="ABC Pharma",
            product_name="Metformin",
            detailed_description="Brown discoloration was reported.",
        ),
        risk_assessment=RiskAssessment(
            severity="Minor",
            priority="Low",
            rationale="The available information indicates a limited cosmetic issue.",
            recommended_actions=["Review retained samples"],
            qa_investigation_required=True,
            product_replacement_recommended=False,
        ),
        assistant_message="The assessment requires QA review.",
        changed_fields=[],
    )


class FakeLogComplaintService:
    def __init__(self, result=None, error=None) -> None:
        self.result = result
        self.error = error
        self.messages: list[str] = []

    async def process(self, message: str) -> ComplaintAgentResponse:
        self.messages.append(message)
        if self.error is not None:
            raise self.error
        return self.result


def with_service(service: LogComplaintService | FakeLogComplaintService):
    app.dependency_overrides[get_log_complaint_service] = lambda: service
    return TestClient(app)


def test_log_complaint_endpoint_returns_unsaved_agent_response() -> None:
    service = FakeLogComplaintService(result=response())
    client = with_service(service)
    try:
        result = client.post(
            "/api/ai/log-complaint",
            json={"message": "ABC Pharma reported brown discoloration."},
        )
    finally:
        app.dependency_overrides.pop(get_log_complaint_service, None)

    assert result.status_code == 200
    assert result.json()["complaint"]["customer_name"] == "ABC Pharma"
    assert result.json()["risk_assessment"]["severity"] == "Minor"
    assert service.messages == ["ABC Pharma reported brown discoloration."]


def test_empty_log_complaint_message_returns_422() -> None:
    service = FakeLogComplaintService(result=response())
    client = with_service(service)
    try:
        result = client.post("/api/ai/log-complaint", json={"message": "  "})
    finally:
        app.dependency_overrides.pop(get_log_complaint_service, None)

    assert result.status_code == 422
    assert service.messages == []


def test_provider_failure_returns_503_without_internal_detail() -> None:
    service = FakeLogComplaintService(error=GroqProviderError("secret provider detail"))
    client = with_service(service)
    try:
        result = client.post("/api/ai/log-complaint", json={"message": "A complaint."})
    finally:
        app.dependency_overrides.pop(get_log_complaint_service, None)

    assert result.status_code == 503
    assert result.json() == {"detail": "AI service is unavailable."}
    assert "secret" not in result.text


def test_invalid_ai_response_returns_clean_502() -> None:
    service = FakeLogComplaintService(error=AIResponseValidationError("internal detail"))
    client = with_service(service)
    try:
        result = client.post("/api/ai/log-complaint", json={"message": "A complaint."})
    finally:
        app.dependency_overrides.pop(get_log_complaint_service, None)

    assert result.status_code == 502
    assert result.json() == {"detail": "AI response could not be validated."}


def test_unexpected_failure_returns_clean_500() -> None:
    service = FakeLogComplaintService(error=RuntimeError("internal detail"))
    client = with_service(service)
    try:
        result = client.post("/api/ai/log-complaint", json={"message": "A complaint."})
    finally:
        app.dependency_overrides.pop(get_log_complaint_service, None)

    assert result.status_code == 500
    assert result.json() == {"detail": "Unable to process complaint."}
    assert "internal detail" not in result.text
