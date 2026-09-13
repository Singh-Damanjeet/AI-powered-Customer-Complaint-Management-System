"""Optional complaint-insights stage for the LangGraph workflow."""

from __future__ import annotations

from typing import Any

from app.agents.nodes.common import logger, maybe_await
from app.agents.state import ComplaintGraphState
from app.schemas.complaint import ComplaintData, RiskAssessment
from app.schemas.insights import ComplaintAIInsights


async def generate_insights_node(
    state: ComplaintGraphState,
    insights_service: Any | None = None,
) -> dict[str, Any]:
    """Generate optional insights without changing mandatory workflow status."""

    if insights_service is None:
        return {}

    try:
        complaint = ComplaintData.model_validate(state.get("complaint"))
        risk_assessment = RiskAssessment.model_validate(state.get("risk_assessment"))
        metadata = state.get("metadata")
        exclude_complaint_id = (
            metadata.get("exclude_complaint_id")
            if isinstance(metadata, dict)
            else None
        )
        analyze = getattr(insights_service, "analyze", None)
        if analyze is None:
            raise TypeError("insights service does not provide analyze().")
        result = await maybe_await(
            analyze(
                complaint,
                risk_assessment,
                exclude_complaint_id=exclude_complaint_id,
            )
        )
        insights = ComplaintAIInsights.model_validate(result)
        logger.info(
            "LangGraph node=generate_insights completed completeness=%s",
            insights.completeness.score,
        )
        return {"ai_insights": insights.model_dump(mode="json")}
    except Exception as exc:
        # Bonus features are intentionally non-blocking. The deterministic
        # fallback still exposes completeness and any available DB matches.
        logger.warning(
            "LangGraph optional insights stage unavailable error_type=%s",
            type(exc).__name__,
            exc_info=True,
        )
        try:
            complaint = ComplaintData.model_validate(state.get("complaint"))
            risk_assessment = RiskAssessment.model_validate(state.get("risk_assessment"))
            fallback = getattr(insights_service, "fallback", None)
            if fallback is None:
                return {}
            metadata = state.get("metadata")
            exclude_complaint_id = (
                metadata.get("exclude_complaint_id")
                if isinstance(metadata, dict)
                else None
            )
            fallback_result = await maybe_await(
                fallback(
                    complaint,
                    risk_assessment,
                    exclude_complaint_id=exclude_complaint_id,
                )
            )
            insights = ComplaintAIInsights.model_validate(fallback_result)
            return {"ai_insights": insights.model_dump(mode="json")}
        except Exception as fallback_exc:
            logger.warning(
                "LangGraph optional insights fallback unavailable error_type=%s",
                type(fallback_exc).__name__,
                exc_info=True,
            )
            return {}


generate_insights = generate_insights_node


def make_generate_insights_node(insights_service: Any | None = None):
    """Capture the optional insights service outside serializable graph state."""

    async def node(state: ComplaintGraphState) -> dict[str, Any]:
        return await generate_insights_node(state, insights_service=insights_service)

    return node


__all__ = [
    "generate_insights",
    "generate_insights_node",
    "make_generate_insights_node",
]
