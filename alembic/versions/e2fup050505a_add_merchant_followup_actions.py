# -*- coding: utf-8 -*-
"""E2 merchant_followup_actions — birth fb4d43bf.

Revision ID: e2fup050505a
Revises: e1rsn260426a
Create Date: 2026-05-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2fup050505a"
down_revision: Union[str, Sequence[str], None] = "e1rsn260426a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "merchant_followup_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("abandoned_cart_id", sa.Integer(), nullable=True),
        sa.Column("customer_phone", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("inbound_message", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["abandoned_cart_id"], ["abandoned_carts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_merchant_followup_actions_store_id",
        "merchant_followup_actions",
        ["store_id"],
    )
    op.create_index(
        "ix_merchant_followup_actions_abandoned_cart_id",
        "merchant_followup_actions",
        ["abandoned_cart_id"],
    )
    op.create_index(
        "ix_merchant_followup_actions_customer_phone",
        "merchant_followup_actions",
        ["customer_phone"],
    )
    op.create_index(
        "ix_merchant_followup_actions_status", "merchant_followup_actions", ["status"]
    )
    op.create_index(
        "ix_merchant_followup_actions_reason", "merchant_followup_actions", ["reason"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_merchant_followup_actions_reason", table_name="merchant_followup_actions"
    )
    op.drop_index(
        "ix_merchant_followup_actions_status", table_name="merchant_followup_actions"
    )
    op.drop_index(
        "ix_merchant_followup_actions_customer_phone",
        table_name="merchant_followup_actions",
    )
    op.drop_index(
        "ix_merchant_followup_actions_abandoned_cart_id",
        table_name="merchant_followup_actions",
    )
    op.drop_index(
        "ix_merchant_followup_actions_store_id", table_name="merchant_followup_actions"
    )
    op.drop_table("merchant_followup_actions")
