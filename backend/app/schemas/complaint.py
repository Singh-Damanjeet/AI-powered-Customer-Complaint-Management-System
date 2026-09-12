"""Typed domain contracts for complaint data and agent responses."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmptyText: TypeAlias = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
NonNegativeQuantity: TypeAlias = Annotated[Decimal, Field(ge=0)]


class ProductType(str, Enum):
    """Supported pharmaceutical product categories."""

    API = "API"
    FDF = "FDF"
    UNKNOWN = "UNKNOWN"


class Severity(str, Enum):
    """AI-assigned complaint severity."""

    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"
    UNKNOWN = "Unknown"


class Priority(str, Enum):
    """AI-assigned complaint priority."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNKNOWN = "Unknown"


class ComplaintFields(BaseModel):
    """Shared nullable complaint fields.

    Factual values are nullable because an incomplete complaint is valid while
    information is being gathered. Empty strings are rejected so they cannot
    be used as an alternative representation of missing data.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    complaint_source: NonEmptyText | None = None
    customer_name: NonEmptyText | None = None
    product_name: NonEmptyText | None = None
    product_strength_grade: NonEmptyText | None = None
    batch_lot_number: NonEmptyText | None = None
    manufacturing_date: date | None = None
    expiry_date: date | None = None
    quantity_affected: NonNegativeQuantity | None = None
    quantity_unit: NonEmptyText | None = None
    complaint_type: NonEmptyText | None = None
    complaint_date: date | None = None
    detailed_description: NonEmptyText | None = None

    product_type: ProductType | None = None
    received_date: date | None = None
    complainant_name: NonEmptyText | None = None
    complainant_contact: NonEmptyText | None = None


class ComplaintData(ComplaintFields):
    """Complete complaint state.

    All fields are represented in the model even when their factual values are
    not known yet; unknown values are ``None`` rather than empty strings.
    """


class ComplaintPatch(ComplaintFields):
    """Natural-language update payload for an existing complaint.

    Every field is optional. Consumers must use ``model_dump(exclude_unset=True)``
    (or ``as_update_dict``) when applying a patch so omitted fields remain
    untouched. An explicitly supplied ``None`` remains an intentional update.
    """

    def as_update_dict(self) -> dict[str, object]:
        """Return only fields explicitly supplied in this patch."""

        return self.model_dump(exclude_unset=True)


class RiskAssessment(BaseModel):
    """AI-derived risk classification and recommended response."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    severity: Severity = Severity.UNKNOWN
    priority: Priority = Priority.UNKNOWN
    rationale: NonEmptyText | None = None
    recommended_actions: list[NonEmptyText] = Field(default_factory=list)
    qa_investigation_required: bool | None = None
    product_replacement_recommended: bool | None = None


class ComplaintAgentResponse(BaseModel):
    """Stable response envelope returned by future complaint agents."""

    model_config = ConfigDict(extra="forbid")

    complaint: ComplaintData
    risk_assessment: RiskAssessment
    assistant_message: str = ""
    changed_fields: list[str] = Field(default_factory=list)
