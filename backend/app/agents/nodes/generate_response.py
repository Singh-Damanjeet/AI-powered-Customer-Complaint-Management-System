"""Deterministic final response node for the complaint workflow."""

from __future__ import annotations

from typing import Any

from app.agents.nodes.common import logger, workflow_error_update
from app.agents.state import ComplaintGraphState
from app.schemas.complaint import ComplaintData, RiskAssessment, Severity


def generate_response_node(state: ComplaintGraphState) -> dict[str, Any]:
    """Create a safe, preliminary response from validated graph state."""

    try:
        ComplaintData.model_validate(state.get("complaint"))
        assessment = RiskAssessment.model_validate(state.get("risk_assessment"))
        changed_fields = state.get("changed_fields", [])
        if not isinstance(changed_fields, list) or not all(
            isinstance(field_name, str) for field_name in changed_fields
        ):
            raise ValueError("changed_fields must be a list of strings.")

        if assessment.severity is Severity.UNKNOWN:
            assistant_message = (
                "I've extracted the available complaint details. There is not enough "
                "information for a confident risk classification, so QA review is "
                "required."
            )
        else:
            assistant_message = (
                "I've extracted the complaint details and completed an initial AI "
                "risk assessment. The preliminary assessment is "
                f"{assessment.severity.value} severity with "
                f"{assessment.priority.value} priority and requires QA review."
            )

        # Preserve the Phase 4 response text when a legacy test double is used.
        if state.get("legacy_processed") and state.get("assistant_message"):
            assistant_message = state["assistant_message"]

        logger.info("LangGraph node=generate_response completed")
        return {
            "assistant_message": assistant_message,
            "changed_fields": list(changed_fields),
            "workflow_status": "COMPLETED",
        }
    except Exception as exc:
        return workflow_error_update(state, exc, phase="response")


generate_response = generate_response_node


__all__ = ["generate_response", "generate_response_node"]
