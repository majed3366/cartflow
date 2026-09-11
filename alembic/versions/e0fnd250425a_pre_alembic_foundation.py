# -*- coding: utf-8 -*-
"""E0 pre-Alembic foundation — schema immediately before a3ff333f6d46.

Revision ID: e0fnd250425a
Revises: None
Create Date: 2026-04-25

Birth body from git 2d316878. Do not include later Alembic or create_all columns.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e0fnd250425a"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("zid_store_id", sa.String(length=128), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stores_zid_store_id", "stores", ["zid_store_id"], unique=True
    )

    op.create_table(
        "abandoned_carts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("zid_cart_id", sa.String(length=255), nullable=False),
        sa.Column("customer_name", sa.String(length=500), nullable=True),
        sa.Column("customer_phone", sa.String(length=100), nullable=True),
        sa.Column("customer_email", sa.String(length=500), nullable=True),
        sa.Column("cart_value", sa.Float(), nullable=True),
        sa.Column("cart_url", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("recovered_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_abandoned_carts_zid_cart_id",
        "abandoned_carts",
        ["zid_cart_id"],
        unique=True,
    )
    op.create_index(
        "ix_abandoned_carts_store_id", "abandoned_carts", ["store_id"]
    )

    op.create_table(
        "message_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("abandoned_cart_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("phone", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("provider_response", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["abandoned_cart_id"], ["abandoned_carts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_logs_store_id", "message_logs", ["store_id"])
    op.create_index(
        "ix_message_logs_abandoned_cart_id",
        "message_logs",
        ["abandoned_cart_id"],
    )

    op.create_table(
        "objection_tracks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("customer_name", sa.String(length=500), nullable=True),
        sa.Column("customer_phone", sa.String(length=100), nullable=True),
        sa.Column("cart_url", sa.String(length=2048), nullable=True),
        sa.Column("customer_type", sa.String(length=20), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_objection_tracks_type", "objection_tracks", ["type"])

    op.create_table(
        "recovery_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("abandoned_cart_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["abandoned_cart_id"], ["abandoned_carts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recovery_events_store_id", "recovery_events", ["store_id"])
    op.create_index(
        "ix_recovery_events_abandoned_cart_id",
        "recovery_events",
        ["abandoned_cart_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_recovery_events_abandoned_cart_id", table_name="recovery_events")
    op.drop_index("ix_recovery_events_store_id", table_name="recovery_events")
    op.drop_table("recovery_events")
    op.drop_index("ix_objection_tracks_type", table_name="objection_tracks")
    op.drop_table("objection_tracks")
    op.drop_index("ix_message_logs_abandoned_cart_id", table_name="message_logs")
    op.drop_index("ix_message_logs_store_id", table_name="message_logs")
    op.drop_table("message_logs")
    op.drop_index("ix_abandoned_carts_store_id", table_name="abandoned_carts")
    op.drop_index("ix_abandoned_carts_zid_cart_id", table_name="abandoned_carts")
    op.drop_table("abandoned_carts")
    op.drop_index("ix_stores_zid_store_id", table_name="stores")
    op.drop_table("stores")
