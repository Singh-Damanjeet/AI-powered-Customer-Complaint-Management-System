"""AI-assisted complaint operations."""

from collections.abc import Awaitable, Callable
from collections.abc import Generator

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.services.complaint_graph_service import (
    ComplaintGraphService,
    ComplaintWorkflowError,
    UnsupportedComplaintIntentError,
)
from app.services.complaint_insights_service import ComplaintInsightsService
from app.config import get_settings
from app.database.session import get_session_factory
from app.schemas.agent import AgentMessageRequest
from app.schemas.ai import LogComplaintRequest
from app.schemas.complaint import ComplaintAgentResponse
from app.services.ai_errors import AIResponseValidationError
from app.services.edit_complaint_service import EditComplaintService
from app.services.document_parser import (
    CorruptDocumentError,
    DocumentParserConfigurationError,
    DocumentParserError,
    DocumentTooLargeError,
    EmptyDocumentError,
    MAX_DOCUMENT_SIZE_BYTES,
    NoExtractableTextError,
    UnsupportedDocumentTypeError,
)
from app.services.groq_service import (
    GroqConfigurationError,
    GroqProviderError,
    GroqResponseError,
    GroqServiceError,
)
from app.services.log_complaint_service import LogComplaintService


router = APIRouter(prefix="/ai", tags=["ai"])
agent_router = APIRouter(prefix="/agent", tags=["agent"])

# Starlette renamed these constants; numeric fallbacks keep the API compatible
# with the minimum supported FastAPI/Starlette versions without emitting a
# deprecation warning during normal requests.
HTTP_422_UNPROCESSABLE_CONTENT = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
HTTP_413_CONTENT_TOO_LARGE = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)


def get_log_complaint_service() -> LogComplaintService:
    """Build the unsaved log complaint service for one request."""

    return LogComplaintService()


def get_optional_db() -> Generator[Session | None, None, None]:
    """Yield a DB session when configured without making AI intake depend on it.

    The core log/edit/document workflow is intentionally usable without a
    database in local development and in existing API tests. Duplicate
    detection simply returns no matches when no database is configured.
    """

    if not get_settings().database_url:
        yield None
        return

    try:
        session_factory = get_session_factory()
        database = session_factory()
    except Exception:
        yield None
        return

    try:
        yield database
    finally:
        database.close()


def get_complaint_graph_service(
    service: LogComplaintService = Depends(get_log_complaint_service),
    database: Session | None = Depends(get_optional_db),
) -> ComplaintGraphService:
    """Build the graph service while retaining Phase 4 service injection.

    Normal requests inject the Phase 4 extraction/risk dependencies into a
    freshly compiled graph. A non-``LogComplaintService`` test double is
    treated as a compatibility service by the graph's log node, so existing
    API tests remain valid while the endpoint still invokes LangGraph.
    """

    # Direct callers can invoke this dependency as a regular function; in
    # that case FastAPI's Depends marker is not a real session.
    resolved_database = database if isinstance(database, Session) else None
    if isinstance(service, LogComplaintService):
        return ComplaintGraphService(
            extraction_service=service.extraction_service,
            risk_service=service.risk_service,
            edit_service=EditComplaintService(groq_service=service.groq_service),
            groq_service=service.groq_service,
            insights_service=ComplaintInsightsService(
                session=resolved_database,
                groq_service=service.groq_service,
            ),
        )
    return ComplaintGraphService(
        legacy_log_service=service,
        insights_service=ComplaintInsightsService(
            session=resolved_database,
            groq_service=getattr(service, "groq_service", None),
        ),
    )


async def _run_graph_operation(
    operation: Callable[[], Awaitable[ComplaintAgentResponse]],
) -> ComplaintAgentResponse:
    """Run a graph operation and preserve stable public error responses."""

    try:
        return await operation()
    except UnsupportedComplaintIntentError as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ComplaintWorkflowError as exc:
        error_status = {
            "AI_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI_RESPONSE_INVALID": status.HTTP_502_BAD_GATEWAY,
            "INVALID_INPUT": HTTP_422_UNPROCESSABLE_CONTENT,
            "INVALID_COMPLAINT": HTTP_422_UNPROCESSABLE_CONTENT,
        }.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise HTTPException(
            status_code=error_status,
            detail=str(exc),
        ) from exc
    except (DocumentParserError, DocumentParserConfigurationError):
        # Document-specific status mapping is handled by the upload wrapper.
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except (GroqConfigurationError, GroqProviderError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is unavailable.",
        ) from exc
    except (GroqResponseError, AIResponseValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI response could not be validated.",
        ) from exc
    except GroqServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is unavailable.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process complaint.",
        ) from exc


async def _run_graph_request(
    graph_service: ComplaintGraphService,
    message: str,
    *,
    current_complaint=None,
) -> ComplaintAgentResponse:
    """Run a text graph request."""

    return await _run_graph_operation(
        lambda: graph_service.run(
            message,
            current_complaint=current_complaint,
        )
    )


async def _run_document_request(
    graph_service: ComplaintGraphService,
    filename: str,
    content: bytes,
) -> ComplaintAgentResponse:
    """Run a document graph request with parser-specific HTTP errors."""

    try:
        return await _run_graph_operation(
            lambda: graph_service.run_document(filename, content)
        )
    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except DocumentTooLargeError as exc:
        raise HTTPException(
            status_code=HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except (
        EmptyDocumentError,
        CorruptDocumentError,
        NoExtractableTextError,
        DocumentParserError,
    ) as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DocumentParserConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document parser is unavailable.",
        ) from exc


@agent_router.post("/document", response_model=ComplaintAgentResponse)
async def agent_document(
    file: UploadFile = File(...),
    graph_service: ComplaintGraphService = Depends(get_complaint_graph_service),
) -> ComplaintAgentResponse:
    """Parse an uploaded complaint document and run the shared graph."""

    try:
        content = await file.read(MAX_DOCUMENT_SIZE_BYTES + 1)
    except Exception as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Uploaded document could not be read.",
        ) from exc
    return await _run_document_request(graph_service, file.filename or "", content)


@router.post("/log-complaint", response_model=ComplaintAgentResponse)
async def log_complaint(
    request: LogComplaintRequest,
    graph_service: ComplaintGraphService = Depends(get_complaint_graph_service),
) -> ComplaintAgentResponse:
    """Run the unsaved complaint workflow through the compiled LangGraph."""

    return await _run_graph_request(graph_service, request.message)


@agent_router.post("/message", response_model=ComplaintAgentResponse)
async def agent_message(
    request: AgentMessageRequest,
    graph_service: ComplaintGraphService = Depends(get_complaint_graph_service),
) -> ComplaintAgentResponse:
    """Run a new complaint or edit an explicitly supplied current complaint."""

    return await _run_graph_request(
        graph_service,
        request.message,
        current_complaint=request.complaint,
    )


__all__ = [
    "get_complaint_graph_service",
    "get_optional_db",
    "get_log_complaint_service",
    "agent_message",
    "agent_document",
    "agent_router",
    "log_complaint",
    "router",
]
