"""SQLAlchemy model for persisted AI assessment snapshots."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import persisted_enum
from app.models.types import JSONBType
from app.schemas.complaint import Priority, Severity

if TYPE_CHECKING:
    from app.models.complaint import Complaint


class AIAssessment(Base):
    """Immutable assessment result associated with a complaint."""

    __tablename__ = "ai_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    severity: Mapped[Severity] = mapped_column(
        persisted_enum(Severity, "assessment_severity"),
        nullable=False,
    )
    priority: Mapped[Priority] = mapped_column(
        persisted_enum(Priority, "assessment_priority"),
        nullable=False,
    )
    rationale: Mapped[str | None] = mapped_column(Text)
    recommended_actions: Mapped[list[str]] = mapped_column(
        JSONBType,
        nullable=False,
        default=list,
    )
    qa_investigation_required: Mapped[bool | None] = mapped_column(Boolean)
    product_replacement_recommended: Mapped[bool | None] = mapped_column(Boolean)
    model_name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    complaint: Mapped["Complaint"] = relationship(back_populates="ai_assessments")
