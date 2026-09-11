# -*- coding: utf-8 -*-
"""E10 movement_snapshots — birth 3270bc34. Not p2q3 (no-op lineage bridge).

Revision ID: e10mv030703a
Revises: e9sas070607a
Create Date: 2026-07-03
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e10mv030703a"
down_revision: Union[str, Sequence[str], None] = "e9sas070607a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "movement_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("merchant_id", sa.Integer(), nullable=True),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("recovery_key", sa.String(length=512), nullable=False),
        sa.Column("cart_id", sa.String(length=255), nullable=True),
        sa.Column("session_id", sa.String(length=512), nullable=True),
        sa.Column("provider_sent", sa.Boolean(), nullable=False),
        sa.Column("provider_sent_at", sa.DateTime(), nullable=True),
        sa.Column("reply_received", sa.Boolean(), nullable=False),
        sa.Column("reply_at", sa.DateTime(), nullable=True),
        sa.Column("continuation_started", sa.Boolean(), nullable=False),
        sa.Column("continuation_at", sa.DateTime(), nullable=True),
        sa.Column("returned_to_site", sa.Boolean(), nullable=False),
        sa.Column("returned_at", sa.DateTime(), nullable=True),
        sa.Column("passive_return_visit_count", sa.Integer(), nullable=False),
        sa.Column("passive_return_last_at", sa.DateTime(), nullable=True),
        sa.Column("purchase_detected", sa.Boolean(), nullable=False),
        sa.Column("purchase_at", sa.DateTime(), nullable=True),
        sa.Column("purchase_truth_id", sa.Integer(), nullable=True),
        sa.Column("last_movement_type", sa.String(length=64), nullable=True),
        sa.Column("last_movement_at", sa.DateTime(), nullable=True),
        sa.Column("movement_active", sa.Boolean(), nullable=False),
        sa.Column("movement_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recovery_key"),
    )
    op.create_index(
        "ix_movement_snapshots_merchant_id", "movement_snapshots", ["merchant_id"]
    )
    op.create_index(
        "ix_movement_snapshots_purchase_detected",
        "movement_snapshots",
        ["purchase_detected"],
    )
    op.create_index(
        "ix_movement_snapshots_last_movement_at",
        "movement_snapshots",
        ["last_movement_at"],
    )
    op.create_index(
        "ix_movement_snapshots_movement_active",
        "movement_snapshots",
        ["movement_active"],
    )
    op.create_index(
        "ix_movement_snapshots_merchant_recovery_key",
        "movement_snapshots",
        ["merchant_id", "recovery_key"],
    )
    op.create_index(
        "ix_movement_snapshots_store_slug_updated_at",
        "movement_snapshots",
        ["store_slug", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_movement_snapshots_store_slug_updated_at", table_name="movement_snapshots"
    )
    op.drop_index(
        "ix_movement_snapshots_merchant_recovery_key", table_name="movement_snapshots"
    )
    op.drop_index(
        "ix_movement_snapshots_movement_active", table_name="movement_snapshots"
    )
    op.drop_index(
        "ix_movement_snapshots_last_movement_at", table_name="movement_snapshots"
    )
    op.drop_index(
        "ix_movement_snapshots_purchase_detected", table_name="movement_snapshots"
    )
    op.drop_index("ix_movement_snapshots_merchant_id", table_name="movement_snapshots")
    op.drop_table("movement_snapshots")
