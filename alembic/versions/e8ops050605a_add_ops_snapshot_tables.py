# -*- coding: utf-8 -*-
"""E8 ops snapshots — operational_control + db_ready birth 81c027e4 / 17acd6a3.

Revision ID: e8ops050605a
Revises: e7sid030603a
Create Date: 2026-06-05

Later db_ready columns belong in follow-on ALTER revisions.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8ops050605a"
down_revision: Union[str, Sequence[str], None] = "e7sid030603a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operational_control_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform_wa_paused", sa.Boolean(), nullable=False),
        sa.Column("platform_schedule_paused", sa.Boolean(), nullable=False),
        sa.Column("platform_continuation_paused", sa.Boolean(), nullable=False),
        sa.Column("provider_paused", sa.Boolean(), nullable=False),
        sa.Column("provider_id", sa.String(length=32), nullable=True),
        sa.Column("paused_stores_json", sa.Text(), nullable=False),
        sa.Column("paused_reasons_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "db_ready_operational_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("last_duration_ms", sa.Float(), nullable=False),
        sa.Column("worst_duration_ms", sa.Float(), nullable=False),
        sa.Column("avg_duration_ms", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("last_stage", sa.String(length=64), nullable=True),
        sa.Column("last_trace_id", sa.String(length=16), nullable=True),
        sa.Column("last_lock_wait_ms", sa.Float(), nullable=False),
        sa.Column("last_query_count", sa.Integer(), nullable=False),
        sa.Column("last_sql_ms", sa.Float(), nullable=False),
        sa.Column("last_success", sa.Boolean(), nullable=False),
        sa.Column("last_failure_message", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("db_ready_operational_snapshots")
    op.drop_table("operational_control_snapshots")
