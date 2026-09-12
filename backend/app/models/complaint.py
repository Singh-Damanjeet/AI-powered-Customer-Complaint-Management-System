"""SQLAlchemy model for persisted complaints."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ComplaintStatus, persisted_enum
from app.schemas.complaint import Priority, ProductType, Severity

if TYPE_CHECKING:
    from app.models.ai_assessment import AIAssessment
    from app.models.audit_log import ComplaintAuditLog


class Complaint(Base):
    """Persisted complaint record."""

    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    complaint_source: Mapped[str | None] = mapped_column(String(100))
    customer_name: Mapped[str | None] = mapped_column(String(255))
    complainant_name: Mapped[str | None] = mapped_column(String(255))
    complainant_contact: Mapped[str | None] = mapped_column(String(255))
    product_type: Mapped[ProductType | None] = mapped_column(
        persisted_enum(ProductType, "product_type"),
    )
    product_name: Mapped[str | None] = mapped_column(String(255))
    product_strength_grade: Mapped[str | None] = mapped_column(String(255))
    batch_lot_number: Mapped[str | None] = mapped_column(String(255))
    manufacturing_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    quantity_affected: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    quantity_unit: Mapped[str | None] = mapped_column(String(50))
    complaint_type: Mapped[str | None] = mapped_column(String(255))
    complaint_date: Mapped[date | None] = mapped_column(Date)
    received_date: Mapped[date | None] = mapped_column(Date)
    detailed_description: Mapped[str | None] = mapped_column(Text)

    severity: Mapped[Severity] = mapped_column(
        persisted_enum(Severity, "complaint_severity"),
        nullable=False,
        default=Severity.UNKNOWN,
        server_default=Severity.UNKNOWN.value,
    )
    priority: Mapped[Priority] = mapped_column(
        persisted_enum(Priority, "complaint_priority"),
        nullable=False,
        default=Priority.UNKNOWN,
        server_default=Priority.UNKNOWN.value,
    )
    status: Mapped[ComplaintStatus] = mapped_column(
        persisted_enum(ComplaintStatus, "complaint_status"),
        nullable=False,
        default=ComplaintStatus.DRAFT,
        server_default=ComplaintStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    ai_assessments: Mapped[list["AIAssessment"]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    audit_logs: Mapped[list["ComplaintAuditLog"]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
