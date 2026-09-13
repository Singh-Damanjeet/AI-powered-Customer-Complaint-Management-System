"""Focused tests for Phase 10 optional complaint intelligence."""

import asyncio
from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.graph import build_complaint_graph
from app.agents.state import initial_complaint_graph_state
from app.database.base import Base
from app.models.complaint import Complaint
from app.models.enums import ComplaintStatus
from app.schemas.complaint import ComplaintData, RiskAssessment
from app.schemas.insights import (
    CAPARecommendations,
    ComplaintAIInsights,
    ComplaintSummary,
    CompletenessStatus,
    DuplicateDetectionResult,
    InvestigationSuggestion,
    RootCauseRecommendation,
)
from app.services.ai_errors import AIResponseValidationError
from app.services.capa_service import CAPAService
from app.services.complaint_insights_service import ComplaintInsightsService
from app.services.complaint_summary_service import ComplaintSummaryService
from app.services.completeness_service import (
    COMPLETENESS_WEIGHTS,
    CompletenessService,
)
from app.services.duplicate_detection_service import DuplicateDetectionService
from app.services.root_cause_service import RootCauseService


def run(coroutine):
    return asyncio.run(coroutine)


def complaint_data(**overrides) -> ComplaintData:
    values = {
        "complaint_source": "Customer email",
        "customer_name": "ABC Pharma",
        "product_type": "FDF",
        "product_name": "Metformin tablets",
        "product_strength_grade": "500 mg",
        "batch_lot_number": "MT24003",
        "manufacturing_date": date(2026, 1, 10),
        "expiry_date": date(2028, 1, 9),
        "quantity_affected": 120,
        "quantity_unit": "tablets",
        "complaint_type": "Discoloration",
        "complaint_date": date(2026, 2, 1),
        "received_date": date(2026, 2, 2),
        "detailed_description": "Brown discoloration was reported on tablets.",
        "complainant_name": "Asha Rao",
        "complainant_contact": "asha@example.com",
    }
    values.update(overrides)
    return ComplaintData(**values)


def risk_assessment() -> RiskAssessment:
    return RiskAssessment(
        severity="Major",
        priority="High",
        rationale="The reported quality defect requires QA review.",
        recommended_actions=["Inspect retained samples"],
        qa_investigation_required=True,
        product_replacement_recommended=False,
    )


class FakeStructuredAI:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def generate_structured_response(
        self,
        user_prompt,
        response_model,
        *,
        system_prompt,
        temperature,
    ):
        self.calls.append(
            {
                "prompt": user_prompt,
                "response_model": response_model,
                "system_prompt": system_prompt,
                "temperature": temperature,
            }
        )
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield database
    finally:
        database.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def add_saved_complaint(
    session: Session,
    *,
    complaint_number: str,
    **overrides,
) -> Complaint:
    data = complaint_data(**overrides)
    record = Complaint(
        complaint_number=complaint_number,
        complaint_source=data.complaint_source,
        customer_name=data.customer_name,
        complainant_name=data.complainant_name,
        complainant_contact=data.complainant_contact,
        product_type=data.product_type,
        product_name=data.product_name,
        product_strength_grade=data.product_strength_grade,
        batch_lot_number=data.batch_lot_number,
        manufacturing_date=data.manufacturing_date,
        expiry_date=data.expiry_date,
        quantity_affected=data.quantity_affected,
        quantity_unit=data.quantity_unit,
        complaint_type=data.complaint_type,
        complaint_date=data.complaint_date,
        received_date=data.received_date,
        detailed_description=data.detailed_description,
        severity="Unknown",
        priority="Unknown",
        status=ComplaintStatus.DRAFT,
    )
    session.add(record)
    session.commit()
    return record


def test_completeness_is_deterministic_and_weights_total_100() -> None:
    assert sum(COMPLETENESS_WEIGHTS.values()) == 100

    service = CompletenessService()
    complete = service.check(complaint_data())
    minimal = service.check(ComplaintData(detailed_description="Damaged tablets."))
    missing_identity = service.check(
        complaint_data(product_name=None, batch_lot_number=None)
    )

    assert complete.score == 100
    assert complete.status is CompletenessStatus.COMPLETE
    assert minimal.score == COMPLETENESS_WEIGHTS["detailed_description"]
    assert minimal.status is CompletenessStatus.INSUFFICIENT
    assert missing_identity.score == 64
    assert missing_identity.status is CompletenessStatus.INCOMPLETE
    assert missing_identity.missing_fields == ["product_name", "batch_lot_number"]
    assert missing_identity.missing_critical_fields == [
        "product_name",
        "batch_lot_number",
    ]


def test_completeness_uses_none_for_missing_and_rejects_invalid_score() -> None:
    assert CompletenessService().check(ComplaintData()).score == 0
    with pytest.raises(ValidationError):
        from app.schemas.insights import ComplaintCompleteness

        ComplaintCompleteness(
            score=101,
            status="COMPLETE",
            message="Invalid score",
        )


def test_duplicate_detection_scores_exact_match_and_excludes_self(session: Session) -> None:
    saved = add_saved_complaint(session, complaint_number="CMP-2026-0001")
    service = DuplicateDetectionService(session)

    result = service.find_matches(complaint_data())
    self_excluded = service.find_matches(
        complaint_data(),
        exclude_complaint_id=saved.id,
    )

    assert result.possible_duplicate is True
    assert result.matches[0].complaint_id == saved.id
    assert result.matches[0].similarity_score == 100
    assert {
        "batch_lot_number",
        "product_name",
        "complaint_type",
        "product_strength_grade",
        "detailed_description",
    } == set(result.matches[0].matched_fields)
    assert self_excluded.matches == []
    assert self_excluded.possible_duplicate is False


def test_duplicate_detection_returns_lower_score_for_different_batch(session: Session) -> None:
    add_saved_complaint(
        session,
        complaint_number="CMP-2026-0002",
        batch_lot_number="OTHER-BATCH",
        complaint_type="Packaging",
        detailed_description="A separate packaging seal issue was reported.",
    )

    result = DuplicateDetectionService(session).find_matches(complaint_data())

    assert result.matches
    assert result.matches[0].similarity_score < 75
    assert result.possible_duplicate is False


def test_duplicate_detection_limits_matches_to_five(session: Session) -> None:
    for index in range(7):
        add_saved_complaint(
            session,
            complaint_number=f"CMP-2026-{index + 10:04d}",
            detailed_description=f"Brown discoloration was reported on tablets {index}.",
        )

    result = DuplicateDetectionService(session).find_matches(complaint_data())

    assert len(result.matches) == 5


def test_summary_prompt_keeps_unknown_dates_null_and_rejects_hallucinated_date() -> None:
    complaint = complaint_data(manufacturing_date=None, expiry_date=None)
    fake = FakeStructuredAI(
        ComplaintSummary(summary="Metformin complaint dated 2029-03-14."),
    )

    with pytest.raises(AIResponseValidationError):
        run(ComplaintSummaryService(fake, max_attempts=1).summarize(complaint))

    assert '"expiry_date": null' in fake.calls[0]["prompt"]
    assert '"manufacturing_date": null' in fake.calls[0]["prompt"]
    assert "confirmed root cause" in fake.calls[0]["system_prompt"]


def test_summary_root_cause_and_capa_use_structured_safe_contracts() -> None:
    complaint = complaint_data()
    risk = risk_assessment()
    fake = FakeStructuredAI(
        ComplaintSummary(summary="ABC Pharma reported brown discoloration on Metformin tablets."),
        RootCauseRecommendation(
            suggestions=[
                InvestigationSuggestion(
                    category="Coating process variation",
                    rationale="Evaluate process records for variation.",
                )
            ]
        ),
        CAPARecommendations(
            immediate_actions=["Inspect retained samples"],
            investigation_actions=["Review the batch record"],
            preventive_actions=["Trend similar complaints"],
        ),
    )

    summary = run(ComplaintSummaryService(fake).summarize(complaint))
    investigation = run(RootCauseService(fake).recommend(complaint, risk))
    capa = run(CAPAService(fake).recommend(complaint, risk, investigation))

    assert summary.summary.startswith("ABC Pharma")
    assert investigation.suggestions[0].category == "Coating process variation"
    assert capa.immediate_actions == ["Inspect retained samples"]
    assert "potential investigation" in fake.calls[1]["system_prompt"].lower()
    assert "require QA review" in fake.calls[2]["system_prompt"]
    assert '"expiry_date"' in fake.calls[2]["prompt"]


class FailingOptionalService:
    def __init__(self, error_code: str):
        self.error_code = error_code
        self.calls = 0

    async def summarize(self, *_args, **_kwargs):
        self.calls += 1
        raise RuntimeError(self.error_code)

    async def recommend(self, *_args, **_kwargs):
        self.calls += 1
        raise RuntimeError(self.error_code)


class FixedSummaryService:
    async def summarize(self, complaint):
        return ComplaintSummary(summary=f"Summary for {complaint.product_name}.")


class FixedInvestigationService:
    async def recommend(self, complaint, risk):
        return RootCauseRecommendation(
            suggestions=[
                InvestigationSuggestion(
                    category="Process review",
                    rationale="Review relevant process records.",
                )
            ]
        )


class FixedCAPAService:
    async def recommend(self, complaint, risk, investigation):
        return CAPARecommendations(
            immediate_actions=["Inspect available samples"],
            investigation_actions=["Review the batch record"],
            preventive_actions=[],
        )


def test_insights_aggregator_isolates_optional_failures_and_keeps_completeness() -> None:
    summary = FailingOptionalService("summary unavailable")
    root = FailingOptionalService("root unavailable")
    capa = FailingOptionalService("capa unavailable")
    service = ComplaintInsightsService(
        summary_service=summary,
        root_cause_service=root,
        capa_service=capa,
    )

    result = run(service.analyze(complaint_data(), risk_assessment()))

    assert result.completeness.score == 100
    assert result.summary is None
    assert result.investigation_suggestions is None
    assert result.capa_recommendations is None
    assert result.insight_errors == [
        "summary_unavailable",
        "root_cause_unavailable",
        "capa_unavailable",
    ]


def test_minimal_complaint_skips_hypotheses_and_capa_without_groq() -> None:
    summary = FixedSummaryService()
    root = FixedInvestigationService()
    capa = FixedCAPAService()
    result = run(
        ComplaintInsightsService(
            summary_service=summary,
            root_cause_service=root,
            capa_service=capa,
        ).analyze(
            ComplaintData(detailed_description="Customer reported damaged tablets."),
            risk_assessment(),
        )
    )

    assert result.completeness.status is CompletenessStatus.INSUFFICIENT
    assert result.summary is not None
    assert result.investigation_suggestions is None
    assert result.capa_recommendations is None


class FakeExtraction:
    async def extract(self, _message):
        return complaint_data()


class FakeRisk:
    async def assess_risk(self, *, complaint, original_text):
        return risk_assessment()


class FakeInsights:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls = 0

    async def analyze(self, complaint, risk, *, exclude_complaint_id=None):
        self.calls += 1
        if self.error:
            raise self.error
        return ComplaintAIInsights(
            completeness=CompletenessService().check(complaint),
            duplicates=DuplicateDetectionResult(),
            summary=ComplaintSummary(summary="Factual complaint summary."),
        )

    def fallback(self, complaint, risk, *, exclude_complaint_id=None):
        return ComplaintAIInsights(
            completeness=CompletenessService().check(complaint),
            duplicates=DuplicateDetectionResult(),
            insight_errors=["insights_unavailable"],
        )


def test_langgraph_runs_insights_after_risk_and_optional_failure_is_non_blocking() -> None:
    working_insights = FakeInsights()
    graph = build_complaint_graph(
        extraction_service=FakeExtraction(),
        risk_service=FakeRisk(),
        insights_service=working_insights,
    )
    result = run(
        graph.ainvoke(
            initial_complaint_graph_state(
                "Customer reported brown discoloration on Metformin tablets."
            )
        )
    )

    assert result["workflow_status"] == "COMPLETED"
    assert result["risk_assessment"]["severity"] == "Major"
    assert result["ai_insights"]["completeness"]["score"] == 100
    assert working_insights.calls == 1

    failing_insights = FakeInsights(RuntimeError("optional failure"))
    failing_graph = build_complaint_graph(
        extraction_service=FakeExtraction(),
        risk_service=FakeRisk(),
        insights_service=failing_insights,
    )
    failed_optional_result = run(
        failing_graph.ainvoke(
            initial_complaint_graph_state(
                "Customer reported brown discoloration on Metformin tablets."
            )
        )
    )

    assert failed_optional_result["workflow_status"] == "COMPLETED"
    assert failed_optional_result["complaint"]["product_name"] == "Metformin tablets"
    assert failed_optional_result["risk_assessment"]["priority"] == "High"
    assert failed_optional_result["ai_insights"]["insight_errors"] == [
        "insights_unavailable"
    ]
