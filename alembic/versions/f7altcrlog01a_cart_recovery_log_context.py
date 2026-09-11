# -*- coding: utf-8 -*-
"""Follow-on ALTER: later create_all context columns on cart_recovery_logs.

Revision ID: f7altcrlog01a
Revises: f6altmauth01a
Create Date: 2026-05-21

C-class birth is b2c3; step is d4e5. Later context columns came from
schema_recovery_message_context.py / restart-survival work (11b89e3e era).

| COLUMN | FIRST OWNER | PROD | CONF |
|--------|-------------|------|------|
| recovery_key | CartRecoveryLog + schema_recovery_message_context | live | HIGH |
| reason_tag | same | live | HIGH |
| context_status | same | live | HIGH |
| context_json | same | live | HIGH |
| message_type | same | live | HIGH |
| source | same | live | HIGH |
| provider | same | live | HIGH |
| provider_message_sid | same | live | HIGH |
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7altcrlog01a"
down_revision: Union[str, Sequence[str], None] = "f6altmauth01a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cart_recovery_logs",
        sa.Column("recovery_key", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "cart_recovery_logs",
        sa.Column("reason_tag", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "cart_recovery_logs",
        sa.Column("context_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "cart_recovery_logs",
        sa.Column("context_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "cart_recovery_logs",
        sa.Column("message_type", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "cart_recovery_logs",
        sa.Column("source", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "cart_recovery_logs",
        sa.Column("provider", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "cart_recovery_logs",
        sa.Column("provider_message_sid", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_cart_recovery_logs_recovery_key", "cart_recovery_logs", ["recovery_key"]
    )
    op.create_index(
        "ix_cart_recovery_logs_context_status",
        "cart_recovery_logs",
        ["context_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cart_recovery_logs_context_status", table_name="cart_recovery_logs"
    )
    op.drop_index("ix_cart_recovery_logs_recovery_key", table_name="cart_recovery_logs")
    op.drop_column("cart_recovery_logs", "provider_message_sid")
    op.drop_column("cart_recovery_logs", "provider")
    op.drop_column("cart_recovery_logs", "source")
    op.drop_column("cart_recovery_logs", "message_type")
    op.drop_column("cart_recovery_logs", "context_json")
    op.drop_column("cart_recovery_logs", "context_status")
    op.drop_column("cart_recovery_logs", "reason_tag")
    op.drop_column("cart_recovery_logs", "recovery_key")
