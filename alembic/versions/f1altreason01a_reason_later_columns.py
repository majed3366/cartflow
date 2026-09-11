# -*- coding: utf-8 -*-
"""Follow-on ALTER: later create_all columns on reason tables.

Revision ID: f1altreason01a
Revises: e13px090909a
Create Date: 2026-04-26

Birth CREATEs stay at E1 (reason VARCHAR(32), no later columns).

| COLUMN / CHANGE | FIRST COMMIT | OWNER | PROD | CONF |
|-----------------|--------------|-------|------|------|
| abandonment_reason_logs.sub_category | cee9752e 2026-04-26 | AbandonmentReasonLog | live | HIGH |
| cart_recovery_reasons.sub_category | cee9752e | CartRecoveryReason | live | HIGH |
| cart_recovery_reasons.reason 32→64 | later widget tags | CartRecoveryReason | live | HIGH |
| cart_recovery_reasons.customer_phone | schema_widget / reason API | CartRecoveryReason | live | HIGH |
| cart_recovery_reasons.source | schema_widget | CartRecoveryReason | live | HIGH |
| cart_recovery_reasons.created_at | schema_widget | CartRecoveryReason | live | HIGH |
| cart_recovery_reasons.user_rejected_help | 05f41db3 2026-04-30 | CartRecoveryReason | live | HIGH |
| cart_recovery_reasons.rejection_timestamp | 05f41db3 | CartRecoveryReason | live | HIGH |
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1altreason01a"
down_revision: Union[str, Sequence[str], None] = "e13px090909a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "abandonment_reason_logs",
        sa.Column("sub_category", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_abandonment_reason_logs_sub_category",
        "abandonment_reason_logs",
        ["sub_category"],
    )

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        # SQLite cannot ALTER COLUMN TYPE; VARCHAR length is not enforced there.
        op.alter_column(
            "cart_recovery_reasons",
            "reason",
            existing_type=sa.String(length=32),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
    op.add_column(
        "cart_recovery_reasons",
        sa.Column("customer_phone", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "cart_recovery_reasons",
        sa.Column("sub_category", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "cart_recovery_reasons",
        sa.Column("source", sa.String(length=32), nullable=False),
    )
    op.add_column(
        "cart_recovery_reasons",
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.add_column(
        "cart_recovery_reasons",
        sa.Column("user_rejected_help", sa.Boolean(), nullable=False),
    )
    op.add_column(
        "cart_recovery_reasons",
        sa.Column("rejection_timestamp", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_cart_recovery_reasons_sub_category",
        "cart_recovery_reasons",
        ["sub_category"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cart_recovery_reasons_sub_category", table_name="cart_recovery_reasons"
    )
    op.drop_column("cart_recovery_reasons", "rejection_timestamp")
    op.drop_column("cart_recovery_reasons", "user_rejected_help")
    op.drop_column("cart_recovery_reasons", "created_at")
    op.drop_column("cart_recovery_reasons", "source")
    op.drop_column("cart_recovery_reasons", "sub_category")
    op.drop_column("cart_recovery_reasons", "customer_phone")
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column(
            "cart_recovery_reasons",
            "reason",
            existing_type=sa.String(length=64),
            type_=sa.String(length=32),
            existing_nullable=False,
        )
    op.drop_index(
        "ix_abandonment_reason_logs_sub_category",
        table_name="abandonment_reason_logs",
    )
    op.drop_column("abandonment_reason_logs", "sub_category")
