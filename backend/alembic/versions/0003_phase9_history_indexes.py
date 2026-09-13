"""Add indexes used by complaint history endpoints.

Revision ID: 0003_phase9_history_indexes
Revises: 0002_complaint_persistence
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0003_phase9_history_indexes"
down_revision: Union[str, None] = "0002_complaint_persistence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Index chronological history lookups by complaint."""

    op.create_index(
        "ix_ai_assessments_complaint_created",
        "ai_assessments",
        ["complaint_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_complaint_audit_logs_complaint_created",
        "complaint_audit_logs",
        ["complaint_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove chronological history indexes."""

    op.drop_index(
        "ix_complaint_audit_logs_complaint_created",
        table_name="complaint_audit_logs",
    )
    op.drop_index(
        "ix_ai_assessments_complaint_created",
        table_name="ai_assessments",
    )
