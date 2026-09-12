"""AI-assisted complaint operations."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.ai import LogComplaintRequest
from app.schemas.complaint import ComplaintAgentResponse
from app.services.ai_errors import AIResponseValidationError
from app.services.groq_service import (
    GroqConfigurationError,
    GroqProviderError,
    GroqResponseError,
    GroqServiceError,
)
from app.services.log_complaint_service import LogComplaintService


router = APIRouter(prefix="/ai", tags=["ai"])


def get_log_complaint_service() -> LogComplaintService:
    """Build the unsaved log complaint service for one request."""

    return LogComplaintService()


@router.post("/log-complaint", response_model=ComplaintAgentResponse)
async def log_complaint(
    request: LogComplaintRequest,
    service: LogComplaintService = Depends(get_log_complaint_service),
) -> ComplaintAgentResponse:
    """Extract and assess a complaint without persisting it."""

    try:
        return await service.process(request.message)
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


__all__ = ["get_log_complaint_service", "log_complaint", "router"]
