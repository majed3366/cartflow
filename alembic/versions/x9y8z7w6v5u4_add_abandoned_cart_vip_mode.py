"""add vip_mode to abandoned_carts

Revision ID: x9y8z7w6v5u4
Revises: v3w4x5y6z7a8
Create Date: 2026-05-02

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "x9y8z7w6v5u4"
down_revision = "v3w4x5y6z7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "abandoned_carts",
        sa.Column("vip_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("abandoned_carts", "vip_mode")
