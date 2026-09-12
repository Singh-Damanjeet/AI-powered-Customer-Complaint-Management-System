"""LangGraph node that makes normalized document text available downstream."""

from __future__ import annotations

from typing import Any

from app.agents.nodes.common import logger, maybe_await, workflow_error_update
from app.agents.state import ComplaintGraphState
from app.services.document_parser import (
    DocumentParserConfigurationError,
    DocumentParserError,
    DocumentParserService,
)


async def extract_document_node(
    state: ComplaintGraphState,
    document_parser_service: DocumentParserService | Any | None = None,
) -> dict[str, Any]:
    """Parse transient document bytes or validate text parsed before invocation."""

    try:
        document_text = state.get("document_text")
        if isinstance(document_text, str) and document_text.strip():
            logger.info("LangGraph node=extract_document reused parsed text")
            return {
                "document_text": document_text.strip(),
                "document_content": None,
            }

        filename = state.get("document_filename")
        content = state.get("document_content")
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("document_filename is required for document intake.")
        if not isinstance(content, (bytes, bytearray, memoryview)):
            raise ValueError("document_content is required for document intake.")

        parser = document_parser_service or DocumentParserService()
        parsed = await maybe_await(parser.parse(filename, bytes(content)))
        if not isinstance(parsed, str) or not parsed.strip():
            raise ValueError("document parser returned no usable text.")
        logger.info("LangGraph node=extract_document completed")
        return {
            "document_text": parsed.strip(),
            "document_filename": filename,
            "document_content": None,
        }
    except (DocumentParserError, DocumentParserConfigurationError):
        # Preserve parser-specific failures so the upload API can return the
        # appropriate 415/413/422 response without exposing a traceback.
        raise
    except Exception as exc:
        result = workflow_error_update(state, exc, phase="document")
        # Binary upload content is transient graph input and must not remain
        # available after a parser failure.
        result["document_content"] = None
        return result


def make_extract_document_node(
    document_parser_service: DocumentParserService | Any | None = None,
):
    """Capture parser dependencies outside serializable graph state."""

    async def node(state: ComplaintGraphState) -> dict[str, Any]:
        return await extract_document_node(
            state,
            document_parser_service=document_parser_service,
        )

    return node


extract_document = extract_document_node


__all__ = [
    "extract_document",
    "extract_document_node",
    "make_extract_document_node",
]
