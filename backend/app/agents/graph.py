"""Compiled LangGraph orchestration for complaint logging."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.assess_risk import make_assess_risk_node
from app.agents.nodes.classify_intent import classify_intent_node
from app.agents.nodes.edit_complaint import make_edit_complaint_node
from app.agents.nodes.generate_response import generate_response_node
from app.agents.nodes.log_complaint import make_log_complaint_node
from app.agents.nodes.unsupported import (
    unsupported_for_now_node,
    unsupported_request_node,
    workflow_error_node,
)
from app.agents.nodes.validate_complaint import validate_complaint_node
from app.agents.router import (
    route_after_assess,
    route_after_edit,
    route_after_log,
    route_after_validate,
    route_by_intent,
)
from app.agents.state import ComplaintGraphState
from app.services.complaint_extraction_service import ComplaintExtractionService
from app.services.groq_service import GroqService
from app.services.risk_service import RiskService


def build_complaint_graph(
    extraction_service: ComplaintExtractionService | None = None,
    risk_service: RiskService | None = None,
    *,
    edit_service: Any | None = None,
    groq_service: GroqService | None = None,
    legacy_log_service: Any | None = None,
):
    """Build and compile one complaint graph with injected service objects.

    The dependencies are captured by node closures and never placed in the
    graph state. With no injected services, the existing Phase 4 services are
    constructed lazily when their nodes execute.
    """

    if groq_service is not None:
        extraction_service = extraction_service or ComplaintExtractionService(
            groq_service
        )
        risk_service = risk_service or RiskService(groq_service)

    if groq_service is not None:
        from app.services.edit_complaint_service import EditComplaintService

        edit_service = edit_service or EditComplaintService(
            groq_service=groq_service
        )

    builder = StateGraph(ComplaintGraphState)
    builder.add_node("classify_intent", classify_intent_node)
    builder.add_node(
        "log_complaint",
        make_log_complaint_node(
            extraction_service,
            groq_service=groq_service,
            legacy_log_service=legacy_log_service,
        ),
    )
    builder.add_node(
        "edit_complaint",
        make_edit_complaint_node(edit_service, groq_service=groq_service),
    )
    builder.add_node("validate_complaint", validate_complaint_node)
    builder.add_node(
        "assess_risk",
        make_assess_risk_node(risk_service, groq_service=groq_service),
    )
    builder.add_node("generate_response", generate_response_node)
    builder.add_node("unsupported_for_now", unsupported_for_now_node)
    builder.add_node("unsupported_request", unsupported_request_node)
    builder.add_node("workflow_error", workflow_error_node)

    builder.add_edge(START, "classify_intent")
    builder.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "log_complaint": "log_complaint",
            "edit_complaint": "edit_complaint",
            "unsupported_for_now": "unsupported_for_now",
            "unsupported_request": "unsupported_request",
            "workflow_error": "workflow_error",
        },
    )
    builder.add_conditional_edges(
        "log_complaint",
        route_after_log,
        {
            "validate_complaint": "validate_complaint",
            "workflow_error": "workflow_error",
        },
    )
    builder.add_conditional_edges(
        "edit_complaint",
        route_after_edit,
        {
            "validate_complaint": "validate_complaint",
            "workflow_error": "workflow_error",
        },
    )
    builder.add_conditional_edges(
        "validate_complaint",
        route_after_validate,
        {
            "assess_risk": "assess_risk",
            "generate_response": "generate_response",
            "workflow_error": "workflow_error",
        },
    )
    builder.add_conditional_edges(
        "assess_risk",
        route_after_assess,
        {
            "generate_response": "generate_response",
            "workflow_error": "workflow_error",
        },
    )
    builder.add_edge("generate_response", END)
    builder.add_edge("unsupported_for_now", END)
    builder.add_edge("unsupported_request", END)
    builder.add_edge("workflow_error", END)

    return builder.compile()


# A ready-to-use compiled graph for direct callers and future LangGraph nodes.
# It performs no provider or database work until invoked.
graph = build_complaint_graph()
complaint_graph = graph


__all__ = ["build_complaint_graph", "complaint_graph", "graph"]
