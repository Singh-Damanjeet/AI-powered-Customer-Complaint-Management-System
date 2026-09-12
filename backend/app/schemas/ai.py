"""Pydantic contracts for AI-facing API operations."""

from pydantic import BaseModel, ConfigDict

from app.schemas.complaint import NonEmptyText


class LogComplaintRequest(BaseModel):
    """Natural-language input for the log complaint endpoint."""

    model_config = ConfigDict(extra="forbid")

    message: NonEmptyText


__all__ = ["LogComplaintRequest"]
