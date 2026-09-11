# -*- coding: utf-8 -*-
"""E1 reason capture — abandonment_reason_logs + cart_recovery_reasons birth.

Revision ID: e1rsn260426a
Revises: mrgk1k2hd01a
Create Date: 2026-04-26

Birth: 83cb7edf / b3ad4a33. Later columns (sub_category, phone, source, …)
belong in follow-on ALTER revisions.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1rsn260426a"
down_revision: Union[str, Sequence[str], None] = "mrgk1k2hd01a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "abandonment_reason_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=512), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("custom_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_abandonment_reason_logs_store_slug",
        "abandonment_reason_logs",
        ["store_slug"],
    )
    op.create_index(
        "ix_abandonment_reason_logs_session_id",
        "abandonment_reason_logs",
        ["session_id"],
    )
    op.create_index(
        "ix_abandonment_reason_logs_reason", "abandonment_reason_logs", ["reason"]
    )

    op.create_table(
        "cart_recovery_reasons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=512), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("custom_text", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cart_recovery_reasons_store_slug", "cart_recovery_reasons", ["store_slug"]
    )
    op.create_index(
        "ix_cart_recovery_reasons_session_id", "cart_recovery_reasons", ["session_id"]
    )
    op.create_index("ix_cart_recovery_reasons_reason", "cart_recovery_reasons", ["reason"])


def downgrade() -> None:
    op.drop_index("ix_cart_recovery_reasons_reason", table_name="cart_recovery_reasons")
    op.drop_index("ix_cart_recovery_reasons_session_id", table_name="cart_recovery_reasons")
    op.drop_index("ix_cart_recovery_reasons_store_slug", table_name="cart_recovery_reasons")
    op.drop_table("cart_recovery_reasons")
    op.drop_index("ix_abandonment_reason_logs_reason", table_name="abandonment_reason_logs")
    op.drop_index(
        "ix_abandonment_reason_logs_session_id", table_name="abandonment_reason_logs"
    )
    op.drop_index(
        "ix_abandonment_reason_logs_store_slug", table_name="abandonment_reason_logs"
    )
    op.drop_table("abandonment_reason_logs")
