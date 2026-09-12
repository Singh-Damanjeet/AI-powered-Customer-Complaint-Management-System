"""Groq structured-output service.

This module provides the infrastructure used by later LangGraph workflows. It
does not create or modify complaints and is intentionally not wired into an
API route in this phase.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Protocol, TypeVar

from groq import Groq
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings


ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)

DEFAULT_SYSTEM_PROMPT = (
    "You are a structured data assistant for a pharmaceutical complaint "
    "management system. Return only information supported by the supplied "
    "input. Never invent factual complaint information; use null for an "
    "unknown factual value. Evaluative fields such as risk classification "
    "and recommended actions may be inferred only when supported by the "
    "input."
)
_MANDATORY_DATA_INTEGRITY_INSTRUCTION = (
    "Mandatory data-integrity rules: never invent factual complaint "
    "information. Use null for every factual value that is not present in "
    "the supplied input."
)


class GroqServiceError(RuntimeError):
    """Base error for failures raised by the structured Groq service."""


class GroqConfigurationError(GroqServiceError):
    """Raised when the service cannot be configured from environment settings."""


class GroqProviderError(GroqServiceError):
    """Raised when the Groq provider rejects or cannot complete a request."""


class GroqResponseError(GroqServiceError):
    """Raised when a provider response cannot be parsed into its Pydantic model."""


class _ChatCompletionsClient(Protocol):
    def create(self, **kwargs: Any) -> Any:
        """Create a non-streaming chat completion."""


class _ChatClient(Protocol):
    completions: _ChatCompletionsClient


class GroqClient(Protocol):
    chat: _ChatClient


_SCHEMA_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")


def _schema_name(response_model: type[BaseModel]) -> str:
    """Return a Groq-compatible name for a Pydantic response model."""

    name = _SCHEMA_NAME_PATTERN.sub("_", response_model.__name__).strip("_")
    return (name or "structured_response")[:64]


def _value(value: Any, key: str) -> Any:
    """Read a key from either an SDK object or a dictionary-shaped test double."""

    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _completion_content(completion: Any) -> str:
    """Extract non-empty assistant text from a Groq completion response."""

    choices = _value(completion, "choices")
    if not choices:
        raise GroqResponseError("Groq returned no completion choices.")

    message = _value(choices[0], "message")
    if message is None:
        raise GroqResponseError("Groq returned a completion without a message.")

    refusal = _value(message, "refusal")
    if refusal:
        raise GroqResponseError("Groq refused to produce the structured response.")

    content = _value(message, "content")
    if not isinstance(content, str) or not content.strip():
        raise GroqResponseError("Groq returned an empty structured response.")
    return content


class GroqService:
    """Generate and validate structured responses from Groq.

    The client is injectable so tests and future application services can use a
    fake client without making a network call. When no client is provided,
    ``GROQ_API_KEY`` and ``GROQ_MODEL`` are read through the existing settings
    object; no credentials or model names are hardcoded here.
    """

    def __init__(
        self,
        client: GroqClient | None = None,
        settings: Settings | None = None,
        *,
        model: str | None = None,
        strict: bool = False,
    ) -> None:
        resolved_settings = settings or get_settings()
        configured_model = model if model is not None else resolved_settings.groq_model
        if not isinstance(configured_model, str) or not configured_model.strip():
            raise GroqConfigurationError(
                "GROQ_MODEL must be configured before using the Groq service."
            )
        self.model = configured_model.strip()
        self.strict = strict

        if client is not None:
            self.client = client
            return

        api_key = resolved_settings.groq_api_key
        if not isinstance(api_key, str) or not api_key.strip():
            raise GroqConfigurationError(
                "GROQ_API_KEY must be configured before using the Groq service."
            )
        self.client = Groq(api_key=api_key.strip())

    def generate_structured_response(
        self,
        user_prompt: str,
        response_model: type[ResponseModelT],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> ResponseModelT:
        """Request a JSON-schema response and validate it with Pydantic.

        ``strict=False`` is the default because the Phase 1 domain contracts
        intentionally contain nullable and defaulted fields. Callers may opt
        into Groq strict mode for schemas that meet the provider's stricter
        requirements; Pydantic validation is still applied in either mode.
        """

        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise ValueError("user_prompt must be a non-empty string.")
        if not isinstance(response_model, type) or not issubclass(response_model, BaseModel):
            raise TypeError("response_model must be a Pydantic BaseModel class.")
        if not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            raise ValueError("temperature must be between 0 and 2.")

        if system_prompt is None:
            resolved_system_prompt = DEFAULT_SYSTEM_PROMPT
        else:
            if not isinstance(system_prompt, str) or not system_prompt.strip():
                raise ValueError("system_prompt must be a non-empty string.")
            resolved_system_prompt = (
                f"{system_prompt.strip()}\n\n{_MANDATORY_DATA_INTEGRITY_INSTRUCTION}"
            )

        messages = [
            {"role": "system", "content": resolved_system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": _schema_name(response_model),
                "strict": self.strict,
                "schema": response_model.model_json_schema(),
            },
        }

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format=response_format,
                temperature=temperature,
            )
        except Exception as exc:
            raise GroqProviderError("Unable to obtain a structured response from Groq.") from exc

        content = _completion_content(completion)
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise GroqResponseError("Groq returned invalid JSON for the structured response.") from exc

        if not isinstance(payload, dict):
            raise GroqResponseError("Groq structured response must be a JSON object.")

        try:
            return response_model.model_validate(payload)
        except ValidationError as exc:
            raise GroqResponseError(
                f"Groq response did not validate as {response_model.__name__}."
            ) from exc

    def complete(
        self,
        user_prompt: str,
        response_model: type[ResponseModelT],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> ResponseModelT:
        """Compatibility alias for ``generate_structured_response``."""

        return self.generate_structured_response(
            user_prompt,
            response_model,
            system_prompt=system_prompt,
            temperature=temperature,
        )


GroqStructuredAIService = GroqService


__all__ = [
    "DEFAULT_SYSTEM_PROMPT",
    "GroqClient",
    "GroqConfigurationError",
    "GroqProviderError",
    "GroqResponseError",
    "GroqService",
    "GroqServiceError",
    "GroqStructuredAIService",
]
