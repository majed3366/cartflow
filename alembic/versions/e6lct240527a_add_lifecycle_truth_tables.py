# -*- coding: utf-8 -*-
"""E6 lifecycle truth — PT / closure / timeline / cart archive births.

Revision ID: e6lct240527a
Revises: e5wad230523a
Create Date: 2026-05-27

Births: 915ebaa7, 8fe9bd0c, 26defaa6, c4bdfe53.
Do not alter Purchase Truth semantics.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6lct240527a"
down_revision: Union[str, Sequence[str], None] = "e5wad230523a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purchase_truth_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recovery_key", sa.String(length=512), nullable=False),
        sa.Column("purchase_detected", sa.Boolean(), nullable=False),
        sa.Column("purchase_time", sa.DateTime(), nullable=False),
        sa.Column("purchase_source", sa.String(length=128), nullable=False),
        sa.Column("order_id", sa.String(length=255), nullable=True),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=512), nullable=False),
        sa.Column("cart_id", sa.String(length=255), nullable=True),
        sa.Column("customer_phone", sa.String(length=100), nullable=True),
        sa.Column("evidence_detail", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_purchase_truth_records_recovery_key",
        "purchase_truth_records",
        ["recovery_key"],
        unique=True,
    )
    op.create_index(
        "ix_purchase_truth_records_purchase_source",
        "purchase_truth_records",
        ["purchase_source"],
    )
    op.create_index(
        "ix_purchase_truth_records_order_id", "purchase_truth_records", ["order_id"]
    )
    op.create_index(
        "ix_purchase_truth_records_store_slug", "purchase_truth_records", ["store_slug"]
    )
    op.create_index(
        "ix_purchase_truth_records_session_id", "purchase_truth_records", ["session_id"]
    )
    op.create_index(
        "ix_purchase_truth_records_cart_id", "purchase_truth_records", ["cart_id"]
    )

    op.create_table(
        "lifecycle_closure_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recovery_key", sa.String(length=512), nullable=False),
        sa.Column("closure_status", sa.String(length=64), nullable=False),
        sa.Column("closure_reason", sa.String(length=128), nullable=False),
        sa.Column("closure_source", sa.String(length=128), nullable=False),
        sa.Column("closure_time", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lifecycle_closure_records_recovery_key",
        "lifecycle_closure_records",
        ["recovery_key"],
        unique=True,
    )
    op.create_index(
        "ix_lifecycle_closure_records_closure_status",
        "lifecycle_closure_records",
        ["closure_status"],
    )

    op.create_table(
        "recovery_truth_timeline_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recovery_key", sa.String(length=512), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=512), nullable=True),
        sa.Column("cart_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recovery_truth_timeline_events_recovery_key",
        "recovery_truth_timeline_events",
        ["recovery_key"],
    )
    op.create_index(
        "ix_recovery_truth_timeline_events_store_slug",
        "recovery_truth_timeline_events",
        ["store_slug"],
    )
    op.create_index(
        "ix_recovery_truth_timeline_events_session_id",
        "recovery_truth_timeline_events",
        ["session_id"],
    )
    op.create_index(
        "ix_recovery_truth_timeline_events_cart_id",
        "recovery_truth_timeline_events",
        ["cart_id"],
    )
    op.create_index(
        "ix_recovery_truth_timeline_events_status",
        "recovery_truth_timeline_events",
        ["status"],
    )
    op.create_index(
        "ix_recovery_truth_timeline_events_created_at",
        "recovery_truth_timeline_events",
        ["created_at"],
    )

    op.create_table(
        "merchant_cart_lifecycle_archives",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recovery_key", sa.String(length=512), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("abandoned_cart_id", sa.Integer(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("archive_source", sa.String(length=64), nullable=False),
        sa.Column("archived_at", sa.DateTime(), nullable=False),
        sa.Column("reopened_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_merchant_cart_lifecycle_archives_recovery_key",
        "merchant_cart_lifecycle_archives",
        ["recovery_key"],
        unique=True,
    )
    op.create_index(
        "ix_merchant_cart_lifecycle_archives_store_slug",
        "merchant_cart_lifecycle_archives",
        ["store_slug"],
    )
    op.create_index(
        "ix_merchant_cart_lifecycle_archives_abandoned_cart_id",
        "merchant_cart_lifecycle_archives",
        ["abandoned_cart_id"],
    )
    op.create_index(
        "ix_merchant_cart_lifecycle_archives_is_archived",
        "merchant_cart_lifecycle_archives",
        ["is_archived"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_merchant_cart_lifecycle_archives_is_archived",
        table_name="merchant_cart_lifecycle_archives",
    )
    op.drop_index(
        "ix_merchant_cart_lifecycle_archives_abandoned_cart_id",
        table_name="merchant_cart_lifecycle_archives",
    )
    op.drop_index(
        "ix_merchant_cart_lifecycle_archives_store_slug",
        table_name="merchant_cart_lifecycle_archives",
    )
    op.drop_index(
        "ix_merchant_cart_lifecycle_archives_recovery_key",
        table_name="merchant_cart_lifecycle_archives",
    )
    op.drop_table("merchant_cart_lifecycle_archives")
    op.drop_index(
        "ix_recovery_truth_timeline_events_created_at",
        table_name="recovery_truth_timeline_events",
    )
    op.drop_index(
        "ix_recovery_truth_timeline_events_status",
        table_name="recovery_truth_timeline_events",
    )
    op.drop_index(
        "ix_recovery_truth_timeline_events_cart_id",
        table_name="recovery_truth_timeline_events",
    )
    op.drop_index(
        "ix_recovery_truth_timeline_events_session_id",
        table_name="recovery_truth_timeline_events",
    )
    op.drop_index(
        "ix_recovery_truth_timeline_events_store_slug",
        table_name="recovery_truth_timeline_events",
    )
    op.drop_index(
        "ix_recovery_truth_timeline_events_recovery_key",
        table_name="recovery_truth_timeline_events",
    )
    op.drop_table("recovery_truth_timeline_events")
    op.drop_index(
        "ix_lifecycle_closure_records_closure_status",
        table_name="lifecycle_closure_records",
    )
    op.drop_index(
        "ix_lifecycle_closure_records_recovery_key",
        table_name="lifecycle_closure_records",
    )
    op.drop_table("lifecycle_closure_records")
    op.drop_index("ix_purchase_truth_records_cart_id", table_name="purchase_truth_records")
    op.drop_index(
        "ix_purchase_truth_records_session_id", table_name="purchase_truth_records"
    )
    op.drop_index(
        "ix_purchase_truth_records_store_slug", table_name="purchase_truth_records"
    )
    op.drop_index("ix_purchase_truth_records_order_id", table_name="purchase_truth_records")
    op.drop_index(
        "ix_purchase_truth_records_purchase_source", table_name="purchase_truth_records"
    )
    op.drop_index(
        "ix_purchase_truth_records_recovery_key", table_name="purchase_truth_records"
    )
    op.drop_table("purchase_truth_records")
