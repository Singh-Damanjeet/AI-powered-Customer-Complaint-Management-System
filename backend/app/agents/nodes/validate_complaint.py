"""Complaint state validation node."""

from __future__ import annotations

from typing import Any

from app.agents.nodes.common import logger, workflow_error_update
from app.agents.state import ComplaintGraphState
from app.schemas.complaint import ComplaintData


def validate_complaint_node(state: ComplaintGraphState) -> dict[str, Any]:
    """Validate extracted data without filling or inferring factual fields."""

    raw_complaint = state.get("complaint")
    if raw_complaint is None:
        return workflow_error_update(
            state,
            ValueError("complaint is required before validation."),
            phase="validate",
        )

    try:
        complaint = ComplaintData.model_validate(raw_complaint)
    except Exception as exc:
        return workflow_error_update(state, exc, phase="validate")

    logger.info("LangGraph node=validate_complaint completed")
    return {"complaint": complaint.model_dump(mode="json")}


validate_complaint = validate_complaint_node


__all__ = ["validate_complaint", "validate_complaint_node"]
