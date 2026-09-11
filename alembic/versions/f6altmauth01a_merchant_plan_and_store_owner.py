# -*- coding: utf-8 -*-
"""Follow-on ALTER: merchant plan cols, audit extras, stores.merchant_user_id.

Revision ID: f6altmauth01a
Revises: f5altstorezi01
Create Date: 2026-05-23

Depends on E4 merchant_users. No index on stores.merchant_user_id —
production create_all ADD did not create one.

| COLUMN | FIRST COMMIT | OWNER | PROD | CONF |
|--------|--------------|-------|------|------|
| stores.merchant_user_id | 5a7b5649 2026-05-23 | Store + schema_merchant_auth | live NULL INTEGER | HIGH |
| merchant_users.current_plan / plan_* / trial_* / billing_interval | 58dfa3e5 2026-06-07 | MerchantUser + schema_merchant_subscription | live | HIGH |
| merchant_subscription_audit_logs old/new billing+started pairs | a9bdd052 2026-06-07 | MerchantSubscriptionAuditLog | live | HIGH |
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6altmauth01a"
down_revision: Union[str, Sequence[str], None] = "f5altstorezi01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Production create_all ADD left this as INTEGER NULL without an FK or index.
    op.add_column("stores", sa.Column("merchant_user_id", sa.Integer(), nullable=True))

    op.add_column(
        "merchant_users",
        sa.Column("current_plan", sa.String(length=32), nullable=False),
    )
    op.add_column(
        "merchant_users",
        sa.Column("plan_status", sa.String(length=32), nullable=False),
    )
    op.add_column(
        "merchant_users",
        sa.Column("plan_source", sa.String(length=32), nullable=False),
    )
    op.add_column(
        "merchant_users", sa.Column("plan_started_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "merchant_users", sa.Column("plan_expires_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "merchant_users", sa.Column("trial_started_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "merchant_users", sa.Column("trial_expires_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "merchant_users",
        sa.Column("billing_interval", sa.String(length=32), nullable=True),
    )

    op.add_column(
        "merchant_subscription_audit_logs",
        sa.Column("old_billing_interval", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "merchant_subscription_audit_logs",
        sa.Column("new_billing_interval", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "merchant_subscription_audit_logs",
        sa.Column("old_plan_started_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "merchant_subscription_audit_logs",
        sa.Column("new_plan_started_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "merchant_subscription_audit_logs",
        sa.Column("old_trial_started_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "merchant_subscription_audit_logs",
        sa.Column("new_trial_started_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("merchant_subscription_audit_logs", "new_trial_started_at")
    op.drop_column("merchant_subscription_audit_logs", "old_trial_started_at")
    op.drop_column("merchant_subscription_audit_logs", "new_plan_started_at")
    op.drop_column("merchant_subscription_audit_logs", "old_plan_started_at")
    op.drop_column("merchant_subscription_audit_logs", "new_billing_interval")
    op.drop_column("merchant_subscription_audit_logs", "old_billing_interval")
    op.drop_column("merchant_users", "billing_interval")
    op.drop_column("merchant_users", "trial_expires_at")
    op.drop_column("merchant_users", "trial_started_at")
    op.drop_column("merchant_users", "plan_expires_at")
    op.drop_column("merchant_users", "plan_started_at")
    op.drop_column("merchant_users", "plan_source")
    op.drop_column("merchant_users", "plan_status")
    op.drop_column("merchant_users", "current_plan")
    op.drop_column("stores", "merchant_user_id")
