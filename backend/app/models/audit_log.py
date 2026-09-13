"""SQLAlchemy model for complaint audit events."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import AuditSource, persisted_enum

if TYPE_CHECKING:
    from app.models.complaint import Complaint


class ComplaintAuditLog(Base):
    """Immutable history record for a complaint event or field change."""

    __tablename__ = "complaint_audit_logs"
    __table_args__ = (
        Index(
            "ix_complaint_audit_logs_complaint_created",
            "complaint_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(100))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    source: Mapped[AuditSource] = mapped_column(
        persisted_enum(AuditSource, "audit_source"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    complaint: Mapped["Complaint"] = relationship(back_populates="audit_logs")
