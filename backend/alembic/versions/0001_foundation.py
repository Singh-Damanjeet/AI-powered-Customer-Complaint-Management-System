"""Create the initial empty foundation revision."""

from typing import Sequence, Union


revision: str = "0001_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Leave the schema empty until complaint models are introduced."""


def downgrade() -> None:
    """Revert the empty foundation revision."""
