# -*- coding: utf-8 -*-
"""E7 store_identity_aliases — birth b1ad25b9.

Revision ID: e7sid030603a
Revises: e6lct240527a
Create Date: 2026-06-03
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7sid030603a"
down_revision: Union[str, Sequence[str], None] = "e6lct240527a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_identity_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("alias_kind", sa.String(length=64), nullable=False),
        sa.Column("alias_value", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_store_identity_aliases_store_id", "store_identity_aliases", ["store_id"]
    )
    op.create_index(
        "ix_store_identity_aliases_alias_kind", "store_identity_aliases", ["alias_kind"]
    )
    op.create_index(
        "ix_store_identity_aliases_alias_value",
        "store_identity_aliases",
        ["alias_value"],
        unique=True,
    )
    op.create_index(
        "ix_store_identity_aliases_platform", "store_identity_aliases", ["platform"]
    )


def downgrade() -> None:
    op.drop_index("ix_store_identity_aliases_platform", table_name="store_identity_aliases")
    op.drop_index(
        "ix_store_identity_aliases_alias_value", table_name="store_identity_aliases"
    )
    op.drop_index(
        "ix_store_identity_aliases_alias_kind", table_name="store_identity_aliases"
    )
    op.drop_index("ix_store_identity_aliases_store_id", table_name="store_identity_aliases")
    op.drop_table("store_identity_aliases")
