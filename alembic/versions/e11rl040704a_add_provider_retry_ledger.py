# -*- coding: utf-8 -*-
"""E11 provider_retry_ledger — birth 3a5a2848.

Revision ID: e11rl040704a
Revises: e10mv030703a
Create Date: 2026-07-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e11rl040704a"
down_revision: Union[str, Sequence[str], None] = "e10mv030703a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_retry_ledger",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("correlation_key", sa.String(length=512), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=True),
        sa.Column("session_id", sa.String(length=512), nullable=True),
        sa.Column("cart_id", sa.String(length=255), nullable=True),
        sa.Column("customer_phone", sa.String(length=100), nullable=True),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_failure_class", sa.String(length=64), nullable=True),
        sa.Column("last_disposition", sa.String(length=32), nullable=True),
        sa.Column("last_error", sa.String(length=512), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("retry_after_until", sa.DateTime(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "correlation_key", "provider", "step", name="uq_provider_retry_ledger_key"
        ),
    )
    op.create_index(
        "ix_provider_retry_ledger_correlation_key",
        "provider_retry_ledger",
        ["correlation_key"],
    )
    op.create_index("ix_provider_retry_ledger_provider", "provider_retry_ledger", ["provider"])
    op.create_index(
        "ix_provider_retry_ledger_store_slug", "provider_retry_ledger", ["store_slug"]
    )
    op.create_index("ix_provider_retry_ledger_step", "provider_retry_ledger", ["step"])
    op.create_index("ix_provider_retry_ledger_status", "provider_retry_ledger", ["status"])
    op.create_index(
        "ix_provider_retry_ledger_next_attempt_at",
        "provider_retry_ledger",
        ["next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_retry_ledger_next_attempt_at", table_name="provider_retry_ledger"
    )
    op.drop_index("ix_provider_retry_ledger_status", table_name="provider_retry_ledger")
    op.drop_index("ix_provider_retry_ledger_step", table_name="provider_retry_ledger")
    op.drop_index("ix_provider_retry_ledger_store_slug", table_name="provider_retry_ledger")
    op.drop_index("ix_provider_retry_ledger_provider", table_name="provider_retry_ledger")
    op.drop_index(
        "ix_provider_retry_ledger_correlation_key", table_name="provider_retry_ledger"
    )
    op.drop_table("provider_retry_ledger")
