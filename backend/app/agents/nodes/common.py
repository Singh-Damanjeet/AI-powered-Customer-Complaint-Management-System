"""Small helpers shared by complaint graph nodes."""

from __future__ import annotations

import inspect
import logging
from typing import Any

from pydantic import ValidationError

from app.services.ai_errors import AIResponseValidationError
from app.services.groq_service import (
    GroqConfigurationError,
    GroqProviderError,
    GroqResponseError,
    GroqServiceError,
)


logger = logging.getLogger(__name__)


async def maybe_await(value: Any) -> Any:
    """Accept async production services and simple sync test doubles."""

    return await value if inspect.isawaitable(value) else value


def workflow_error_update(
    state: dict[str, Any],
    error: Exception,
    *,
    phase: str,
) -> dict[str, Any]:
    """Convert an internal node failure into safe serializable state."""

    if isinstance(error, (GroqResponseError, AIResponseValidationError)):
        code = "AI_RESPONSE_INVALID"
        message = "AI response could not be validated."
    elif isinstance(
        error,
        (GroqConfigurationError, GroqProviderError, GroqServiceError),
    ):
        code = "AI_UNAVAILABLE"
        message = "AI service is unavailable."
    elif isinstance(error, ValidationError):
        code = "INVALID_COMPLAINT" if phase == "validate" else "AI_RESPONSE_INVALID"
        message = (
            "Complaint data failed validation."
            if phase == "validate"
            else "AI response could not be validated."
        )
    elif isinstance(error, ValueError):
        code = "INVALID_INPUT" if phase in {"classify_intent", "log"} else "INVALID_COMPLAINT"
        message = (
            "Complaint input is invalid."
            if code == "INVALID_INPUT"
            else "Complaint data failed validation."
        )
    else:
        code = "INTERNAL_ERROR"
        message = "Unable to process complaint."

    logger.error(
        "LangGraph node failed phase=%s error_type=%s",
        phase,
        type(error).__name__,
        # Do not emit a meaningless ``NoneType: None`` traceback for
        # validation checks that construct an error without raising it.
        exc_info=error.__traceback__ is not None,
    )
    return {
        "errors": [*state.get("errors", []), message],
        "error_code": code,
        "workflow_status": "ERROR",
    }


__all__ = ["logger", "maybe_await", "workflow_error_update"]
