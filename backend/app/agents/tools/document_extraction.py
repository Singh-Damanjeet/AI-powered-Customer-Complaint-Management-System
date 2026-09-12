"""Document-to-complaint extraction using the shared factual AI service."""

from __future__ import annotations

import inspect
from typing import Any

from app.schemas.complaint import ComplaintData
from app.services.complaint_extraction_service import ComplaintExtractionService
from app.services.groq_service import GroqService


class DocumentExtractionTool:
    """Callable facade that reuses ``ComplaintExtractionService``."""

    name = "document_extraction"
    description = (
        "Extract factual pharmaceutical complaint information from already "
        "parsed document text."
    )

    def __init__(
        self,
        extraction_service: ComplaintExtractionService | Any | None = None,
        *,
        groq_service: GroqService | Any | None = None,
    ) -> None:
        self.extraction_service = extraction_service
        self.groq_service = groq_service

    async def extract(self, document_text: str) -> ComplaintData:
        """Extract and validate complaint facts from plain document text."""

        if not isinstance(document_text, str) or not document_text.strip():
            raise ValueError("document_text must be a non-empty string.")
        service = self.extraction_service or ComplaintExtractionService(
            self.groq_service
        )
        result = service.extract(document_text.strip())
        if inspect.isawaitable(result):
            result = await result
        return ComplaintData.model_validate(result)

    async def run(self, document_text: str) -> ComplaintData:
        """Compatibility alias for future tool callers."""

        return await self.extract(document_text)

    async def __call__(self, document_text: str) -> ComplaintData:
        return await self.extract(document_text)


async def extract_document_complaint(
    document_text: str,
    extraction_service: ComplaintExtractionService | Any | None = None,
    *,
    groq_service: GroqService | Any | None = None,
) -> ComplaintData:
    """Reuse the existing complaint extraction contract for document text."""

    return await DocumentExtractionTool(
        extraction_service=extraction_service,
        groq_service=groq_service,
    ).extract(document_text)


__all__ = [
    "DocumentExtractionTool",
    "extract_document_complaint",
]
