"""Natural-language complaint edit node."""

from __future__ import annotations

from typing import Any

from app.agents.nodes.common import logger, maybe_await, workflow_error_update
from app.agents.state import ComplaintGraphState
from app.agents.tools.edit_complaint import field_display_name, infer_edit_field
from app.schemas.complaint import ComplaintData, ComplaintPatch
from app.services.complaint_merge_service import apply_patch
from app.services.edit_complaint_service import EditComplaintService
from app.services.groq_service import GroqService


def _patch_from_result(
    current: ComplaintData,
    updated: ComplaintData,
    changed_fields: list[str],
    patch: ComplaintPatch | None,
) -> ComplaintPatch:
    """Use a service-provided patch or derive one for simple test doubles."""

    if patch is not None:
        return ComplaintPatch.model_validate(patch)
    return ComplaintPatch.model_validate(
        {
            field_name: getattr(updated, field_name)
            for field_name in changed_fields
            if getattr(current, field_name) != getattr(updated, field_name)
        }
    )


async def edit_complaint_node(
    state: ComplaintGraphState,
    edit_service: EditComplaintService | None = None,
    *,
    groq_service: GroqService | None = None,
) -> dict[str, Any]:
    """Apply a sparse edit and leave reassessment to the shared risk node."""

    raw_complaint = state.get("complaint")
    instruction = state.get("user_message")
    if raw_complaint is None:
        return workflow_error_update(
            state,
            ValueError("an existing complaint is required for editing."),
            phase="edit",
        )
    if not isinstance(instruction, str) or not instruction.strip():
        return workflow_error_update(
            state,
            ValueError("user_instruction must be a non-empty string."),
            phase="edit",
        )

    try:
        current = ComplaintData.model_validate(raw_complaint)
        service = edit_service or EditComplaintService(groq_service=groq_service)
        process_with_patch = getattr(service, "process_with_patch", None)
        if process_with_patch is not None:
            result = process_with_patch(
                current_complaint=current,
                user_instruction=instruction,
            )
            result = await maybe_await(result)
            if not isinstance(result, tuple) or len(result) != 3:
                raise TypeError("edit service returned an invalid edit result.")
            updated, changed_fields, raw_patch = result
            patch = ComplaintPatch.model_validate(raw_patch)
        else:
            result = service.process(
                current_complaint=current,
                user_instruction=instruction,
            )
            result = await maybe_await(result)
            if not isinstance(result, tuple) or len(result) != 2:
                raise TypeError("edit service returned an invalid edit result.")
            updated, changed_fields = result
            patch = None

        updated = ComplaintData.model_validate(updated)
        if not isinstance(changed_fields, list) or not all(
            isinstance(field_name, str) for field_name in changed_fields
        ):
            raise ValueError("changed_fields must be a list of strings.")

        # Recompute effective changes from the validated complaint when a
        # simple test double only exposes ``process``. The production service
        # returns an effective complaint because description additions may
        # intentionally include the existing description context.
        if patch is None:
            patch = _patch_from_result(current, updated, changed_fields, patch)
            updated, changed_fields = apply_patch(current, patch)
        else:
            changed_fields = [
                field_name
                for field_name in ComplaintData.model_fields
                if field_name in patch.model_fields_set
                and getattr(current, field_name) != getattr(updated, field_name)
            ]

            unexpected_changes = [
                field_name
                for field_name in ComplaintData.model_fields
                if field_name not in patch.model_fields_set
                and getattr(current, field_name) != getattr(updated, field_name)
            ]
            if unexpected_changes:
                raise ValueError(
                    "edit service changed fields outside the explicit patch: "
                    + ", ".join(unexpected_changes)
                )

        patch_changes = patch.model_dump(mode="json", exclude_unset=True)
        result_state: dict[str, Any] = {
            "complaint": updated.model_dump(mode="json"),
            "complaint_patch": patch_changes,
            "changed_fields": changed_fields,
            "edit_outcome": "UPDATED" if changed_fields else (
                "NO_OP" if patch_changes else "AMBIGUOUS"
            ),
        }
        if not changed_fields and not patch_changes:
            target_field = infer_edit_field(instruction)
            if target_field is not None:
                result_state["edit_notice"] = (
                    f"I couldn't update the {field_display_name(target_field)} "
                    "because no replacement value was provided."
                )
            else:
                result_state["edit_notice"] = (
                    "I couldn't apply that change because the replacement value "
                    "was not clear."
                )
        logger.info(
            "LangGraph node=edit_complaint completed changed_fields=%s",
            changed_fields,
        )
        return result_state
    except Exception as exc:
        return workflow_error_update(state, exc, phase="edit")


def make_edit_complaint_node(
    edit_service: EditComplaintService | None = None,
    *,
    groq_service: GroqService | None = None,
):
    """Capture edit-service dependencies outside serializable graph state."""

    async def node(state: ComplaintGraphState) -> dict[str, Any]:
        return await edit_complaint_node(
            state,
            edit_service=edit_service,
            groq_service=groq_service,
        )

    return node


edit_complaint = edit_complaint_node


__all__ = [
    "edit_complaint",
    "edit_complaint_node",
    "make_edit_complaint_node",
]
