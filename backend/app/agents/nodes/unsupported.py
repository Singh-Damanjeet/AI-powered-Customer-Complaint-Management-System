"""Placeholder and terminal error nodes for future workflow branches."""

from __future__ import annotations

from typing import Any

from app.agents.router import ComplaintIntent
from app.agents.state import ComplaintGraphState


def unsupported_for_now_node(state: ComplaintGraphState) -> dict[str, Any]:
    """Explain that edit/document branches arrive in a later phase."""

    intent = state.get("intent")
    if intent == ComplaintIntent.EDIT_COMPLAINT.value:
        message = "Editing is not available in the current workflow yet."
    else:
        message = "Document intake is not available in the current workflow yet."
    return {
        "assistant_message": message,
        "changed_fields": list(state.get("changed_fields", [])),
        "errors": [],
        "workflow_status": "UNSUPPORTED",
    }


def unsupported_request_node(state: ComplaintGraphState) -> dict[str, Any]:
    """Handle unrelated or unrecognized requests without invoking AI."""

    return {
        "assistant_message": (
            "I couldn't identify a complaint logging request. Please describe the "
            "new complaint you want to log."
        ),
        "changed_fields": list(state.get("changed_fields", [])),
        "errors": [],
        "workflow_status": "UNSUPPORTED",
    }


def workflow_error_node(state: ComplaintGraphState) -> dict[str, Any]:
    """Terminate a failed workflow with a non-sensitive assistant message."""

    return {
        "assistant_message": "The complaint workflow could not be completed.",
        "changed_fields": list(state.get("changed_fields", [])),
        "workflow_status": "ERROR",
    }


__all__ = [
    "unsupported_for_now_node",
    "unsupported_request_node",
    "workflow_error_node",
]
