"""add vip_cart_threshold to stores

Revision ID: v3w4x5y6z7a8
Revises: s9t0u1v2w3x4
Create Date: 2026-05-02

Optional SAR threshold for future VIP cart handling (NULL = disabled).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v3w4x5y6z7a8"
down_revision: Union[str, Sequence[str], None] = "s9t0u1v2w3x4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("vip_cart_threshold", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stores", "vip_cart_threshold")
