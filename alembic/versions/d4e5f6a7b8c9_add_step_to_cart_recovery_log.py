"""add step to cart recovery log

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7
Create Date: 2026-04-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cart_recovery_logs",
        sa.Column("step", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_cart_recovery_logs_step", "cart_recovery_logs", ["step"]
    )


def downgrade() -> None:
    op.drop_index("ix_cart_recovery_logs_step", table_name="cart_recovery_logs")
    op.drop_column("cart_recovery_logs", "step")
