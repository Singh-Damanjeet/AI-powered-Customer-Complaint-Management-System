"""AI-assisted complaint operations."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.services.complaint_graph_service import (
    ComplaintGraphService,
    ComplaintWorkflowError,
    UnsupportedComplaintIntentError,
)
from app.schemas.agent import AgentMessageRequest
from app.schemas.ai import LogComplaintRequest
from app.schemas.complaint import ComplaintAgentResponse
from app.services.ai_errors import AIResponseValidationError
from app.services.edit_complaint_service import EditComplaintService
from app.services.groq_service import (
    GroqConfigurationError,
    GroqProviderError,
    GroqResponseError,
    GroqServiceError,
)
from app.services.log_complaint_service import LogComplaintService


router = APIRouter(prefix="/ai", tags=["ai"])
agent_router = APIRouter(prefix="/agent", tags=["agent"])


def get_log_complaint_service() -> LogComplaintService:
    """Build the unsaved log complaint service for one request."""

    return LogComplaintService()


def get_complaint_graph_service(
    service: LogComplaintService = Depends(get_log_complaint_service),
) -> ComplaintGraphService:
    """Build the graph service while retaining Phase 4 service injection.

    Normal requests inject the Phase 4 extraction/risk dependencies into a
    freshly compiled graph. A non-``LogComplaintService`` test double is
    treated as a compatibility service by the graph's log node, so existing
    API tests remain valid while the endpoint still invokes LangGraph.
    """

    if isinstance(service, LogComplaintService):
        return ComplaintGraphService(
            extraction_service=service.extraction_service,
            risk_service=service.risk_service,
            edit_service=EditComplaintService(groq_service=service.groq_service),
            groq_service=service.groq_service,
        )
    return ComplaintGraphService(legacy_log_service=service)


async def _run_graph_request(
    graph_service: ComplaintGraphService,
    message: str,
    *,
    current_complaint=None,
) -> ComplaintAgentResponse:
    """Run shared graph requests and preserve stable public error responses."""

    try:
        return await graph_service.run(
            message,
            current_complaint=current_complaint,
        )
    except UnsupportedComplaintIntentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ComplaintWorkflowError as exc:
        error_status = {
            "AI_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI_RESPONSE_INVALID": status.HTTP_502_BAD_GATEWAY,
            "INVALID_INPUT": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_COMPLAINT": status.HTTP_422_UNPROCESSABLE_ENTITY,
        }.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise HTTPException(
            status_code=error_status,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
    "get_log_complaint_service",
    "agent_message",
    "agent_router",
    "log_complaint",
    "router",
]
