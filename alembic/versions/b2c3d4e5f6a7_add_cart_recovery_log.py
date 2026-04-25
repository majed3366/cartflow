"""add cart recovery log

Revision ID: b2c3d4e5f6a7
Revises: a3ff333f6d46
Create Date: 2026-04-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a3ff333f6d46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cart_recovery_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=512), nullable=False),
        sa.Column("cart_id", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=100), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cart_recovery_logs_store_slug", "cart_recovery_logs", ["store_slug"]
    )
    op.create_index(
        "ix_cart_recovery_logs_session_id", "cart_recovery_logs", ["session_id"]
    )
    op.create_index("ix_cart_recovery_logs_cart_id", "cart_recovery_logs", ["cart_id"])
    op.create_index("ix_cart_recovery_logs_status", "cart_recovery_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_cart_recovery_logs_status", table_name="cart_recovery_logs")
    op.drop_index("ix_cart_recovery_logs_cart_id", table_name="cart_recovery_logs")
    op.drop_index("ix_cart_recovery_logs_session_id", table_name="cart_recovery_logs")
    op.drop_index("ix_cart_recovery_logs_store_slug", table_name="cart_recovery_logs")
    op.drop_table("cart_recovery_logs")
