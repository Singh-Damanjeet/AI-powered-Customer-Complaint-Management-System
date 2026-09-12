"""Backward-compatible exports for the Phase 4 log complaint service."""

from app.services.log_complaint_service import LogComplaintService, log_complaint
from app.services.risk_service import RiskAssessmentService, RiskService

__all__ = [
    "LogComplaintService",
    "RiskAssessmentService",
    "RiskService",
    "log_complaint",
]
