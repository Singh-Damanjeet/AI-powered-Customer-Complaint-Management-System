"""Complaint extraction node backed by the Phase 4 extraction service."""

from __future__ import annotations

from typing import Any

from app.agents.nodes.common import logger, maybe_await, workflow_error_update
from app.agents.state import ComplaintGraphState
from app.schemas.complaint import ComplaintAgentResponse, ComplaintData
from app.services.complaint_extraction_service import ComplaintExtractionService
from app.services.groq_service import GroqService


async def log_complaint_node(
    state: ComplaintGraphState,
    extraction_service: ComplaintExtractionService | None = None,
    *,
    groq_service: GroqService | None = None,
    legacy_log_service: Any | None = None,
) -> dict[str, Any]:
    """Extract factual complaint data and leave risk work to its own node."""

    message = state.get("user_message")
    if not isinstance(message, str) or not message.strip():
        return workflow_error_update(
            state,
            ValueError("user_message must be a non-empty string."),
            phase="log",
        )

    try:
        if legacy_log_service is not None:
            # Kept solely so existing Phase 4 dependency overrides continue to
            # work while the request still traverses the compiled graph.
            result = await maybe_await(legacy_log_service.process(message))
            response = ComplaintAgentResponse.model_validate(result)
            complaint = response.complaint
            logger.info("LangGraph node=log_complaint completed via compatibility service")
            return {
                "complaint": complaint.model_dump(mode="json"),
                "risk_assessment": response.risk_assessment.model_dump(mode="json"),
                "assistant_message": response.assistant_message,
                "changed_fields": list(response.changed_fields),
                "legacy_processed": True,
            }

        service = extraction_service or ComplaintExtractionService(groq_service)
        extracted = await maybe_await(service.extract(message))
        if isinstance(extracted, ComplaintData):
            complaint_value: Any = extracted.model_dump(mode="json")
        elif isinstance(extracted, dict):
            # Leave contract validation to the dedicated validation node. This
            # also makes malformed service doubles observable in that node.
            complaint_value = dict(extracted)
        else:
            complaint_value = extracted
        logger.info("LangGraph node=log_complaint completed")
        return {
            "complaint": complaint_value,
            "legacy_processed": False,
        }
    except Exception as exc:  # Convert provider/service failures to graph state.
        return workflow_error_update(state, exc, phase="log")


def make_log_complaint_node(
    extraction_service: ComplaintExtractionService | None = None,
    *,
    groq_service: GroqService | None = None,
    legacy_log_service: Any | None = None,
):
    """Capture node dependencies outside serializable LangGraph state."""

    async def node(state: ComplaintGraphState) -> dict[str, Any]:
        return await log_complaint_node(
            state,
            extraction_service=extraction_service,
            groq_service=groq_service,
            legacy_log_service=legacy_log_service,
        )

    return node


log_complaint = log_complaint_node


__all__ = ["log_complaint", "log_complaint_node", "make_log_complaint_node"]
