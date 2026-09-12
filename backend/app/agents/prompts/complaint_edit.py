"""Prompt construction for safe natural-language complaint edits."""

from __future__ import annotations

import json

from app.schemas.complaint import ComplaintData


COMPLAINT_EDIT_SYSTEM_PROMPT = (
    "You are editing an existing pharmaceutical customer complaint. "
    "Identify ONLY fields the user explicitly wants changed and return a "
    "ComplaintPatch object. Return only changed fields; do not repeat "
    "unchanged fields. Never invent factual complaint information or guess "
    "replacement values. If a requested value is ambiguous, omit that field. "
    "If the user clearly asks to remove, clear, or mark a field unknown, "
    "include that field with an explicit null. An omitted field means no "
    "change; do not use null for omitted fields. Do not perform risk "
    "classification in this step. If the user adds description detail, "
    "return only the supplied addition when possible; the application will "
    "preserve the existing description context. Return only ComplaintPatch "
    "fields."
)


def build_complaint_edit_prompt(
    current_complaint: ComplaintData,
    user_instruction: str,
) -> str:
    """Build a delimited edit prompt using the current complaint as context."""

    current_json = json.dumps(
        current_complaint.model_dump(mode="json"),
        sort_keys=True,
    )
    return (
        "Identify only the explicit complaint changes requested by the user. "
        "Do not return a regenerated full complaint. Treat the current state "
        "as context and the instruction as the requested edit.\n\n"
        "<current_complaint>\n"
        f"{current_json}\n"
        "</current_complaint>\n\n"
        "<edit_instruction>\n"
        f"{user_instruction}\n"
        "</edit_instruction>"
    )


# Short aliases make the prompt module convenient for future agent adapters.
build_edit_prompt = build_complaint_edit_prompt


__all__ = [
    "COMPLAINT_EDIT_SYSTEM_PROMPT",
    "build_complaint_edit_prompt",
    "build_edit_prompt",
]
