# -*- coding: utf-8 -*-
"""E4 merchant auth — merchant_users + reset tokens birth 5a7b5649.

Revision ID: e4aut230523a
Revises: e2fup050505a
Create Date: 2026-05-23

Later plan/trial/billing columns belong in follow-on ALTER revisions.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4aut230523a"
down_revision: Union[str, Sequence[str], None] = "e2fup050505a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "merchant_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("merchant_name", sa.String(length=255), nullable=False),
        sa.Column("primary_store_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["primary_store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merchant_users_email", "merchant_users", ["email"], unique=True)
    op.create_index(
        "ix_merchant_users_primary_store_id", "merchant_users", ["primary_store_id"]
    )

    op.create_table(
        "merchant_password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("merchant_user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_user_id"], ["merchant_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_merchant_password_reset_tokens_merchant_user_id",
        "merchant_password_reset_tokens",
        ["merchant_user_id"],
    )
    op.create_index(
        "ix_merchant_password_reset_tokens_token_hash",
        "merchant_password_reset_tokens",
        ["token_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_merchant_password_reset_tokens_token_hash",
        table_name="merchant_password_reset_tokens",
    )
    op.drop_index(
        "ix_merchant_password_reset_tokens_merchant_user_id",
        table_name="merchant_password_reset_tokens",
    )
    op.drop_table("merchant_password_reset_tokens")
    op.drop_index("ix_merchant_users_primary_store_id", table_name="merchant_users")
    op.drop_index("ix_merchant_users_email", table_name="merchant_users")
    op.drop_table("merchant_users")
