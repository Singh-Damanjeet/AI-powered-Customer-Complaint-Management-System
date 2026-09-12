"""Application service for parsing and extracting complaints from documents."""

from __future__ import annotations

import inspect
from typing import Any

from app.agents.tools.document_extraction import DocumentExtractionTool
from app.schemas.complaint import ComplaintData
from app.services.document_parser import DocumentParserService
from app.services.groq_service import GroqService


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class DocumentComplaintService:
    """Parse a document and extract a validated complaint without saving it."""

    def __init__(
        self,
        parser: DocumentParserService | Any | None = None,
        extraction_service: Any | None = None,
        *,
        extraction_tool: DocumentExtractionTool | Any | None = None,
        groq_service: GroqService | Any | None = None,
    ) -> None:
        self.parser = parser or DocumentParserService()
        self.extraction_service = extraction_service
        self.extraction_tool = extraction_tool or DocumentExtractionTool(
            extraction_service=extraction_service,
            groq_service=groq_service,
        )

    async def parse(self, filename: str, content: bytes) -> str:
        """Parse one document through the configured parser."""

        result = self.parser.parse(filename, content)
        parsed = await _maybe_await(result)
        if not isinstance(parsed, str) or not parsed.strip():
            raise ValueError("document parser returned no usable text.")
        return parsed.strip()

    async def process(
        self,
        filename: str,
        content: bytes,
    ) -> tuple[str, ComplaintData]:
        """Return normalized document text and its extracted complaint."""

        document_text = await self.parse(filename, content)
        extractor = getattr(self.extraction_tool, "extract", None)
        if extractor is None:
            extractor = getattr(self.extraction_tool, "run", None)
        if extractor is None:
            raise TypeError("extraction_tool must provide extract or run.")
        complaint = await _maybe_await(extractor(document_text))
        return document_text, ComplaintData.model_validate(complaint)


__all__ = ["DocumentComplaintService"]
