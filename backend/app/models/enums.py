"""Enum values persisted by the complaint database models."""

from enum import Enum
from typing import TypeVar

from sqlalchemy import Enum as SQLAlchemyEnum


class ComplaintStatus(str, Enum):
    """Complaint lifecycle values stored in the complaints table."""

    DRAFT = "DRAFT"
    PENDING_TRIAGE = "PENDING_TRIAGE"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    CLOSED = "CLOSED"


class AuditSource(str, Enum):
    """Sources allowed for audit log entries."""

    AI = "AI"
    USER = "USER"
    SYSTEM = "SYSTEM"


EnumType = TypeVar("EnumType", bound=Enum)


def persisted_enum(enum_type: type[EnumType], name: str) -> SQLAlchemyEnum:
    """Create a portable SQLAlchemy enum that stores the public values."""

    return SQLAlchemyEnum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda enum: [member.value for member in enum],
    )
