# -*- coding: utf-8 -*-
"""dashboard_snapshots_archive — Data Growth Governance Phase 3 cold storage."""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "r4s5t6u7v8w9"
down_revision: Union[str, Sequence[str], None] = "o1p2q3r4s5t6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""

    op.create_table(
        "dashboard_snapshots_archive",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_snapshot_id", sa.Integer(), nullable=False),
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
        sa.Column("archived_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    if dialect == "sqlite":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_dashboard_snapshots_archive_source_id "
            "ON dashboard_snapshots_archive (source_snapshot_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_dashboard_snapshots_archive_store_type_gen "
            "ON dashboard_snapshots_archive (store_slug, snapshot_type, generated_at)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_dashboard_snapshots_archive_archived_at "
            "ON dashboard_snapshots_archive (archived_at)"
        )
        return

    op.create_index(
        "ix_dashboard_snapshots_archive_source_id",
        "dashboard_snapshots_archive",
        ["source_snapshot_id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_dashboard_snapshots_archive_store_type_gen",
        "dashboard_snapshots_archive",
        ["store_slug", "snapshot_type", "generated_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_dashboard_snapshots_archive_archived_at",
        "dashboard_snapshots_archive",
        ["archived_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_dashboard_snapshots_archive_store_id",
        "dashboard_snapshots_archive",
        ["store_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""

    if dialect == "sqlite":
        op.execute("DROP INDEX IF EXISTS ix_dashboard_snapshots_archive_archived_at")
        op.execute("DROP INDEX IF EXISTS ix_dashboard_snapshots_archive_store_type_gen")
        op.execute("DROP INDEX IF EXISTS ix_dashboard_snapshots_archive_source_id")
    else:
        for name in (
            "ix_dashboard_snapshots_archive_store_id",
            "ix_dashboard_snapshots_archive_archived_at",
            "ix_dashboard_snapshots_archive_store_type_gen",
            "ix_dashboard_snapshots_archive_source_id",
        ):
            op.drop_index(name, table_name="dashboard_snapshots_archive", if_exists=True)
    op.drop_table("dashboard_snapshots_archive")
