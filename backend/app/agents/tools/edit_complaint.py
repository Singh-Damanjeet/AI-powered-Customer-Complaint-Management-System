"""Structured, source-grounded natural-language complaint edit tool."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from app.agents.prompts.complaint_edit import (
    COMPLAINT_EDIT_SYSTEM_PROMPT,
    build_complaint_edit_prompt,
)
from app.schemas.complaint import ComplaintData, ComplaintPatch, ProductType
from app.services.ai_errors import AIResponseValidationError
from app.services.complaint_extraction_service import (
    normalize_complaint_type,
    normalize_quantity_unit,
    normalize_strength_grade,
)
from app.services.groq_service import GroqResponseError, GroqService
from app.services.structured_ai import generate_structured_response


_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "complaint_source": ("complaint source", "source"),
    "customer_name": ("customer name", "customer", "client name", "client"),
    "product_name": ("product name", "product"),
    "product_strength_grade": (
        "product strength",
        "strength",
        "strength grade",
    ),
    "batch_lot_number": ("batch lot number", "batch number", "batch", "lot number", "lot"),
    "manufacturing_date": (
        "manufacturing date",
        "manufacture date",
        "manufactured date",
    ),
    "expiry_date": ("expiry date", "expiration date", "expiry", "expiration"),
    "quantity_affected": (
        "quantity affected",
        "affected quantity",
        "quantity",
        "number affected",
    ),
    "quantity_unit": ("quantity unit", "unit", "tablets", "capsules"),
    "complaint_type": ("complaint type", "complaint category", "category", "type"),
    "complaint_date": ("complaint date", "reported date"),
    "received_date": ("received date", "date received"),
    "detailed_description": (
        "detailed description",
        "description",
        "complaint details",
        "details",
    ),
    "product_type": ("product type", "api", "fdf"),
    "complainant_name": ("complainant name", "complainant"),
    "complainant_contact": (
        "complainant contact",
        "contact information",
        "contact",
        "phone",
        "email",
    ),
}

_DISPLAY_NAMES = {
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

_CLEAR_PATTERN = re.compile(
    r"\b(?:remove|clear|delete|unset|erase|omit|unknown|not\s+provided|"
    r"wasn't\s+provided|was\s+not\s+provided|no\s+longer\s+known)\b",
    re.IGNORECASE,
)
_VAGUE_VALUE_WORDS = {
    "appropriate",
    "best",
    "better",
    "something",
    "tbd",
    "whatever",
}


def _normalized_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _contains_phrase(source: str, candidate: str) -> bool:
    source_text = _normalized_text(source)
    candidate_text = _normalized_text(candidate)
    return bool(candidate_text) and re.search(
        rf"(?<!\w){re.escape(candidate_text)}(?!\w)",
        source_text,
    ) is not None


def _field_is_mentioned(field_name: str, instruction: str) -> bool:
    return any(
        _contains_phrase(instruction, alias)
        for alias in _FIELD_ALIASES.get(field_name, (field_name,))
    )


def is_explicit_clear(field_name: str, instruction: str) -> bool:
    """Return whether the instruction clearly asks to clear one field."""

    return _field_is_mentioned(field_name, instruction) and bool(
        _CLEAR_PATTERN.search(instruction)
    )


def infer_edit_field(instruction: str) -> str | None:
    """Infer only the named target field for a safe ambiguity message."""

    candidates = sorted(
        (
            (alias, field_name)
            for field_name, aliases in _FIELD_ALIASES.items()
            for alias in aliases
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for alias, field_name in candidates:
        if _contains_phrase(instruction, alias):
            return field_name
    return None


def field_display_name(field_name: str) -> str:
    """Return a concise human-readable field label."""

    return _DISPLAY_NAMES.get(field_name, field_name.replace("_", " "))


def _date_is_explicit(value: date, instruction: str) -> bool:
    """Require a complete date representation before accepting an AI value."""

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
    return any(_contains_phrase(instruction, variant) for variant in variants)


def _quantity_is_explicit(value: Decimal, instruction: str) -> bool:
    number = format(value, "f")
    if "." in number:
        number = number.rstrip("0").rstrip(".") or "0"
    return re.search(
        rf"(?<![\d.]){re.escape(number)}(?!\.\d)(?!\d)",
        instruction.replace(",", ""),
    ) is not None


def _strength_is_explicit(value: str, instruction: str) -> bool:
    compact_source = re.sub(r"[^a-z0-9]+", "", instruction.casefold())
    compact_value = re.sub(r"[^a-z0-9]+", "", value.casefold())
    return bool(compact_value) and compact_value in compact_source


def _description_is_grounded(value: str, instruction: str, current: str | None) -> bool:
    """Allow only words supplied by the edit or already in current context."""

    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "be",
        "by",
        "is",
        "it",
        "of",
        "on",
        "reported",
        "that",
        "the",
        "to",
        "was",
        "were",
        "with",
    }
    source_tokens = set(re.findall(r"[a-z0-9]+", instruction.casefold()))
    source_tokens.update(re.findall(r"[a-z0-9]+", (current or "").casefold()))
    value_tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in stop_words
    ]
    return bool(value_tokens) and all(token in source_tokens for token in value_tokens)


def _value_is_grounded(
    field_name: str,
    value: object,
    instruction: str,
    current: ComplaintData,
) -> bool:
    if value is None:
        return is_explicit_clear(field_name, instruction)
    if field_name in {"manufacturing_date", "expiry_date", "complaint_date", "received_date"}:
        return isinstance(value, date) and _date_is_explicit(value, instruction)
    if field_name == "quantity_affected":
        return isinstance(value, Decimal) and _quantity_is_explicit(value, instruction)
    if field_name == "product_strength_grade":
        return isinstance(value, str) and _strength_is_explicit(value, instruction)
    if field_name == "quantity_unit" and isinstance(value, str):
        normalized = normalize_quantity_unit(value)
        return any(
            _contains_phrase(instruction, alias)
            for alias in (normalized or value, value, "tab", "tabs", "tablet", "tablets", "cap", "caps", "capsule", "capsules")
        )
    if field_name == "complaint_type" and isinstance(value, str):
        normalized = normalize_complaint_type(value) or value
        if _contains_phrase(instruction, value) or _contains_phrase(instruction, normalized):
            return True
        complaint_terms = {
            "discoloration": ("brown spot", "brown spots", "colour variation", "color variation"),
            "physical damage": ("broken", "cracked", "chipped", "damaged"),
            "foreign material": ("foreign", "glass", "metal fragment", "hair"),
            "labeling": ("label", "labelling", "mislabel"),
            "packaging": ("leaking", "broken seal", "damaged seal", "blister"),
        }
        return any(
            _contains_phrase(instruction, term)
            for term in complaint_terms.get(normalized.casefold(), ())
        )
    if field_name == "product_type" and isinstance(value, ProductType):
        return _contains_phrase(instruction, value.value)
    if field_name == "detailed_description" and isinstance(value, str):
        return _description_is_grounded(value, instruction, current.detailed_description)
    if isinstance(value, str):
        if _normalized_text(value) in _VAGUE_VALUE_WORDS:
            return False
        return _contains_phrase(instruction, value)
    return False


def _ground_patch(
    patch: ComplaintPatch,
    instruction: str,
    current: ComplaintData,
) -> ComplaintPatch:
    """Drop ungrounded model fields while preserving explicit null clears."""

    changes: dict[str, Any] = {}
    for field_name in ComplaintPatch.model_fields:
        if field_name not in patch.model_fields_set:
            continue
        value = getattr(patch, field_name)
        if _value_is_grounded(field_name, value, instruction, current):
            if field_name == "product_strength_grade" and isinstance(value, str):
                value = normalize_strength_grade(value)
            elif field_name == "quantity_unit" and isinstance(value, str):
                value = normalize_quantity_unit(value)
            elif field_name == "complaint_type" and isinstance(value, str):
                value = normalize_complaint_type(value)
            if field_name == "product_type" and value is ProductType.UNKNOWN:
                value = None
            changes[field_name] = value
    return ComplaintPatch.model_validate(changes)


class EditComplaintTool:
    """Extract a source-grounded, sparse ``ComplaintPatch`` with GroqService."""

    name = "edit_complaint"
    description = (
        "Extract only explicit natural-language updates to an existing "
        "pharmaceutical complaint as a ComplaintPatch."
    )

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

    async def extract_patch(
        self,
        current_complaint: ComplaintData,
        user_instruction: str,
    ) -> ComplaintPatch:
        """Return only grounded fields explicitly requested by the user."""

        current = ComplaintData.model_validate(current_complaint)
        if not isinstance(user_instruction, str) or not user_instruction.strip():
            raise ValueError("user_instruction must be a non-empty string.")

        service = self.groq_service or GroqService()
        last_error: Exception | None = None
        for _ in range(self.max_attempts):
            try:
                result = await generate_structured_response(
                    service,
                    build_complaint_edit_prompt(current, user_instruction.strip()),
                    ComplaintPatch,
                    system_prompt=COMPLAINT_EDIT_SYSTEM_PROMPT,
                    temperature=0.0,
                )
                patch = ComplaintPatch.model_validate(result)
                return _ground_patch(patch, user_instruction.strip(), current)
            except (GroqResponseError, ValidationError) as exc:
                last_error = exc

        raise AIResponseValidationError(
            "Complaint edit returned invalid structured data after retry."
        ) from last_error

    async def run(
        self,
        current_complaint: ComplaintData,
        user_instruction: str,
    ) -> ComplaintPatch:
        """Compatibility alias for tool callers."""

        return await self.extract_patch(current_complaint, user_instruction)

    async def __call__(
        self,
        current_complaint: ComplaintData,
        user_instruction: str,
    ) -> ComplaintPatch:
        return await self.extract_patch(current_complaint, user_instruction)


async def edit_complaint(
    current_complaint: ComplaintData,
    user_instruction: str,
    groq_service: GroqService | None = None,
) -> ComplaintPatch:
    """Extract a safe complaint patch without persisting or reassessing risk."""

    return await EditComplaintTool(groq_service=groq_service).extract_patch(
        current_complaint,
        user_instruction,
    )


__all__ = [
    "COMPLAINT_EDIT_SYSTEM_PROMPT",
    "EditComplaintTool",
    "edit_complaint",
    "field_display_name",
    "infer_edit_field",
    "is_explicit_clear",
]
