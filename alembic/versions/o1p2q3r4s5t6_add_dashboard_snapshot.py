# -*- coding: utf-8 -*-
"""dashboard_snapshots table + hot-path indexes (Reliability Foundation P0)."""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o1p2q3r4s5t6"
down_revision: Union[str, Sequence[str], None] = "n2o3p4q5r6s7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""

    op.create_table(
        "dashboard_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("snapshot_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    if dialect == "sqlite":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_dashboard_snapshots_store_type_generated "
            "ON dashboard_snapshots (store_slug, snapshot_type, generated_at DESC)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_abandoned_carts_store_status_last_seen "
            "ON abandoned_carts (store_id, status, last_seen_at)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_recovery_schedules_store_slug_status_due "
            "ON recovery_schedules (store_slug, status, due_at)"
        )
        return

    op.create_index(
        "ix_dashboard_snapshots_store_type_generated",
        "dashboard_snapshots",
        ["store_slug", "snapshot_type", "generated_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_dashboard_snapshots_store_id",
        "dashboard_snapshots",
        ["store_id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_abandoned_carts_store_status_last_seen",
        "abandoned_carts",
        ["store_id", "status", "last_seen_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_recovery_schedules_store_slug_status_due",
        "recovery_schedules",
        ["store_slug", "status", "due_at"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""

    if dialect == "sqlite":
        op.execute("DROP INDEX IF EXISTS ix_recovery_schedules_store_slug_status_due")
        op.execute("DROP INDEX IF EXISTS ix_abandoned_carts_store_status_last_seen")
        op.execute("DROP INDEX IF EXISTS ix_dashboard_snapshots_store_type_generated")
    else:
        op.drop_index(
            "ix_recovery_schedules_store_slug_status_due",
            table_name="recovery_schedules",
            if_exists=True,
        )
        op.drop_index(
            "ix_abandoned_carts_store_status_last_seen",
            table_name="abandoned_carts",
            if_exists=True,
        )
        op.drop_index(
            "ix_dashboard_snapshots_store_id",
            table_name="dashboard_snapshots",
            if_exists=True,
        )
        op.drop_index(
            "ix_dashboard_snapshots_store_type_generated",
            table_name="dashboard_snapshots",
            if_exists=True,
        )
    op.drop_table("dashboard_snapshots")
