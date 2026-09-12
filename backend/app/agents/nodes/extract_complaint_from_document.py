"""LangGraph node for shared complaint extraction from parsed document text."""

from __future__ import annotations

from typing import Any

from app.agents.nodes.common import logger, maybe_await, workflow_error_update
from app.agents.tools.document_extraction import DocumentExtractionTool
from app.agents.state import ComplaintGraphState
from app.schemas.complaint import ComplaintData
from app.services.complaint_extraction_service import ComplaintExtractionService
from app.services.groq_service import GroqService


async def extract_complaint_from_document_node(
    state: ComplaintGraphState,
    extraction_service: ComplaintExtractionService | Any | None = None,
    *,
    groq_service: GroqService | Any | None = None,
) -> dict[str, Any]:
    """Run the existing factual extraction service against document text."""

    try:
        document_text = state.get("document_text")
        if not isinstance(document_text, str) or not document_text.strip():
            raise ValueError("document_text is required before complaint extraction.")
        tool = DocumentExtractionTool(
            extraction_service=extraction_service,
            groq_service=groq_service,
        )
        complaint = await maybe_await(tool.extract(document_text))
        complaint = ComplaintData.model_validate(complaint)
        logger.info("LangGraph node=extract_complaint_from_document completed")
        return {
            "complaint": complaint.model_dump(mode="json"),
            "legacy_processed": False,
        }
    except Exception as exc:
        return workflow_error_update(state, exc, phase="document_extraction")


def make_extract_complaint_from_document_node(
    extraction_service: ComplaintExtractionService | Any | None = None,
    *,
    groq_service: GroqService | Any | None = None,
):
    """Capture extraction dependencies outside serializable graph state."""

    async def node(state: ComplaintGraphState) -> dict[str, Any]:
        return await extract_complaint_from_document_node(
            state,
            extraction_service=extraction_service,
            groq_service=groq_service,
        )

    return node


extract_complaint_from_document = extract_complaint_from_document_node


__all__ = [
    "extract_complaint_from_document",
    "extract_complaint_from_document_node",
    "make_extract_complaint_from_document_node",
]
