# -*- coding: utf-8 -*-
"""Follow-on ALTER: later create_all columns on db_ready_operational_snapshots.

Revision ID: f8altdbready1
Revises: f7altcrlog01a
Create Date: 2026-06-05

E8 birth is 17acd6a3 timing counters only. Later columns from
schema_db_ready_operational.py / 2713e0c7 startup warm + restart survival.

Runtime health / Admin Operations still read these — canonical ownership required.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f8altdbready1"
down_revision: Union[str, Sequence[str], None] = "f7altcrlog01a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("last_top_substage", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("last_top_substage_queries", sa.Integer(), nullable=False),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("last_top_substage_sql_ms", sa.Float(), nullable=False),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("last_top_substage_elapsed_ms", sa.Float(), nullable=False),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("top_substages_json", sa.Text(), nullable=False),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("stage_classifications_json", sa.Text(), nullable=False),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("startup_warm_status", sa.String(length=16), nullable=False),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("startup_warm_duration_ms", sa.Float(), nullable=False),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("startup_warm_error", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("last_request_cached_verification", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_startup_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_warm_completed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_first_dashboard_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_first_dashboard_duration_ms", sa.Float(), nullable=False),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_first_dashboard_cached_verification", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_first_dashboard_heavy_warm", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_first_dashboard_used_safe_path", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_survival_result", sa.String(length=8), nullable=False),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_survival_timing", sa.String(length=64), nullable=False),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_survival_protected", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_survival_reason", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "db_ready_operational_snapshots",
        sa.Column("restart_survival_evaluated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    for name in (
        "restart_survival_evaluated_at",
        "restart_survival_reason",
        "restart_survival_protected",
        "restart_survival_timing",
        "restart_survival_result",
        "restart_first_dashboard_used_safe_path",
        "restart_first_dashboard_heavy_warm",
        "restart_first_dashboard_cached_verification",
        "restart_first_dashboard_duration_ms",
        "restart_first_dashboard_at",
        "restart_warm_completed_at",
        "restart_startup_at",
        "last_request_cached_verification",
        "startup_warm_error",
        "startup_warm_duration_ms",
        "startup_warm_status",
        "stage_classifications_json",
        "top_substages_json",
        "last_top_substage_elapsed_ms",
        "last_top_substage_sql_ms",
        "last_top_substage_queries",
        "last_top_substage",
    ):
        op.drop_column("db_ready_operational_snapshots", name)
