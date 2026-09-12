"""Deterministic intent classification and LangGraph routing."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from app.agents.state import ComplaintGraphState


class ComplaintIntent(str, Enum):
    """User intents supported by the complaint workflow boundary."""

    LOG_COMPLAINT = "LOG_COMPLAINT"
    EDIT_COMPLAINT = "EDIT_COMPLAINT"
    DOCUMENT_COMPLAINT = "DOCUMENT_COMPLAINT"
    UNKNOWN = "UNKNOWN"


_EDIT_LANGUAGE_PATTERN = re.compile(
    r"\b(?:change|edit|update|correct|modify|replace|revise|amend|set)\b"
    r"|\bactually\b.*\b(?:quantity|batch|lot|product|strength|date|customer|"
    r"description|contact)\b|\b(?:should\s+be|is\s+now|are\s+now)\b",
    re.IGNORECASE | re.DOTALL,
)
_CONTEXT_EDIT_LANGUAGE_PATTERN = re.compile(
    r"\b(?:actually|also|add\s+that|include\s+that|mention\s+that|append)\b",
    re.IGNORECASE,
)
_DOCUMENT_LANGUAGE_PATTERN = re.compile(
    r"\b(?:upload(?:ed|ing)?|attachment|attached\s+(?:file|document)|document\s+"
    r"(?:complaint|intake|report))\b",
    re.IGNORECASE,
)
_LOG_LANGUAGE_PATTERN = re.compile(
    r"\b(?:log|create|record|register|report(?:ed|ing)?|complaint|"
    r"customer|client|patient|defect|discoloration|discolouration|damaged?|"
    r"broken|cracked|foreign\s+(?:material|object|particle)|contamination|"
    r"wrong\s+(?:label|strength|product)|packaging|leak(?:ing)?|batch|lot|"
    r"tablet(?:s)?|capsule(?:s)?|affected|quality|pharmaceutical|\d+\s*(?:mg|"
    r"mcg|g|kg))\b",
    re.IGNORECASE,
)


def _explicit_intent(state: ComplaintGraphState) -> ComplaintIntent | None:
    """Honor a future caller-provided intent without involving an LLM."""

    metadata = state.get("metadata")
    if not isinstance(metadata, dict):
        return None
    requested = metadata.get("intent") or metadata.get("mode")
    try:
        return ComplaintIntent(requested) if requested is not None else None
    except (TypeError, ValueError):
        return None


def classify_intent_value(
    user_message: str,
    *,
    current_complaint: Any | None = None,
    document_text: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ComplaintIntent:
    """Classify obvious workflow intent using predictable local rules.

    A fresh complaint narrative is sent through the log path only when it
    contains complaint/logging language. Unrelated text remains ``UNKNOWN``;
    edit language is checked first so an edit is never silently logged as a
    new complaint.
    """

    if not isinstance(user_message, str) or not user_message.strip():
        return ComplaintIntent.UNKNOWN

    context_state: ComplaintGraphState = {"metadata": metadata or {}}
    explicit = _explicit_intent(context_state)
    if explicit is not None:
        return explicit

    normalized_message = " ".join(user_message.split())
    if isinstance(document_text, str) and document_text.strip():
        return ComplaintIntent.DOCUMENT_COMPLAINT
    if _DOCUMENT_LANGUAGE_PATTERN.search(normalized_message):
        return ComplaintIntent.DOCUMENT_COMPLAINT
    if _EDIT_LANGUAGE_PATTERN.search(normalized_message):
        return ComplaintIntent.EDIT_COMPLAINT
    if current_complaint is not None and _CONTEXT_EDIT_LANGUAGE_PATTERN.search(
        normalized_message
    ):
        return ComplaintIntent.EDIT_COMPLAINT
    if _LOG_LANGUAGE_PATTERN.search(normalized_message):
        return ComplaintIntent.LOG_COMPLAINT
    return ComplaintIntent.UNKNOWN


def classify_intent(
    value: str | ComplaintGraphState,
    *,
    current_complaint: Any | None = None,
    document_text: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ComplaintIntent:
    """Public classifier accepting either a message or graph state."""

    if isinstance(value, dict):
        message = value.get("user_message")
        if not isinstance(message, str):
            return ComplaintIntent.UNKNOWN
        return classify_intent_value(
            message,
            current_complaint=value.get("complaint"),
            document_text=value.get("document_text"),
            metadata=value.get("metadata"),
        )
    if not isinstance(value, str):
        return ComplaintIntent.UNKNOWN
    return classify_intent_value(
        value,
        current_complaint=current_complaint,
        document_text=document_text,
        metadata=metadata,
    )


def route_by_intent(state: ComplaintGraphState) -> str:
    """Return the next graph node for a classified intent."""

    if state.get("errors"):
        return "workflow_error"

    try:
        intent = ComplaintIntent(state.get("intent", ComplaintIntent.UNKNOWN))
    except (TypeError, ValueError):
        intent = ComplaintIntent.UNKNOWN

    if intent is ComplaintIntent.LOG_COMPLAINT:
        return "log_complaint"
    if intent is ComplaintIntent.EDIT_COMPLAINT:
        # An edit has no safe target until the caller supplies the current
        # complaint. Keep the request on the terminal compatibility branch
        # instead of invoking the edit tool with missing state.
        if state.get("complaint") is None:
            return "unsupported_for_now"
        return "edit_complaint"
    if intent is ComplaintIntent.DOCUMENT_COMPLAINT:
        metadata = state.get("metadata")
        has_document_input = (
            "document_filename" in state
            or "document_content" in state
            or (
                isinstance(metadata, dict)
                and bool(metadata.get("document_filename"))
            )
        )
        # Preserve the Phase 5 terminal behavior for callers that only put
        # arbitrary document text in state. Real document requests carry a
        # filename (or transient content) and use the active parser branch.
        if has_document_input:
            return "extract_document"
        return "unsupported_for_now"
    return "unsupported_request"


def route_after_log(state: ComplaintGraphState) -> str:
    """Stop after extraction failures; otherwise validate extracted data."""

    return "workflow_error" if state.get("errors") else "validate_complaint"


def route_after_edit(state: ComplaintGraphState) -> str:
    """Stop after edit/merge failures; otherwise validate updated state."""

    return "workflow_error" if state.get("errors") else "validate_complaint"


def route_after_document(state: ComplaintGraphState) -> str:
    """Continue to shared complaint extraction after parsing document text."""

    return "workflow_error" if state.get("errors") else "extract_complaint_from_document"


def route_after_document_extraction(state: ComplaintGraphState) -> str:
    """Continue to complaint validation after document fact extraction."""

    return "workflow_error" if state.get("errors") else "validate_complaint"


def route_after_validate(state: ComplaintGraphState) -> str:
    """Send valid complaints to risk assessment.

    ``legacy_processed`` exists only for backwards-compatible dependency
    overrides from the Phase 4 API tests. Normal graph invocations always use
    the dedicated risk node.
    """

    if state.get("errors"):
        return "workflow_error"
    if state.get("legacy_processed") and state.get("risk_assessment"):
        return "generate_response"
    return "assess_risk"


def route_after_assess(state: ComplaintGraphState) -> str:
    """Stop after risk failures; otherwise generate the final response."""

    return "workflow_error" if state.get("errors") else "generate_response"


__all__ = [
    "ComplaintIntent",
    "classify_intent",
    "classify_intent_value",
    "route_after_assess",
    "route_after_document",
    "route_after_document_extraction",
    "route_after_edit",
    "route_after_log",
    "route_after_validate",
    "route_by_intent",
]
