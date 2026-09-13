"""Deterministic complaint-intake completeness checks."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.complaint import ComplaintData, ProductType
from app.schemas.insights import ComplaintCompleteness, CompletenessStatus


# These weights describe useful information for an initial intake review. They
# are application heuristics, not regulatory or quality-system requirements.
# Keeping them in one mapping makes the score easy to review and change.
COMPLETENESS_WEIGHTS: Mapping[str, int] = {
    "product_name": 18,
    "batch_lot_number": 18,
    "detailed_description": 20,
    "complaint_type": 15,
    "customer_name": 10,
    "quantity_affected": 7,
    "complaint_date": 5,
    "product_strength_grade": 3,
    "manufacturing_date": 2,
    "expiry_date": 2,
}

COMPLETENESS_CRITICAL_FIELDS: tuple[str, ...] = (
    "product_name",
    "batch_lot_number",
    "detailed_description",
)

COMPLAINT_FIELD_DISPLAY_NAMES: Mapping[str, str] = {
    "complaint_source": "Complaint Source",
    "customer_name": "Customer Name",
    "complainant_name": "Complainant Name",
    "complainant_contact": "Complainant Contact",
    "product_type": "Product Type",
    "product_name": "Product Name",
    "product_strength_grade": "Product Strength / Grade",
    "batch_lot_number": "Batch / Lot Number",
    "manufacturing_date": "Manufacturing Date",
    "expiry_date": "Expiry Date",
    "quantity_affected": "Quantity Affected",
    "quantity_unit": "Quantity Unit",
    "complaint_type": "Complaint Type",
    "complaint_date": "Complaint Date",
    "received_date": "Received Date",
    "detailed_description": "Complaint Description",
}

_COMPLETENESS_MESSAGES = {
    CompletenessStatus.COMPLETE: (
        "The complaint contains the key information needed for initial triage."
    ),
    CompletenessStatus.MOSTLY_COMPLETE: (
        "The complaint contains enough information for initial triage, but some "
        "details are still missing."
    ),
    CompletenessStatus.INCOMPLETE: (
        "Important complaint information is missing; collect additional facts "
        "before relying on the intake record."
    ),
    CompletenessStatus.INSUFFICIENT: (
        "The complaint contains too little factual information for a meaningful "
        "intake assessment."
    ),
}


def is_known_value(value: Any) -> bool:
    """Return whether a complaint value represents a known fact.

    ``None`` is the canonical missing value. Whitespace-only strings and the
    explicit ``UNKNOWN`` product type are also treated as missing defensively
    for values originating from database rows or test doubles.
    """

    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if value is ProductType.UNKNOWN or value == ProductType.UNKNOWN.value:
        return False
    return True


def display_name_for_field(field_name: str) -> str:
    """Return a human-readable label without exposing a snake_case key."""

    return COMPLAINT_FIELD_DISPLAY_NAMES.get(
        field_name,
        field_name.replace("_", " ").title(),
    )


def _status_for_score(score: int) -> CompletenessStatus:
    if score >= 100:
        return CompletenessStatus.COMPLETE
    if score >= 75:
        return CompletenessStatus.MOSTLY_COMPLETE
    if score >= 40:
        return CompletenessStatus.INCOMPLETE
    return CompletenessStatus.INSUFFICIENT


class CompletenessService:
    """Calculate an explainable, deterministic intake completeness score."""

    def __init__(
        self,
        *,
        weights: Mapping[str, int] | None = None,
        critical_fields: tuple[str, ...] = COMPLETENESS_CRITICAL_FIELDS,
    ) -> None:
        resolved_weights = dict(
            COMPLETENESS_WEIGHTS if weights is None else weights
        )
        if not resolved_weights:
            raise ValueError("Completeness weights must not be empty.")
        if any(
            not isinstance(field_name, str)
            or not field_name
            or not isinstance(weight, int)
            or weight < 0
            for field_name, weight in resolved_weights.items()
        ):
            raise ValueError("Completeness weights must be non-negative integers.")
        total = sum(resolved_weights.values())
        if total != 100:
            raise ValueError("Completeness weights must total 100.")
        if any(field_name not in resolved_weights for field_name in critical_fields):
            raise ValueError("Critical completeness fields must have a weight.")
        self.weights = resolved_weights
        self.critical_fields = tuple(critical_fields)

    def check(self, complaint: ComplaintData) -> ComplaintCompleteness:
        """Return completeness for a validated complaint state."""

        validated = ComplaintData.model_validate(complaint)
        missing_fields = [
            field_name
            for field_name in self.weights
            if not is_known_value(getattr(validated, field_name, None))
        ]
        score = sum(
            weight
            for field_name, weight in self.weights.items()
            if field_name not in missing_fields
        )
        score = max(0, min(100, score))
        status = _status_for_score(score)
        missing_critical_fields = [
            field_name
            for field_name in self.critical_fields
            if field_name in missing_fields
        ]
        return ComplaintCompleteness(
            score=score,
            status=status,
            missing_fields=missing_fields,
            missing_critical_fields=missing_critical_fields,
            message=_COMPLETENESS_MESSAGES[status],
        )

    # Small aliases keep the service convenient for orchestration callers and
    # older assignment examples without duplicating the calculation.
    calculate = check
    assess = check
    check_completeness = check


def check_completeness(complaint: ComplaintData) -> ComplaintCompleteness:
    """Convenience function for deterministic callers and unit tests."""

    return CompletenessService().check(complaint)


calculate_completeness = check_completeness
ComplaintCompletenessService = CompletenessService


__all__ = [
    "COMPLAINT_FIELD_DISPLAY_NAMES",
    "COMPLETENESS_CRITICAL_FIELDS",
    "COMPLETENESS_WEIGHTS",
    "CompletenessService",
    "ComplaintCompletenessService",
    "calculate_completeness",
    "check_completeness",
    "display_name_for_field",
    "is_known_value",
]
