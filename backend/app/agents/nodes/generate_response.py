"""Deterministic final response node for the complaint workflow."""

from __future__ import annotations

from typing import Any

from app.agents.nodes.common import logger, workflow_error_update
from app.agents.state import ComplaintGraphState
from app.schemas.complaint import ComplaintData, RiskAssessment, Severity


_EDIT_FIELD_LABELS = {
    "complaint_source": "complaint source",
    "customer_name": "customer name",
    "product_name": "product name",
    "product_strength_grade": "product strength",
    "batch_lot_number": "batch number",
    "manufacturing_date": "manufacturing date",
    "expiry_date": "expiry date",
    "quantity_affected": "affected quantity",
    "quantity_unit": "quantity unit",
    "complaint_type": "complaint type",
    "complaint_date": "complaint date",
    "received_date": "received date",
    "detailed_description": "description",
    "product_type": "product type",
    "complainant_name": "complainant name",
    "complainant_contact": "complainant contact",
}


def _format_changed_fields(changed_fields: list[str]) -> str:
    labels = [_EDIT_FIELD_LABELS.get(field, field.replace("_", " ")) for field in changed_fields]
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


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

        if state.get("intent") == "DOCUMENT_COMPLAINT":
            assistant_message = (
                "I extracted the complaint information from the uploaded document "
                "and completed a preliminary AI risk assessment. QA review is "
                "required."
            )
        elif state.get("intent") == "EDIT_COMPLAINT":
            outcome = state.get("edit_outcome")
            if outcome == "AMBIGUOUS":
                assistant_message = state.get("edit_notice") or (
                    "I couldn't apply that change because the replacement value "
                    "was not clear."
                )
            elif outcome == "NO_OP":
                assistant_message = (
                    "I reviewed the requested update, but the complaint values "
                    "were already the same. The risk assessment was refreshed."
                )
            elif changed_fields:
                assistant_message = (
                    f"I updated the {_format_changed_fields(changed_fields)}, then "
                    "recalculated the preliminary AI risk assessment."
                )
            else:
                assistant_message = (
                    "I couldn't apply that change because the replacement value "
                    "was not clear."
                )
        elif assessment.severity is Severity.UNKNOWN:
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
