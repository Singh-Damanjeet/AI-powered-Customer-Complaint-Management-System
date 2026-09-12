"""Deterministic intent-classification node."""

from __future__ import annotations

from typing import Any

from app.agents.router import classify_intent_value
from app.agents.state import ComplaintGraphState
from app.agents.nodes.common import logger, workflow_error_update


def classify_intent_node(state: ComplaintGraphState) -> dict[str, Any]:
    """Classify the request without spending an LLM call."""

    message = state.get("user_message")
    if not isinstance(message, str) or not message.strip():
        return workflow_error_update(
            state,
            ValueError("user_message must be a non-empty string."),
            phase="classify_intent",
        )

    intent = classify_intent_value(
        message,
        current_complaint=state.get("complaint"),
        document_text=state.get("document_text"),
        metadata=state.get("metadata"),
    )
    logger.info("LangGraph intent classified intent=%s", intent.value)
    return {
        "intent": intent.value,
        "workflow_status": "RUNNING",
        "errors": list(state.get("errors", [])),
    }


# Concise alias for callers that refer to the node by its specification name.
classify_intent = classify_intent_node


__all__ = ["classify_intent", "classify_intent_node"]
