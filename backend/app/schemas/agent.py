"""Contracts for the shared complaint agent endpoint."""

from pydantic import BaseModel, ConfigDict

from app.schemas.complaint import ComplaintAgentResponse, ComplaintData, NonEmptyText


class AgentMessageRequest(BaseModel):
    """Natural-language agent input with optional in-memory complaint state."""

    model_config = ConfigDict(extra="forbid")

    message: NonEmptyText
    complaint: ComplaintData | None = None


__all__ = ["AgentMessageRequest", "ComplaintAgentResponse"]
