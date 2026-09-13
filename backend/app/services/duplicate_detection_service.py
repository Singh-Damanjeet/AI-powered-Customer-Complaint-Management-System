"""Explainable duplicate-complaint matching against saved records."""

from __future__ import annotations

from difflib import SequenceMatcher
from enum import Enum
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.schemas.complaint import ComplaintData
from app.schemas.insights import DuplicateDetectionResult, DuplicateMatch


# These are deliberately simple application heuristics. They are not a
# regulatory duplicate determination and must remain explainable to QA users.
DUPLICATE_SCORE_WEIGHTS = {
    "batch_lot_number": 40,
    "product_name": 25,
    "complaint_type": 15,
    "product_strength_grade": 10,
}
DUPLICATE_DESCRIPTION_MAX_SCORE = 10
DUPLICATE_THRESHOLD = 75
MAX_DUPLICATE_MATCHES = 5
DUPLICATE_CANDIDATE_LIMIT = 100


def normalize_match_text(value: Any) -> str:
    """Normalize comparable text without changing the stored complaint."""

    if isinstance(value, Enum):
        value = value.value
    if value is None:
        return ""
    return " ".join(str(value).casefold().split())


def _same_text(left: Any, right: Any) -> bool:
    left_value = normalize_match_text(left)
    return bool(left_value) and left_value == normalize_match_text(right)


def _safe_exclusion_id(value: int | str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _description_score(left: Any, right: Any) -> int:
    left_text = normalize_match_text(left)
    right_text = normalize_match_text(right)
    if not left_text or not right_text:
        return 0
    ratio = SequenceMatcher(None, left_text, right_text).ratio()
    return max(0, min(DUPLICATE_DESCRIPTION_MAX_SCORE, round(ratio * 10)))


def _matched_fields_and_score(
    complaint: ComplaintData,
    candidate: Complaint,
) -> tuple[int, list[str]]:
    score = 0
    matched_fields: list[str] = []
    comparisons = (
        ("batch_lot_number", DUPLICATE_SCORE_WEIGHTS["batch_lot_number"]),
        ("product_name", DUPLICATE_SCORE_WEIGHTS["product_name"]),
        ("complaint_type", DUPLICATE_SCORE_WEIGHTS["complaint_type"]),
        (
            "product_strength_grade",
            DUPLICATE_SCORE_WEIGHTS["product_strength_grade"],
        ),
    )
    for field_name, weight in comparisons:
        if _same_text(
            getattr(complaint, field_name, None),
            getattr(candidate, field_name, None),
        ):
            score += weight
            matched_fields.append(field_name)

    description_score = _description_score(
        complaint.detailed_description,
        candidate.detailed_description,
    )
    if description_score:
        score += description_score
        matched_fields.append("detailed_description")

    return max(0, min(100, score)), matched_fields


def _reason_for_match(matched_fields: list[str], score: int) -> str:
    labels = {
        "batch_lot_number": "the same batch/lot",
        "product_name": "the same product",
        "complaint_type": "the same complaint type",
        "product_strength_grade": "the same strength/grade",
        "detailed_description": "a similar description",
    }
    reasons = [labels[field_name] for field_name in matched_fields]
    if not reasons:
        return f"Possible duplicate based on a low-confidence match score of {score}%."
    if len(reasons) == 1:
        joined = reasons[0]
    elif len(reasons) == 2:
        joined = f"{reasons[0]} and {reasons[1]}"
    else:
        joined = ", ".join(reasons[:-1]) + f", and {reasons[-1]}"
    return f"Possible duplicate because it shares {joined} (score {score}%)."


class DuplicateDetectionService:
    """Find likely duplicates among saved complaints using narrow SQL queries."""

    def __init__(
        self,
        session: Session | None,
        *,
        threshold: int = DUPLICATE_THRESHOLD,
        max_matches: int = MAX_DUPLICATE_MATCHES,
        candidate_limit: int = DUPLICATE_CANDIDATE_LIMIT,
    ) -> None:
        if not 0 <= threshold <= 100:
            raise ValueError("Duplicate threshold must be between 0 and 100.")
        if not 1 <= max_matches <= 5:
            raise ValueError("Duplicate max_matches must be between 1 and 5.")
        if candidate_limit < 1:
            raise ValueError("Duplicate candidate_limit must be at least 1.")
        self.session = session
        self.threshold = threshold
        self.max_matches = max_matches
        self.candidate_limit = candidate_limit

    def _candidate_rows(
        self,
        complaint: ComplaintData,
        *,
        exclude_complaint_id: int | str | None = None,
    ) -> list[Complaint]:
        if self.session is None:
            return []

        # A complaint with no structured identity signal cannot be narrowed
        # safely. Returning no matches avoids a full-table scan and avoids
        # implying that a description-only coincidence is a duplicate.
        candidate_filters = []
        for field_name in (
            "batch_lot_number",
            "product_name",
            "complaint_type",
            "product_strength_grade",
        ):
            value = normalize_match_text(getattr(complaint, field_name, None))
            if value:
                column = getattr(Complaint, field_name)
                candidate_filters.append(func.lower(column) == value)
        if not candidate_filters:
            return []

        statement = (
            select(Complaint)
            .where(or_(*candidate_filters))
            .order_by(Complaint.created_at.desc(), Complaint.id.desc())
            .limit(self.candidate_limit)
        )
        exclusion_id = _safe_exclusion_id(exclude_complaint_id)
        if exclusion_id is not None:
            statement = statement.where(Complaint.id != exclusion_id)
        return list(self.session.scalars(statement).all())

    def find_matches(
        self,
        complaint: ComplaintData,
        *,
        exclude_complaint_id: int | str | None = None,
    ) -> DuplicateDetectionResult:
        """Return top explainable matches, including scores below the threshold."""

        validated = ComplaintData.model_validate(complaint)
        candidates = self._candidate_rows(
            validated,
            exclude_complaint_id=exclude_complaint_id,
        )
        scored: list[tuple[int, int, DuplicateMatch]] = []
        for candidate in candidates:
            score, matched_fields = _matched_fields_and_score(validated, candidate)
            complaint_id = int(candidate.id)
            complaint_number = str(candidate.complaint_number)
            scored.append(
                (
                    score,
                    complaint_id,
                    DuplicateMatch(
                        complaint_id=complaint_id,
                        complaint_number=complaint_number,
                        similarity_score=score,
                        matched_fields=matched_fields,
                        reason=_reason_for_match(matched_fields, score),
                    ),
                )
            )

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        matches = [item[2] for item in scored[: self.max_matches]]
        return DuplicateDetectionResult(
            possible_duplicate=any(
                match.similarity_score >= self.threshold for match in matches
            ),
            matches=matches,
        )

    # Aliases keep the service easy to use from orchestration and assignment
    # examples while retaining one implementation.
    detect = find_matches
    check = find_matches
    find_duplicates = find_matches
    detect_duplicates = find_matches


__all__ = [
    "DUPLICATE_CANDIDATE_LIMIT",
    "DUPLICATE_DESCRIPTION_MAX_SCORE",
    "DUPLICATE_SCORE_WEIGHTS",
    "DUPLICATE_THRESHOLD",
    "MAX_DUPLICATE_MATCHES",
    "DuplicateDetectionService",
    "normalize_match_text",
]
