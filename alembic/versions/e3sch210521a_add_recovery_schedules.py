# -*- coding: utf-8 -*-
"""E3 recovery_schedules — birth body 11b89e3e, immediately before o1p2.

Revision ID: e3sch210521a
Revises: n2o3p4q5r6s7
Create Date: 2026-05-21
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3sch210521a"
down_revision: Union[str, Sequence[str], None] = "n2o3p4q5r6s7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recovery_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recovery_key", sa.String(length=512), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=512), nullable=False),
        sa.Column("cart_id", sa.String(length=255), nullable=True),
        sa.Column("reason_tag", sa.String(length=128), nullable=True),
        sa.Column("customer_phone", sa.String(length=100), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("effective_delay_seconds", sa.Float(), nullable=False),
        sa.Column("delay_source", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("multi_slot_index", sa.Integer(), nullable=False),
        sa.Column("sequential_attempt_index", sa.Integer(), nullable=True),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("last_error", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recovery_schedules_recovery_key", "recovery_schedules", ["recovery_key"]
    )
    op.create_index(
        "ix_recovery_schedules_store_slug", "recovery_schedules", ["store_slug"]
    )
    op.create_index(
        "ix_recovery_schedules_session_id", "recovery_schedules", ["session_id"]
    )
    op.create_index("ix_recovery_schedules_cart_id", "recovery_schedules", ["cart_id"])
    op.create_index("ix_recovery_schedules_due_at", "recovery_schedules", ["due_at"])
    op.create_index("ix_recovery_schedules_status", "recovery_schedules", ["status"])


def downgrade() -> None:
    op.drop_index("ix_recovery_schedules_status", table_name="recovery_schedules")
    op.drop_index("ix_recovery_schedules_due_at", table_name="recovery_schedules")
    op.drop_index("ix_recovery_schedules_cart_id", table_name="recovery_schedules")
    op.drop_index("ix_recovery_schedules_session_id", table_name="recovery_schedules")
    op.drop_index("ix_recovery_schedules_store_slug", table_name="recovery_schedules")
    op.drop_index("ix_recovery_schedules_recovery_key", table_name="recovery_schedules")
    op.drop_table("recovery_schedules")
