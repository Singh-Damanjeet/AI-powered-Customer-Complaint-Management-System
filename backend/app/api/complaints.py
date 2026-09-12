"""Complaint persistence endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.persistence import ComplaintCreateRequest, ComplaintResponse
from app.services.complaint_service import (
    ComplaintNotFoundError,
    ComplaintPersistenceError,
    ComplaintService,
    to_complaint_response,
)

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def create_complaint(
    request: ComplaintCreateRequest,
    database: Session = Depends(get_db),
) -> ComplaintResponse:
    """Persist a complaint and its initial assessment snapshot."""

    try:
        complaint = ComplaintService(database).create(request)
    except ComplaintPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return to_complaint_response(complaint)


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(
    complaint_id: int,
    database: Session = Depends(get_db),
) -> ComplaintResponse:
    """Retrieve a complaint and its latest persisted AI assessment."""

    try:
        complaint = ComplaintService(database).get(complaint_id)
    except ComplaintNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve complaint.",
        ) from exc
    return to_complaint_response(complaint)


@router.get("", response_model=list[ComplaintResponse])
def list_complaints(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    database: Session = Depends(get_db),
) -> list[ComplaintResponse]:
    """Retrieve persisted complaints ordered from newest to oldest."""

    try:
        complaints = ComplaintService(database).list(offset=offset, limit=limit)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve complaints.",
        ) from exc
    return [to_complaint_response(complaint) for complaint in complaints]
