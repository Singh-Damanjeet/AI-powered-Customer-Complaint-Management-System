"""Validated, sparse merging of natural-language complaint patches."""

from __future__ import annotations

from typing import Any

from app.schemas.complaint import ComplaintData, ComplaintPatch


def apply_patch(
    complaint: ComplaintData,
    patch: ComplaintPatch,
) -> tuple[ComplaintData, list[str]]:
    """Apply only explicitly supplied patch fields.

    ``exclude_unset=True`` is essential here: a ``ComplaintPatch`` contains
    optional fields whose default is ``None``, but omitted fields must never
    clear a value in the existing complaint. Explicit ``None`` values remain
    present and therefore intentionally clear that field.
    """

    current = ComplaintData.model_validate(complaint)
    validated_patch = ComplaintPatch.model_validate(patch)
    changes: dict[str, Any] = validated_patch.model_dump(
        mode="python",
        exclude_unset=True,
    )

    current_values = current.model_dump(mode="python")
    updated_values = {**current_values, **changes}
    updated = ComplaintData.model_validate(updated_values)

    changed_fields = [
        field_name
        for field_name in ComplaintData.model_fields
        if field_name in changes
        and getattr(current, field_name) != getattr(updated, field_name)
    ]
    return updated, changed_fields


__all__ = ["apply_patch"]
