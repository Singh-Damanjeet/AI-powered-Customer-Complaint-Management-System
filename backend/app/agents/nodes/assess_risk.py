"""Risk assessment node backed by the Phase 4 RiskService."""

from __future__ import annotations

from typing import Any

from app.agents.nodes.common import logger, maybe_await, workflow_error_update
from app.agents.state import ComplaintGraphState
from app.schemas.complaint import ComplaintData, RiskAssessment
from app.services.groq_service import GroqService
from app.services.risk_service import RiskService


def _risk_source_text(state: ComplaintGraphState, complaint: ComplaintData) -> str:
    """Include existing complaint context when reassessing an edit."""

    original_text = state.get("user_message")
    if not isinstance(original_text, str) or not original_text.strip():
        raise ValueError("user_message must be a non-empty string.")
    if state.get("intent") != "EDIT_COMPLAINT":
        return original_text

    context_parts = [original_text.strip()]
    if complaint.detailed_description:
        context_parts.append(complaint.detailed_description)
    if complaint.complaint_type:
        context_parts.append(f"Complaint type: {complaint.complaint_type}")
    return "\n".join(context_parts)


async def assess_risk_node(
    state: ComplaintGraphState,
    risk_service: RiskService | None = None,
    *,
    groq_service: GroqService | None = None,
) -> dict[str, Any]:
    """Assess validated complaint risk using the existing risk service."""

    try:
        complaint = ComplaintData.model_validate(state.get("complaint"))
        original_text = _risk_source_text(state, complaint)

        service = risk_service or RiskService(groq_service)
        assessment = await maybe_await(
            service.assess_risk(
                complaint=complaint,
                original_text=original_text,
            )
        )
        assessment = RiskAssessment.model_validate(assessment)
        logger.info(
            "LangGraph node=assess_risk completed severity=%s priority=%s",
            assessment.severity.value,
            assessment.priority.value,
        )
        return {"risk_assessment": assessment.model_dump(mode="json")}
    except Exception as exc:
        return workflow_error_update(state, exc, phase="risk")


def make_assess_risk_node(
    risk_service: RiskService | None = None,
    *,
    groq_service: GroqService | None = None,
):
    """Capture risk-service dependencies outside graph state."""

    async def node(state: ComplaintGraphState) -> dict[str, Any]:
        return await assess_risk_node(
            state,
            risk_service=risk_service,
            groq_service=groq_service,
        )

    return node


assess_risk = assess_risk_node


__all__ = ["assess_risk", "assess_risk_node", "make_assess_risk_node"]
