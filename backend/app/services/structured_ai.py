"""Async adapter for the synchronous Phase 3 structured AI service."""

from __future__ import annotations

import asyncio
import inspect
from typing import TypeVar

from pydantic import BaseModel

from app.services.groq_service import GroqService


ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


async def generate_structured_response(
    groq_service: GroqService,
    user_prompt: str,
    response_model: type[ResponseModelT],
    *,
    system_prompt: str,
    temperature: float = 0.0,
) -> ResponseModelT:
    """Run the existing synchronous GroqService without blocking the event loop."""

    result = await asyncio.to_thread(
        groq_service.generate_structured_response,
        user_prompt,
        response_model,
        system_prompt=system_prompt,
        temperature=temperature,
    )
    if inspect.isawaitable(result):
        result = await result
    return result


__all__ = ["generate_structured_response"]
