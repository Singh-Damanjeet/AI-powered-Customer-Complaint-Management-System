"""Application service for in-memory complaint edits and patch merging."""

from __future__ import annotations

import inspect
from typing import Any

from app.agents.tools.edit_complaint import EditComplaintTool
from app.schemas.complaint import ComplaintData, ComplaintPatch
from app.services.complaint_merge_service import apply_patch


def _description_is_addition(instruction: str) -> bool:
    lowered = instruction.casefold()
    if lowered.lstrip().startswith("also "):
        return True
    return any(
        phrase in lowered
        for phrase in (
            "also add",
            "also mention",
            "also include",
            "add that",
            "include that",
            "mention that",
            "append",
        )
    )


def _description_is_replacement(instruction: str) -> bool:
    lowered = instruction.casefold()
    description_terms = ("description", "detail", "details")
    replacement_terms = ("replace", "overwrite", "set", "change", "update")
    return any(term in lowered for term in description_terms) and any(
        term in lowered for term in replacement_terms
    )


def merge_description_change(
    current_description: str | None,
    proposed_description: str,
    instruction: str,
) -> str:
    """Preserve existing description context for explicit additions."""

    if not current_description or _description_is_replacement(instruction):
        return proposed_description
    if not _description_is_addition(instruction):
        return proposed_description

    current_normalized = " ".join(current_description.casefold().split())
    proposed_normalized = " ".join(proposed_description.casefold().split())
    if current_normalized in proposed_normalized:
        return proposed_description
    if proposed_normalized in current_normalized:
        return current_description

    separator = "" if current_description.rstrip().endswith((".", "!", "?")) else "."
    addition = proposed_description.strip()
    if not addition:
        return current_description
    return f"{current_description.rstrip()}{separator} {addition[0].upper()}{addition[1:]}"


def _effective_patch(
    complaint: ComplaintData,
    patch: ComplaintPatch,
    instruction: str,
) -> ComplaintPatch:
    """Apply controlled description-addition semantics before generic merge."""

    changes = patch.model_dump(mode="python", exclude_unset=True)
    proposed = changes.get("detailed_description")
    if isinstance(proposed, str):
        changes["detailed_description"] = merge_description_change(
            complaint.detailed_description,
            proposed,
            instruction,
        )
    return ComplaintPatch.model_validate(changes)


class EditComplaintService:
    """Extract and apply complaint edits without database persistence."""

    def __init__(
        self,
        edit_tool: EditComplaintTool | Any | None = None,
        *,
        groq_service: Any | None = None,
    ) -> None:
        self.edit_tool = edit_tool or EditComplaintTool(groq_service=groq_service)

    async def _extract_patch(
        self,
        current_complaint: ComplaintData,
        user_instruction: str,
    ) -> ComplaintPatch:
        extractor = getattr(self.edit_tool, "extract_patch", None)
        if extractor is None:
            extractor = getattr(self.edit_tool, "run", None)
        if extractor is None:
            raise TypeError("edit_tool must provide extract_patch or run.")
        result = extractor(current_complaint, user_instruction)
        if inspect.isawaitable(result):
            result = await result
        return ComplaintPatch.model_validate(result)

    async def process_with_patch(
        self,
        current_complaint: ComplaintData,
        user_instruction: str,
    ) -> tuple[ComplaintData, list[str], ComplaintPatch]:
        """Return the updated complaint, changed fields, and sparse patch."""

        current = ComplaintData.model_validate(current_complaint)
        if not isinstance(user_instruction, str) or not user_instruction.strip():
            raise ValueError("user_instruction must be a non-empty string.")
        patch = await self._extract_patch(current, user_instruction.strip())
        effective_patch = _effective_patch(current, patch, user_instruction.strip())
        updated, changed_fields = apply_patch(current, effective_patch)
        return updated, changed_fields, patch

    async def process(
        self,
        current_complaint: ComplaintData,
        user_instruction: str,
    ) -> tuple[ComplaintData, list[str]]:
        """Apply one natural-language edit without saving it."""

        updated, changed_fields, _ = await self.process_with_patch(
            current_complaint,
            user_instruction,
        )
        return updated, changed_fields


__all__ = [
    "EditComplaintService",
    "apply_patch",
    "merge_description_change",
]
