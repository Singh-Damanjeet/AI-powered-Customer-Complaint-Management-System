"""Factual complaint extraction through the Phase 3 GroqService."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from pydantic import ValidationError

from app.agents.prompts.complaint_extraction import (
    COMPLAINT_EXTRACTION_SYSTEM_PROMPT,
    build_complaint_extraction_prompt,
)
from app.schemas.complaint import ComplaintData, ProductType
from app.services.ai_errors import AIResponseValidationError
from app.services.groq_service import GroqResponseError, GroqService
from app.services.structured_ai import generate_structured_response


_STRENGTH_UNIT_PATTERN = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mg|mcg|µg|ug|kg|g|%)\b",
    re.IGNORECASE,
)

_QUANTITY_UNIT_NORMALIZATIONS = {
    "tab": "tablets",
    "tabs": "tablets",
    "tablet": "tablets",
    "tablets": "tablets",
    "cap": "capsules",
    "caps": "capsules",
    "capsule": "capsules",
    "capsules": "capsules",
}

_QUANTITY_UNIT_ALIASES = {
    "tablets": ("tab", "tabs", "tablet", "tablets"),
    "capsules": ("cap", "caps", "capsule", "capsules"),
}

_DESCRIPTION_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "by",
    "customer",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "reported",
    "the",
    "to",
    "was",
    "were",
    "with",
}

_COMPLAINT_TYPE_NORMALIZATIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Discoloration",
        (
            "brown spot",
            "brown spots",
            "color variation",
            "colour variation",
            "discoloration",
            "discolouration",
        ),
    ),
    (
        "Physical Damage",
        (
            "broken tablet",
            "cracked tablet",
            "chipped tablet",
            "damaged tablet",
            "physical damage",
            "physical defect",
        ),
    ),
    (
        "Foreign Material",
        (
            "foreign particle",
            "foreign object",
            "foreign material",
            "unknown material",
            "metal fragment",
            "glass",
            "hair",
            "unknown particle",
        ),
    ),
    (
        "Labeling",
        (
            "wrong label",
            "missing label",
            "incorrect label",
            "mislabel",
            "labelling",
            "labeling",
        ),
    ),
    (
        "Packaging",
        (
            "leaking bottle",
            "leaking",
            "broken seal",
            "damaged seal",
            "seals were damaged",
            "damaged blister",
            "open blister",
            "open blister pack",
            "packaging",
        ),
    ),
)


def normalize_strength_grade(value: str | None) -> str | None:
    """Apply safe spacing normalization to explicit strength units."""

    if value is None:
        return None

    def replace_unit(match: re.Match[str]) -> str:
        return f"{match.group('value')} {match.group('unit').lower()}"

    return _STRENGTH_UNIT_PATTERN.sub(replace_unit, value.strip())


def normalize_quantity_unit(value: str | None) -> str | None:
    """Normalize common explicit tablet/capsule abbreviations only."""

    if value is None:
        return None
    normalized = value.strip().casefold()
    return _QUANTITY_UNIT_NORMALIZATIONS.get(normalized, value.strip())


def normalize_complaint_type(value: str | None) -> str | None:
    """Map common explicit complaint wording to concise categories."""

    if value is None:
        return None
    normalized = value.strip().casefold()
    for category, terms in _COMPLAINT_TYPE_NORMALIZATIONS:
        if any(term in normalized for term in terms):
            return category
    return value.strip()


def normalize_extracted_complaint(complaint: ComplaintData) -> ComplaintData:
    """Normalize safe formatting while preserving unknown facts as ``None``."""

    values = complaint.model_dump(mode="python")
    values["product_strength_grade"] = normalize_strength_grade(
        values["product_strength_grade"]
    )
    values["quantity_unit"] = normalize_quantity_unit(values["quantity_unit"])
    values["complaint_type"] = normalize_complaint_type(values["complaint_type"])
    if values["product_type"] is ProductType.UNKNOWN:
        values["product_type"] = None
    return ComplaintData.model_validate(values)


def _contains_value(source_text: str, value: str) -> bool:
    """Check a normalized factual text value as a whole-word phrase."""

    source = " ".join(source_text.casefold().split())
    candidate = " ".join(value.casefold().split())
    return bool(candidate) and re.search(
        rf"(?<!\w){re.escape(candidate)}(?!\w)",
        source,
    ) is not None


def _contains_compact_value(source_text: str, value: str) -> bool:
    """Check values such as ``500 mg`` against source text ``500mg``."""

    source = re.sub(r"[^a-z0-9]+", "", source_text.casefold())
    candidate = re.sub(r"[^a-z0-9]+", "", value.casefold())
    return bool(candidate) and candidate in source


def _contains_quantity(source_text: str, value: Decimal) -> bool:
    """Check that an extracted quantity appears explicitly in source text."""

    number = format(value, "f")
    if "." in number:
        number = number.rstrip("0").rstrip(".") or "0"
    return re.search(
        rf"(?<![\d.]){re.escape(number)}(?![\d.])",
        source_text.replace(",", ""),
        flags=re.IGNORECASE,
    ) is not None


def _contains_date(source_text: str, value: date) -> bool:
    """Check common explicit date renderings without inferring a date."""

    variants = (
        value.isoformat(),
        value.strftime("%d/%m/%Y"),
        value.strftime("%m/%d/%Y"),
        value.strftime("%d-%m-%Y"),
        value.strftime("%m-%d-%Y"),
        value.strftime("%B %d, %Y"),
        value.strftime("%b %d, %Y"),
        value.strftime("%d %B %Y"),
        value.strftime("%d %b %Y"),
    )
    return any(_contains_value(source_text, variant) for variant in variants)


def _contains_quantity_unit(source_text: str, value: str) -> bool:
    """Check common safe aliases for an explicit quantity unit."""

    normalized = value.casefold().strip()
    aliases = _QUANTITY_UNIT_ALIASES.get(normalized, (normalized,))
    return any(_contains_value(source_text, alias) for alias in aliases)


def _contains_complaint_type(source_text: str, value: str) -> bool:
    """Check source wording behind a normalized complaint category."""

    normalized = value.casefold().strip()
    for category, terms in _COMPLAINT_TYPE_NORMALIZATIONS:
        if normalized == category.casefold():
            return any(_contains_value(source_text, term) for term in terms)
    return _contains_value(source_text, value)


def _description_is_grounded(source_text: str, value: str) -> bool:
    """Reject summaries containing factual tokens absent from the source."""

    source_tokens = set(re.findall(r"[a-z0-9]+", source_text.casefold()))
    description_tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in _DESCRIPTION_STOP_WORDS
    ]
    return bool(description_tokens) and all(
        token in source_tokens for token in description_tokens
    )


def _fact_is_grounded(field_name: str, value: object, source_text: str) -> bool:
    """Return whether one extracted factual value is supported by source text."""

    if value is None:
        return True
    if field_name == "quantity_affected" and isinstance(value, Decimal):
        return _contains_quantity(source_text, value)
    if field_name in {"manufacturing_date", "expiry_date", "complaint_date", "received_date"}:
        return isinstance(value, date) and _contains_date(source_text, value)
    if field_name == "product_strength_grade" and isinstance(value, str):
        return _contains_compact_value(source_text, value)
    if field_name == "quantity_unit" and isinstance(value, str):
        return _contains_quantity_unit(source_text, value)
    if field_name == "complaint_type" and isinstance(value, str):
        return _contains_complaint_type(source_text, value)
    if field_name == "detailed_description" and isinstance(value, str):
        return _description_is_grounded(source_text, value)
    if field_name == "product_type" and value is ProductType.UNKNOWN:
        return True
    if isinstance(value, ProductType):
        return _contains_value(source_text, value.value)
    if isinstance(value, str):
        return _contains_value(source_text, value)
    return False


def ground_extracted_complaint(
    complaint: ComplaintData,
    source_text: str,
) -> ComplaintData:
    """Null factual output that is not supported by the original narrative."""

    values = complaint.model_dump(mode="python")
    for field_name, value in values.items():
        if value is not None and not _fact_is_grounded(field_name, value, source_text):
            values[field_name] = None
    return ComplaintData.model_validate(values)


class ComplaintExtractionService:
    """Extract only factual complaint data using structured Groq output."""

    def __init__(
        self,
        groq_service: GroqService | None = None,
        *,
        max_attempts: int = 2,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        self.groq_service = groq_service
        self.max_attempts = max_attempts

    async def extract(self, complaint_text: str) -> ComplaintData:
        """Return validated facts, retrying malformed structured output once."""

        if not isinstance(complaint_text, str) or not complaint_text.strip():
            raise ValueError("complaint_text must be a non-empty string.")

        groq_service = self.groq_service or GroqService()
        last_error: Exception | None = None
        for _ in range(self.max_attempts):
            try:
                extracted = await generate_structured_response(
                    groq_service,
                    build_complaint_extraction_prompt(complaint_text.strip()),
                    ComplaintData,
                    system_prompt=COMPLAINT_EXTRACTION_SYSTEM_PROMPT,
                    temperature=0.0,
                )
                normalized = normalize_extracted_complaint(
                    ComplaintData.model_validate(extracted)
                )
                return ground_extracted_complaint(normalized, complaint_text.strip())
            except (GroqResponseError, ValidationError) as exc:
                last_error = exc

        raise AIResponseValidationError(
            "Complaint extraction returned invalid structured data after retry."
        ) from last_error


__all__ = [
    "ComplaintExtractionService",
    "ground_extracted_complaint",
    "normalize_complaint_type",
    "normalize_extracted_complaint",
    "normalize_quantity_unit",
    "normalize_strength_grade",
]
