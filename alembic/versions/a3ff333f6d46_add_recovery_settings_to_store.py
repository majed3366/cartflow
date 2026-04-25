"""add recovery settings to store

Revision ID: a3ff333f6d46
Revises: 
Create Date: 2026-04-25 04:03:44.878960

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3ff333f6d46'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "stores",
        sa.Column(
            "recovery_delay",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("2"),
        ),
    )
    op.add_column(
        "stores",
        sa.Column(
            "recovery_delay_unit",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'minutes'"),
        ),
    )
    op.add_column(
        "stores",
        sa.Column(
            "recovery_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("stores", "recovery_attempts")
    op.drop_column("stores", "recovery_delay_unit")
    op.drop_column("stores", "recovery_delay")
