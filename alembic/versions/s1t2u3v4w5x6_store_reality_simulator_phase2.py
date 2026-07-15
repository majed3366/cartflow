# -*- coding: utf-8 -*-
"""Store Reality Simulator V1 Phase 2 — simulation_runs + simulation_row_index.

Merges dual heads (movement_snapshots + dashboard_snapshots_archive).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s1t2u3v4w5x6"
down_revision: Union[str, Sequence[str], None] = ("p2q3r4s5t6u7", "r4s5t6u7v8w9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""

    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("simulation_run_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("scenario_ids_json", sa.Text(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_day", sa.DateTime(), nullable=True),
        sa.Column("current_step", sa.Integer(), nullable=False),
        sa.Column("simulated_now", sa.DateTime(), nullable=True),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("accounting_json", sa.Text(), nullable=False),
        sa.Column("checkpoint_json", sa.Text(), nullable=False),
        sa.Column("progress_json", sa.Text(), nullable=False),
        sa.Column("errors_json", sa.Text(), nullable=False),
        sa.Column("warnings_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("simulation_run_id", name="uq_simulation_runs_run_id"),
    )

    op.create_table(
        "simulation_row_index",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("simulation_run_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("table_name", sa.String(length=128), nullable=False),
        sa.Column("row_pk", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "simulation_run_id",
            "table_name",
            "row_pk",
            name="uq_simulation_row_index_run_table_pk",
        ),
    )

    if dialect == "sqlite":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_runs_simulation_run_id "
            "ON simulation_runs (simulation_run_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_runs_store_slug "
            "ON simulation_runs (store_slug)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_runs_status "
            "ON simulation_runs (status)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_row_index_simulation_run_id "
            "ON simulation_row_index (simulation_run_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_row_index_store_slug "
            "ON simulation_row_index (store_slug)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_row_index_table_name "
            "ON simulation_row_index (table_name)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_row_index_run_table "
            "ON simulation_row_index (simulation_run_id, table_name)"
        )
    else:
        op.create_index(
            "ix_simulation_runs_simulation_run_id",
            "simulation_runs",
            ["simulation_run_id"],
        )
        op.create_index("ix_simulation_runs_store_slug", "simulation_runs", ["store_slug"])
        op.create_index("ix_simulation_runs_status", "simulation_runs", ["status"])
        op.create_index(
            "ix_simulation_row_index_simulation_run_id",
            "simulation_row_index",
            ["simulation_run_id"],
        )
        op.create_index(
            "ix_simulation_row_index_store_slug",
            "simulation_row_index",
            ["store_slug"],
        )
        op.create_index(
            "ix_simulation_row_index_table_name",
            "simulation_row_index",
            ["table_name"],
        )
        op.create_index(
            "ix_simulation_row_index_run_table",
            "simulation_row_index",
            ["simulation_run_id", "table_name"],
        )


def downgrade() -> None:
    op.drop_table("simulation_row_index")
    op.drop_table("simulation_runs")
