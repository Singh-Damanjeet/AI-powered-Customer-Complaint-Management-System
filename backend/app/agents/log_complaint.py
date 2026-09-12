"""Backward-compatible exports for the Phase 4 log complaint tool."""

from app.agents.prompts.complaint_extraction import (
    COMPLAINT_EXTRACTION_SYSTEM_PROMPT,
    build_complaint_extraction_prompt,
)
from app.agents.prompts.risk_assessment import (
    RISK_ASSESSMENT_SYSTEM_PROMPT,
    build_risk_assessment_prompt,
)
from app.agents.tools.log_complaint import LogComplaintTool, log_complaint
from app.schemas.risk import RiskSignals
from app.services.ai_errors import AIResponseValidationError
from app.services.log_complaint_service import LogComplaintService
from app.services.risk_service import RiskAssessmentService, RiskService

__all__ = [
    "AIResponseValidationError",
    "COMPLAINT_EXTRACTION_SYSTEM_PROMPT",
    "RISK_ASSESSMENT_SYSTEM_PROMPT",
    "LogComplaintService",
    "LogComplaintTool",
    "RiskAssessmentService",
    "RiskService",
    "RiskSignals",
    "build_complaint_extraction_prompt",
    "build_risk_assessment_prompt",
    "log_complaint",
]
