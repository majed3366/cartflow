# -*- coding: utf-8 -*-
"""Store Reality Simulator V1 Phase 3 — event ledger, archives, run metadata."""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "t2u3v4w5x6y7"
down_revision: Union[str, Sequence[str], None] = "s1t2u3v4w5x6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""

    op.add_column("simulation_runs", sa.Column("scale_profile", sa.String(32), nullable=True))
    op.add_column("simulation_runs", sa.Column("manifest_json", sa.Text(), nullable=True))
    op.add_column(
        "simulation_runs", sa.Column("reality_score_json", sa.Text(), nullable=True)
    )
    op.add_column(
        "simulation_runs", sa.Column("validation_report_json", sa.Text(), nullable=True)
    )
    op.add_column(
        "simulation_runs", sa.Column("plan_summary_json", sa.Text(), nullable=True)
    )
    op.add_column(
        "simulation_runs", sa.Column("throttle_state_json", sa.Text(), nullable=True)
    )
    op.add_column("simulation_runs", sa.Column("archived_at", sa.DateTime(), nullable=True))

    op.create_table(
        "simulation_event_ledger",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("simulation_run_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("simulated_event_id", sa.String(length=128), nullable=False),
        sa.Column("event_index", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("support", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scenario_id", sa.String(length=128), nullable=True),
        sa.Column("scenario_version", sa.String(length=32), nullable=True),
        sa.Column("scenario_revision", sa.Integer(), nullable=False),
        sa.Column("simulated_at", sa.DateTime(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "simulation_run_id",
            "simulated_event_id",
            name="uq_simulation_event_ledger_run_event",
        ),
    )

    op.create_table(
        "simulation_run_archives",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("simulation_run_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("archive_json", sa.Text(), nullable=False),
        sa.Column("archived_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "simulation_run_id", name="uq_simulation_run_archives_run_id"
        ),
    )

    if dialect == "sqlite":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_event_ledger_simulation_run_id "
            "ON simulation_event_ledger (simulation_run_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_event_ledger_status "
            "ON simulation_event_ledger (status)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_event_ledger_event_type "
            "ON simulation_event_ledger (event_type)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_event_ledger_run_status "
            "ON simulation_event_ledger (simulation_run_id, status)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_simulation_run_archives_simulation_run_id "
            "ON simulation_run_archives (simulation_run_id)"
        )
    else:
        op.create_index(
            "ix_simulation_event_ledger_simulation_run_id",
            "simulation_event_ledger",
            ["simulation_run_id"],
        )
        op.create_index(
            "ix_simulation_event_ledger_status", "simulation_event_ledger", ["status"]
        )
        op.create_index(
            "ix_simulation_event_ledger_event_type",
            "simulation_event_ledger",
            ["event_type"],
        )
        op.create_index(
            "ix_simulation_event_ledger_run_status",
            "simulation_event_ledger",
            ["simulation_run_id", "status"],
        )


def downgrade() -> None:
    op.drop_table("simulation_run_archives")
    op.drop_table("simulation_event_ledger")
    op.drop_column("simulation_runs", "archived_at")
    op.drop_column("simulation_runs", "throttle_state_json")
    op.drop_column("simulation_runs", "plan_summary_json")
    op.drop_column("simulation_runs", "validation_report_json")
    op.drop_column("simulation_runs", "reality_score_json")
    op.drop_column("simulation_runs", "manifest_json")
    op.drop_column("simulation_runs", "scale_profile")
