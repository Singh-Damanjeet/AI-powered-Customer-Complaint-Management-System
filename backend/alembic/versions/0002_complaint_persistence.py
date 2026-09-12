"""Add complaint persistence tables.

Revision ID: 0002_complaint_persistence
Revises: 0001_foundation
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_complaint_persistence"
down_revision: Union[str, None] = "0001_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def enum_type(*values: str, name: str) -> sa.Enum:
    """Build a portable value enum for PostgreSQL and SQLite migration tests."""

    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


jsonb_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    """Create complaint, assessment, and audit history tables."""

    op.create_table(
        "complaints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("complaint_number", sa.String(length=50), nullable=False),
        sa.Column("complaint_source", sa.String(length=100), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("complainant_name", sa.String(length=255), nullable=True),
        sa.Column("complainant_contact", sa.String(length=255), nullable=True),
        sa.Column(
            "product_type",
            enum_type("API", "FDF", "UNKNOWN", name="product_type"),
            nullable=True,
        ),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("product_strength_grade", sa.String(length=255), nullable=True),
        sa.Column("batch_lot_number", sa.String(length=255), nullable=True),
        sa.Column("manufacturing_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("quantity_affected", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("quantity_unit", sa.String(length=50), nullable=True),
        sa.Column("complaint_type", sa.String(length=255), nullable=True),
        sa.Column("complaint_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("detailed_description", sa.Text(), nullable=True),
        sa.Column(
            "severity",
            enum_type("Critical", "Major", "Minor", "Unknown", name="complaint_severity"),
            server_default="Unknown",
            nullable=False,
        ),
        sa.Column(
            "priority",
            enum_type("High", "Medium", "Low", "Unknown", name="complaint_priority"),
            server_default="Unknown",
            nullable=False,
        ),
        sa.Column(
            "status",
            enum_type(
                "DRAFT",
                "PENDING_TRIAGE",
                "UNDER_INVESTIGATION",
                "CLOSED",
                name="complaint_status",
            ),
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("complaint_number"),
    )
    op.create_index(
        "ix_complaints_complaint_number",
        "complaints",
        ["complaint_number"],
        unique=False,
    )

    op.create_table(
        "ai_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("complaint_id", sa.Integer(), nullable=False),
        sa.Column(
            "severity",
            enum_type("Critical", "Major", "Minor", "Unknown", name="assessment_severity"),
            nullable=False,
        ),
        sa.Column(
            "priority",
            enum_type("High", "Medium", "Low", "Unknown", name="assessment_priority"),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("recommended_actions", jsonb_type, nullable=False),
        sa.Column("qa_investigation_required", sa.Boolean(), nullable=True),
        sa.Column("product_replacement_recommended", sa.Boolean(), nullable=True),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["complaint_id"],
            ["complaints.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_assessments_complaint_id",
        "ai_assessments",
        ["complaint_id"],
        unique=False,
    )

    op.create_table(
        "complaint_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("complaint_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column(
            "source",
            enum_type("AI", "USER", "SYSTEM", name="audit_source"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["complaint_id"],
            ["complaints.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_complaint_audit_logs_complaint_id",
        "complaint_audit_logs",
        ["complaint_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop complaint persistence tables."""

    op.drop_index("ix_complaint_audit_logs_complaint_id", table_name="complaint_audit_logs")
    op.drop_table("complaint_audit_logs")
    op.drop_index("ix_ai_assessments_complaint_id", table_name="ai_assessments")
    op.drop_table("ai_assessments")
    op.drop_index("ix_complaints_complaint_number", table_name="complaints")
    op.drop_table("complaints")
