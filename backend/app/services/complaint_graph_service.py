"""Application service boundary for the compiled complaint LangGraph."""

from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.agents.graph import build_complaint_graph
from app.agents.state import ComplaintGraphState, initial_complaint_graph_state
from app.schemas.complaint import ComplaintAgentResponse, ComplaintData, RiskAssessment
from app.schemas.insights import ComplaintAIInsights
from app.services.ai_errors import AIResponseValidationError
from app.services.document_parser import (
    DocumentParserConfigurationError,
    DocumentParserError,
    DocumentParserService,
)
from app.services.groq_service import (
    GroqConfigurationError,
    GroqProviderError,
    GroqResponseError,
    GroqServiceError,
)


logger = logging.getLogger(__name__)


class ComplaintGraphError(RuntimeError):
    """Base class for clean failures at the graph service boundary."""


class UnsupportedComplaintIntentError(ComplaintGraphError):
    """Raised when a future workflow branch is not implemented yet."""


class ComplaintWorkflowError(ComplaintGraphError):
    """Raised when a graph invocation finishes in an error state."""

    def __init__(self, message: str, *, code: str = "INTERNAL_ERROR") -> None:
        super().__init__(message)
        self.code = code


_PUBLIC_MESSAGES = {
    "AI_UNAVAILABLE": "AI service is unavailable.",
    "AI_RESPONSE_INVALID": "AI response could not be validated.",
    "INVALID_INPUT": "Complaint input is invalid.",
    "INVALID_COMPLAINT": "Complaint data failed validation.",
    "INTERNAL_ERROR": "Unable to process complaint.",
}


def public_workflow_message(code: str | None) -> str:
    """Return a stable, non-sensitive message for an internal error code."""

    return _PUBLIC_MESSAGES.get(code or "", _PUBLIC_MESSAGES["INTERNAL_ERROR"])


class ComplaintGraphService:
    """Run the in-memory complaint workflow through LangGraph."""

    def __init__(
        self,
        graph: Any | None = None,
        *,
        extraction_service: Any | None = None,
        risk_service: Any | None = None,
        edit_service: Any | None = None,
        document_parser_service: Any | None = None,
        document_complaint_service: Any | None = None,
        groq_service: Any | None = None,
        legacy_log_service: Any | None = None,
        insights_service: Any | None = None,
    ) -> None:
        resolved_parser = document_parser_service
        if resolved_parser is None and document_complaint_service is not None:
            resolved_parser = getattr(document_complaint_service, "parser", None)
            if resolved_parser is None and hasattr(
                document_complaint_service,
                "parse",
            ):
                resolved_parser = document_complaint_service
        self.document_parser_service = (
            resolved_parser
            if resolved_parser is not None
            else DocumentParserService()
        )
        self.graph = graph if graph is not None else build_complaint_graph(
            extraction_service=extraction_service,
            risk_service=risk_service,
            edit_service=edit_service,
            document_parser_service=self.document_parser_service,
            groq_service=groq_service,
            legacy_log_service=legacy_log_service,
            insights_service=insights_service,
        )

    async def _invoke_state(
        self,
        initial_state: ComplaintGraphState,
    ) -> ComplaintAgentResponse:
        """Invoke one serializable graph state and validate its response."""

        logger.info("Complaint graph started")
        try:
            invoke_result = self.graph.ainvoke(initial_state)
            result = (
                await invoke_result
                if inspect.isawaitable(invoke_result)
                else invoke_result
            )
        except (GroqConfigurationError, GroqProviderError, GroqResponseError):
            # Actual graph nodes normally capture these into state. Preserve a
            # typed boundary for custom graph implementations as well.
            raise
        except AIResponseValidationError:
            raise
        except (DocumentParserError, DocumentParserConfigurationError):
            raise
        except GroqServiceError:
            raise
        except Exception as exc:
            logger.error(
                "Complaint graph invocation failed error_type=%s",
                type(exc).__name__,
                exc_info=True,
            )
            raise ComplaintWorkflowError(
                _PUBLIC_MESSAGES["INTERNAL_ERROR"],
                code="INTERNAL_ERROR",
            ) from exc

        if not isinstance(result, dict):
            raise ComplaintWorkflowError(
                _PUBLIC_MESSAGES["INTERNAL_ERROR"],
                code="INTERNAL_ERROR",
            )

        state = result
        status = state.get("workflow_status")
        if status == "UNSUPPORTED":
            message = state.get("assistant_message")
            raise UnsupportedComplaintIntentError(
                message
                if isinstance(message, str) and message
                else "This complaint workflow branch is not available yet."
            )

        errors = state.get("errors")
        if status == "ERROR" or errors:
            code = state.get("error_code")
            raise ComplaintWorkflowError(
                public_workflow_message(code),
                code=code if isinstance(code, str) else "INTERNAL_ERROR",
            )

        try:
            complaint = ComplaintData.model_validate(state.get("complaint"))
            risk_assessment = RiskAssessment.model_validate(
                state.get("risk_assessment")
            )
            assistant_message = state.get("assistant_message", "")
            changed_fields = state.get("changed_fields", [])
            if not isinstance(assistant_message, str):
                raise ValueError("assistant_message must be a string.")
            if not isinstance(changed_fields, list) or not all(
                isinstance(field_name, str) for field_name in changed_fields
            ):
                raise ValueError("changed_fields must be a list of strings.")
            ai_insights = None
            raw_ai_insights = state.get("ai_insights")
            if raw_ai_insights is not None:
                try:
                    ai_insights = ComplaintAIInsights.model_validate(raw_ai_insights)
                except (ValidationError, TypeError, ValueError):
                    # Optional insight output must never invalidate the core
                    # complaint/risk response.
                    logger.warning(
                        "Complaint graph returned invalid optional insights; omitting them."
                    )
            response = ComplaintAgentResponse(
                complaint=complaint,
                risk_assessment=risk_assessment,
                assistant_message=assistant_message,
                changed_fields=changed_fields,
                ai_insights=ai_insights,
            )
        except (ValidationError, ValueError, TypeError) as exc:
            logger.error(
                "Complaint graph returned invalid final state error_type=%s",
                type(exc).__name__,
                exc_info=True,
            )
            raise ComplaintWorkflowError(
                _PUBLIC_MESSAGES["INTERNAL_ERROR"],
                code="INTERNAL_ERROR",
            ) from exc

        logger.info("Complaint graph completed")
        return response

    async def run(
        self,
        user_message: str,
        current_complaint: ComplaintData | None = None,
    ) -> ComplaintAgentResponse:
        """Invoke the text/edit graph workflow."""

        if not isinstance(user_message, str) or not user_message.strip():
            raise ValueError("user_message must be a non-empty string.")

        validated_current = (
            ComplaintData.model_validate(current_complaint)
            if current_complaint is not None
            else None
        )
        initial_state = initial_complaint_graph_state(
            user_message.strip(),
            complaint=(
                validated_current.model_dump(mode="json")
                if validated_current is not None
                else None
            ),
        )
        return await self._invoke_state(initial_state)

    async def run_document(
        self,
        filename: str,
        content: bytes,
    ) -> ComplaintAgentResponse:
        """Parse and process one uploaded document through the graph."""

        safe_filename = (
            Path(filename.strip()).name
            if isinstance(filename, str)
            else ""
        )
        transient_content = (
            bytes(content)
            if isinstance(content, (bytes, bytearray, memoryview))
            else None
        )
        initial_state = initial_complaint_graph_state(
            "Process uploaded complaint document",
            document_filename=safe_filename,
            document_content=transient_content,
        )
        return await self._invoke_state(initial_state)

    async def process(
        self,
        user_message: str,
        current_complaint: ComplaintData | None = None,
    ) -> ComplaintAgentResponse:
        """Compatibility alias for service callers that use ``process``."""

        return await self.run(user_message, current_complaint=current_complaint)


__all__ = [
    "ComplaintGraphError",
    "ComplaintGraphService",
    "ComplaintWorkflowError",
    "UnsupportedComplaintIntentError",
    "public_workflow_message",
]
