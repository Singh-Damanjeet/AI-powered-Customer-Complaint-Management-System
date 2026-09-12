"""Serializable state used by the complaint LangGraph workflow."""

from __future__ import annotations

from typing import Any, TypedDict


class ComplaintGraphState(TypedDict, total=False):
    """Data passed between complaint workflow nodes.

    Service objects, database sessions, and provider clients deliberately do
    not belong here. Dependencies are captured when the graph is built so the
    state remains safe to inspect, test, and serialize.
    """

    user_message: str
    intent: str
    complaint: dict[str, Any]
    complaint_patch: dict[str, Any]
    document_text: str | None
    risk_assessment: dict[str, Any]
    assistant_message: str
    changed_fields: list[str]
    errors: list[str]
    error_code: str
    workflow_status: str
    legacy_processed: bool
    edit_outcome: str
    edit_notice: str
    request_id: str
    metadata: dict[str, Any]


def initial_complaint_graph_state(
    user_message: str,
    *,
    complaint: dict[str, Any] | None = None,
    document_text: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ComplaintGraphState:
    """Create the minimal state for one in-request workflow invocation."""

    state: ComplaintGraphState = {
        "user_message": user_message,
        "complaint_patch": {},
        "errors": [],
        "changed_fields": [],
    }
    if complaint is not None:
        state["complaint"] = complaint
    if document_text is not None:
        state["document_text"] = document_text
    if metadata is not None:
        state["metadata"] = metadata
    return state


__all__ = ["ComplaintGraphState", "initial_complaint_graph_state"]
