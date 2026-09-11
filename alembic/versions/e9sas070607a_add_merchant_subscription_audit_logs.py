# -*- coding: utf-8 -*-
"""E9 merchant_subscription_audit_logs — birth 95657478.

Revision ID: e9sas070607a
Revises: e8ops050605a
Create Date: 2026-06-07

Later billing_interval / plan_started / trial_started pairs belong in ALTER.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e9sas070607a"
down_revision: Union[str, Sequence[str], None] = "e8ops050605a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "merchant_subscription_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("merchant_user_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("admin_source", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("old_plan", sa.String(length=32), nullable=True),
        sa.Column("new_plan", sa.String(length=32), nullable=True),
        sa.Column("old_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=True),
        sa.Column("old_plan_expires_at", sa.DateTime(), nullable=True),
        sa.Column("new_plan_expires_at", sa.DateTime(), nullable=True),
        sa.Column("old_trial_expires_at", sa.DateTime(), nullable=True),
        sa.Column("new_trial_expires_at", sa.DateTime(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_user_id"], ["merchant_users.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_merchant_subscription_audit_logs_merchant_user_id",
        "merchant_subscription_audit_logs",
        ["merchant_user_id"],
    )
    op.create_index(
        "ix_merchant_subscription_audit_logs_store_id",
        "merchant_subscription_audit_logs",
        ["store_id"],
    )
    op.create_index(
        "ix_merchant_subscription_audit_logs_created_at",
        "merchant_subscription_audit_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_merchant_subscription_audit_logs_created_at",
        table_name="merchant_subscription_audit_logs",
    )
    op.drop_index(
        "ix_merchant_subscription_audit_logs_store_id",
        table_name="merchant_subscription_audit_logs",
    )
    op.drop_index(
        "ix_merchant_subscription_audit_logs_merchant_user_id",
        table_name="merchant_subscription_audit_logs",
    )
    op.drop_table("merchant_subscription_audit_logs")
