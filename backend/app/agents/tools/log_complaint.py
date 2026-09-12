"""Reusable log complaint tool for the complaint workflow."""

from __future__ import annotations

from app.schemas.complaint import ComplaintAgentResponse
from app.services.groq_service import GroqService
from app.services.log_complaint_service import LogComplaintService


class LogComplaintTool:
    """Callable facade around the in-memory log complaint service."""

    name = "log_complaint"
    description = (
        "Extract a natural-language pharmaceutical complaint and produce a "
        "preliminary AI risk assessment requiring QA review."
    )

    def __init__(
        self,
        service: LogComplaintService | None = None,
        groq_service: GroqService | None = None,
    ) -> None:
        if service is not None and groq_service is not None:
            raise ValueError("Provide either service or groq_service, not both.")
        self.service = service or LogComplaintService(groq_service=groq_service)

    async def run(self, user_message: str) -> ComplaintAgentResponse:
        """Process one natural-language complaint."""

        return await self.service.process(user_message)

    async def __call__(self, user_message: str) -> ComplaintAgentResponse:
        """Allow direct invocation by a future LangGraph node."""

        return await self.run(user_message)


async def log_complaint(
    user_message: str,
    groq_service: GroqService | None = None,
) -> ComplaintAgentResponse:
    """Run the reusable log complaint tool without saving to PostgreSQL."""

    return await LogComplaintService(groq_service=groq_service).process(user_message)


__all__ = ["LogComplaintTool", "log_complaint"]
