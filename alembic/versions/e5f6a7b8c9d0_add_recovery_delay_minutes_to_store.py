"""add recovery_delay_minutes to stores

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-26

Optional per-store CartFlow quiet period in minutes (NULL = legacy Layer-B + recovery_delay).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("recovery_delay_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stores", "recovery_delay_minutes")
