"""Orchestration service for the Phase 4 log complaint workflow."""

from __future__ import annotations

from app.schemas.complaint import ComplaintAgentResponse
from app.services.complaint_extraction_service import ComplaintExtractionService
from app.services.groq_service import GroqService
from app.services.risk_service import RiskService


class LogComplaintService:
    """Coordinate extraction and preliminary risk assessment in memory."""

    def __init__(
        self,
        extraction_service: ComplaintExtractionService | None = None,
        risk_service: RiskService | None = None,
        groq_service: GroqService | None = None,
    ) -> None:
        self.extraction_service = extraction_service
        self.risk_service = risk_service
        self.groq_service = groq_service

    async def process(self, user_message: str) -> ComplaintAgentResponse:
        """Extract facts, assess risk, and return an unsaved agent response."""

        if not isinstance(user_message, str) or not user_message.strip():
            raise ValueError("user_message must be a non-empty string.")

        extraction_service = self.extraction_service
        risk_service = self.risk_service
        if extraction_service is None or risk_service is None:
            shared_groq_service = self.groq_service or GroqService()
            extraction_service = extraction_service or ComplaintExtractionService(
                shared_groq_service
            )
            risk_service = risk_service or RiskService(shared_groq_service)

        complaint = await extraction_service.extract(user_message)
        risk_assessment = await risk_service.assess_risk(
            complaint=complaint,
            original_text=user_message,
        )

        return ComplaintAgentResponse(
            complaint=complaint,
            risk_assessment=risk_assessment,
            assistant_message=(
                "I've extracted the complaint details and completed an initial AI "
                "risk assessment. The assessment requires QA review."
            ),
            # This is a new in-memory complaint, not an edit to existing state.
            changed_fields=[],
        )


async def log_complaint(
    user_message: str,
    groq_service: GroqService | None = None,
) -> ComplaintAgentResponse:
    """Run the log complaint workflow without persisting its result."""

    return await LogComplaintService(groq_service=groq_service).process(user_message)


__all__ = ["LogComplaintService", "log_complaint"]
