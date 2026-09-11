# -*- coding: utf-8 -*-
"""E5 whatsapp_delivery_truth — birth 3f78aa24.

Revision ID: e5wad230523a
Revises: e4aut230523a
Create Date: 2026-05-23
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5wad230523a"
down_revision: Union[str, Sequence[str], None] = "e4aut230523a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_delivery_truth",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("message_sid", sa.String(length=128), nullable=False),
        sa.Column("customer_phone", sa.String(length=100), nullable=True),
        sa.Column("store_slug", sa.String(length=255), nullable=True),
        sa.Column("session_id", sa.String(length=512), nullable=True),
        sa.Column("cart_id", sa.String(length=255), nullable=True),
        sa.Column("recovery_key", sa.String(length=512), nullable=True),
        sa.Column("send_status", sa.String(length=64), nullable=True),
        sa.Column("delivery_status", sa.String(length=64), nullable=True),
        sa.Column("read_status", sa.String(length=64), nullable=True),
        sa.Column("provider_error", sa.String(length=512), nullable=True),
        sa.Column("truth_level", sa.String(length=64), nullable=False),
        sa.Column("last_event_time", sa.DateTime(), nullable=False),
        sa.Column("raw_last_payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_whatsapp_delivery_truth_provider", "whatsapp_delivery_truth", ["provider"])
    op.create_index(
        "ix_whatsapp_delivery_truth_message_sid",
        "whatsapp_delivery_truth",
        ["message_sid"],
        unique=True,
    )
    op.create_index(
        "ix_whatsapp_delivery_truth_store_slug", "whatsapp_delivery_truth", ["store_slug"]
    )
    op.create_index(
        "ix_whatsapp_delivery_truth_session_id", "whatsapp_delivery_truth", ["session_id"]
    )
    op.create_index(
        "ix_whatsapp_delivery_truth_recovery_key",
        "whatsapp_delivery_truth",
        ["recovery_key"],
    )
    op.create_index(
        "ix_whatsapp_delivery_truth_truth_level",
        "whatsapp_delivery_truth",
        ["truth_level"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_whatsapp_delivery_truth_truth_level", table_name="whatsapp_delivery_truth"
    )
    op.drop_index(
        "ix_whatsapp_delivery_truth_recovery_key", table_name="whatsapp_delivery_truth"
    )
    op.drop_index(
        "ix_whatsapp_delivery_truth_session_id", table_name="whatsapp_delivery_truth"
    )
    op.drop_index(
        "ix_whatsapp_delivery_truth_store_slug", table_name="whatsapp_delivery_truth"
    )
    op.drop_index(
        "ix_whatsapp_delivery_truth_message_sid", table_name="whatsapp_delivery_truth"
    )
    op.drop_index(
        "ix_whatsapp_delivery_truth_provider", table_name="whatsapp_delivery_truth"
    )
    op.drop_table("whatsapp_delivery_truth")
