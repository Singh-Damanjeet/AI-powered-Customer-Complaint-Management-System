"""Deterministic risk signals and AI-assisted complaint risk assessment."""

from __future__ import annotations

import re
from decimal import Decimal

from pydantic import ValidationError

from app.agents.prompts.risk_assessment import (
    RISK_ASSESSMENT_SYSTEM_PROMPT,
    build_risk_assessment_prompt,
)
from app.schemas.complaint import ComplaintData, RiskAssessment
from app.schemas.risk import RiskSignals
from app.services.ai_errors import AIResponseValidationError
from app.services.groq_service import GroqResponseError, GroqService
from app.services.structured_ai import generate_structured_response


# This is a configurable heuristic, not a regulatory or quality limit.
LARGE_QUANTITY_THRESHOLD = Decimal("100")

_NEGATION_PATTERN = re.compile(
    r"\b(?:no|not|without|denies|denied|none|never)\b(?:\W+\w+){0,5}\W*$",
    re.IGNORECASE,
)

_SIGNAL_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "adverse_event_signal",
        (
            "patient experienced",
            "patient reported",
            "adverse event",
            "nausea",
            "vomiting",
            "rash",
            "reaction",
            "injury",
        ),
    ),
    (
        "serious_health_signal",
        (
            "severe reaction",
            "severe vomiting",
            "serious harm",
            "life-threatening",
            "hospitalized",
            "hospitalised",
            "anaphylaxis",
            "fatal",
            "death",
        ),
    ),
    (
        "foreign_material_signal",
        (
            "foreign particle",
            "foreign object",
            "foreign material",
            "glass",
            "metal fragment",
            "hair",
            "unknown particle",
        ),
    ),
    (
        "contamination_signal",
        (
            "contamination",
            "microbial contamination",
            "mold",
            "mould",
            "fungal",
            "unusual growth",
        ),
    ),
    (
        "wrong_strength_signal",
        (
            "wrong strength",
            "incorrect strength",
            "strength mismatch",
            "wrong product",
            "incorrect product",
            "mixed product",
            "product mix-up",
            "product mixup",
        ),
    ),
    (
        "labeling_signal",
        (
            "wrong label",
            "missing label",
            "incorrect label",
            "mislabel",
            "mislabelled",
            "mislabeling",
            "labelling",
            "labeling",
        ),
    ),
    (
        "packaging_integrity_signal",
        (
            "broken seal",
            "damaged seal",
            "seals were damaged",
            "seals damaged",
            "leaking",
            "leak",
            "open blister",
            "open blister pack",
            "blister packs were open",
            "damaged blister",
            "punctured",
            "seal failure",
            "seal damaged",
        ),
    ),
    (
        "product_damage_signal",
        (
            "broken tablet",
            "broken tablets",
            "cracked tablet",
            "cracked tablets",
            "chipped tablet",
            "chipped tablets",
            "damaged tablet",
            "damaged tablets",
            "physical damage",
            "physical defect",
        ),
    ),
)

_MISSING_INFORMATION_FIELDS: tuple[tuple[str, str], ...] = (
    ("product_name", "product_name"),
    ("batch_lot_number", "batch_lot_number"),
    ("quantity_affected", "quantity_affected"),
    ("complaint_type", "complaint_type"),
    ("detailed_description", "detailed_description"),
)


def _term_is_negated(text: str, start: int) -> bool:
    """Detect simple negation immediately before a signal term."""

    prefix = text[max(0, start - 80) : start]
    # Keep a negation in the current clause from leaking across a sentence or
    # comma into an unrelated signal.
    prefix = re.split(r"[.!?,;:\n]", prefix)[-1]
    return bool(_NEGATION_PATTERN.search(prefix))


def _matching_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    """Return signal terms present in text and not covered by basic negation."""

    matches: list[str] = []
    for term in terms:
        for occurrence in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
            if _term_is_negated(text, occurrence.start()):
                continue
            matches.append(term)
            break
    return matches


def _missing_information(complaint: ComplaintData) -> list[str]:
    """List factual fields needed for responsible initial triage."""

    return [
        label
        for field_name, label in _MISSING_INFORMATION_FIELDS
        if getattr(complaint, field_name) is None
    ]


class RiskService:
    """Assess complaint risk after factual extraction has completed."""

    def __init__(
        self,
        groq_service: GroqService | None = None,
        *,
        max_attempts: int = 2,
        large_quantity_threshold: Decimal = LARGE_QUANTITY_THRESHOLD,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        if large_quantity_threshold < 0:
            raise ValueError("large_quantity_threshold must be non-negative.")
        self.groq_service = groq_service
        self.max_attempts = max_attempts
        self.large_quantity_threshold = large_quantity_threshold

    def detect_risk_signals(
        self,
        complaint: ComplaintData,
        original_text: str,
    ) -> RiskSignals:
        """Detect obvious source-grounded signals before AI risk reasoning."""

        validated_complaint = ComplaintData.model_validate(complaint)
        if not isinstance(original_text, str) or not original_text.strip():
            raise ValueError("original_text must be a non-empty string.")

        signal_values: dict[str, bool] = {}
        matched_terms: list[str] = []
        for field_name, terms in _SIGNAL_SPECS:
            terms_found = _matching_terms(original_text, terms)
            signal_values[field_name] = bool(terms_found)
            matched_terms.extend(terms_found)

        signal_values["large_quantity_signal"] = bool(
            validated_complaint.quantity_affected is not None
            and validated_complaint.quantity_affected >= self.large_quantity_threshold
        )

        return RiskSignals(
            **signal_values,
            matched_terms=list(dict.fromkeys(matched_terms)),
            missing_information=_missing_information(validated_complaint),
        )

    # Concise alias for future orchestration code.
    analyze = detect_risk_signals

    async def assess_risk(
        self,
        complaint: ComplaintData,
        original_text: str,
    ) -> RiskAssessment:
        """Return a validated preliminary AI risk assessment."""

        validated_complaint = ComplaintData.model_validate(complaint)
        signals = self.detect_risk_signals(validated_complaint, original_text)
        groq_service = self.groq_service or GroqService()
        last_error: Exception | None = None

        for _ in range(self.max_attempts):
            try:
                assessed = await generate_structured_response(
                    groq_service,
                    build_risk_assessment_prompt(
                        validated_complaint,
                        original_text.strip(),
                        signals,
                    ),
                    RiskAssessment,
                    system_prompt=RISK_ASSESSMENT_SYSTEM_PROMPT,
                    temperature=0.0,
                )
                assessment = RiskAssessment.model_validate(assessed)
                # A log-compliant risk result is always preliminary and must be
                # reviewed by QA, regardless of the model's optional boolean.
                return assessment.model_copy(update={"qa_investigation_required": True})
            except (GroqResponseError, ValidationError) as exc:
                last_error = exc

        raise AIResponseValidationError(
            "Risk assessment returned invalid structured data after retry."
        ) from last_error


RiskAssessmentService = RiskService


__all__ = [
    "LARGE_QUANTITY_THRESHOLD",
    "RiskAssessmentService",
    "RiskService",
]
