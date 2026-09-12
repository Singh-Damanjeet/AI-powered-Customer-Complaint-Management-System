"""Risk-related Pydantic contracts."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.complaint import NonEmptyText, Priority, RiskAssessment, Severity


class RiskSignals(BaseModel):
    """Deterministic indicators supplied to the AI risk assessor."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    adverse_event_signal: bool = False
    serious_health_signal: bool = False
    foreign_material_signal: bool = False
    contamination_signal: bool = False
    wrong_strength_signal: bool = False
    labeling_signal: bool = False
    packaging_integrity_signal: bool = False
    product_damage_signal: bool = False
    large_quantity_signal: bool = False
    matched_terms: list[NonEmptyText] = Field(default_factory=list)
    missing_information: list[NonEmptyText] = Field(default_factory=list)


# Compatibility alias for the earlier Phase 4 scaffolding name.
RiskSignalAnalysis = RiskSignals

__all__ = [
    "Priority",
    "RiskAssessment",
    "RiskSignalAnalysis",
    "RiskSignals",
    "Severity",
]
