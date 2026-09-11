# -*- coding: utf-8 -*-
"""Follow-on ALTER: later create_all scope columns on lifecycle_closure_records.

Revision ID: f9altlclose01
Revises: f8altdbready1
Create Date: 2026-05-25

E6 birth (8fe9bd0c) has no store_slug/session_id/cart_id.
schema_lifecycle_closure.py added them later. Current model + runtime use them.

Canonical head after this revision is f10altparity01 (physical alignment).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f9altlclose01"
down_revision: Union[str, Sequence[str], None] = "f8altdbready1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lifecycle_closure_records",
        sa.Column("store_slug", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "lifecycle_closure_records",
        sa.Column("session_id", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "lifecycle_closure_records",
        sa.Column("cart_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_lifecycle_closure_records_store_slug",
        "lifecycle_closure_records",
        ["store_slug"],
    )
    op.create_index(
        "ix_lifecycle_closure_records_session_id",
        "lifecycle_closure_records",
        ["session_id"],
    )
    op.create_index(
        "ix_lifecycle_closure_records_cart_id",
        "lifecycle_closure_records",
        ["cart_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lifecycle_closure_records_cart_id", table_name="lifecycle_closure_records"
    )
    op.drop_index(
        "ix_lifecycle_closure_records_session_id",
        table_name="lifecycle_closure_records",
    )
    op.drop_index(
        "ix_lifecycle_closure_records_store_slug",
        table_name="lifecycle_closure_records",
    )
    op.drop_column("lifecycle_closure_records", "cart_id")
    op.drop_column("lifecycle_closure_records", "session_id")
    op.drop_column("lifecycle_closure_records", "store_slug")
