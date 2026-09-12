"""Schemas used by the health endpoint."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health endpoint response contract."""

    status: Literal["ok"]
    database: Literal["connected"]
