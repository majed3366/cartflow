# -*- coding: utf-8 -*-
"""E13 product exposure events + daily facts — birth 751c35a3.

Revision ID: e13px090909a
Revises: e12dl270729a
Create Date: 2026-09-09
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e13px090909a"
down_revision: Union[str, Sequence[str], None] = "e12dl270729a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_exposure_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("product_id", sa.String(length=128), nullable=False),
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("page_context", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("truth_version", sa.String(length=32), nullable=False),
        sa.Column("commercial_dedupe_key", sa.String(length=512), nullable=False),
        sa.Column("commercial_bucket", sa.String(length=32), nullable=False),
        sa.Column("commerce_platform", sa.String(length=32), nullable=False),
        sa.Column("identity_source", sa.String(length=64), nullable=False),
        sa.Column("event_source", sa.String(length=64), nullable=False),
        sa.Column("referrer_domain", sa.String(length=253), nullable=True),
        sa.Column("claimed_utm_source", sa.String(length=80), nullable=True),
        sa.Column("claimed_utm_medium", sa.String(length=80), nullable=True),
        sa.Column("claimed_utm_campaign", sa.String(length=80), nullable=True),
        sa.Column("lab_flag", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_product_exposure_event_id"),
    )
    op.create_index(
        "ix_pex_commercial_seq",
        "product_exposure_events",
        ["store_slug", "session_id", "product_id", "page_context", "occurred_at"],
    )
    op.create_index(
        "ix_pex_session_day",
        "product_exposure_events",
        ["store_slug", "product_id", "session_id", "occurred_at"],
    )
    op.create_index(
        "ix_pex_store_time", "product_exposure_events", ["store_slug", "occurred_at"]
    )

    op.create_table(
        "product_exposure_daily_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("product_id", sa.String(length=128), nullable=False),
        sa.Column("date_utc", sa.String(length=10), nullable=False),
        sa.Column("pdp_view_count", sa.Integer(), nullable=False),
        sa.Column("viewing_session_count", sa.Integer(), nullable=False),
        sa.Column("truth_version", sa.String(length=32), nullable=False),
        sa.Column("sealed_at", sa.DateTime(), nullable=True),
        sa.Column("seal_truth_version", sa.String(length=32), nullable=True),
        sa.Column("seal_source_window_start", sa.DateTime(), nullable=True),
        sa.Column("seal_source_window_end", sa.DateTime(), nullable=True),
        sa.Column("seal_source_row_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_slug", "product_id", "date_utc", name="uq_pex_daily_facts_grain"
        ),
    )


def downgrade() -> None:
    op.drop_table("product_exposure_daily_facts")
    op.drop_index("ix_pex_store_time", table_name="product_exposure_events")
    op.drop_index("ix_pex_session_day", table_name="product_exposure_events")
    op.drop_index("ix_pex_commercial_seq", table_name="product_exposure_events")
    op.drop_table("product_exposure_events")
