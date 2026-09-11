# -*- coding: utf-8 -*-
"""Follow-on ALTER: later create_all columns on abandoned_carts.

Revision ID: f2altacarts01a
Revises: f1altreason01a
Create Date: 2026-05-04

vip_mode is already owned by surviving Alembic x9y8z7w6v5u4.

| COLUMN | FIRST COMMIT | OWNER | PROD | CONF |
|--------|--------------|-------|------|------|
| recovery_session_id | 2a571348 2026-05-04 | AbandonedCart | live | HIGH |
| vip_lifecycle_status | 215d2a0c 2026-05-06 | AbandonedCart | live | HIGH |
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2altacarts01a"
down_revision: Union[str, Sequence[str], None] = "f1altreason01a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "abandoned_carts",
        sa.Column("recovery_session_id", sa.String(length=512), nullable=True),
    )
    op.create_index(
        "ix_abandoned_carts_recovery_session_id",
        "abandoned_carts",
        ["recovery_session_id"],
    )
    op.add_column(
        "abandoned_carts",
        sa.Column("vip_lifecycle_status", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("abandoned_carts", "vip_lifecycle_status")
    op.drop_index(
        "ix_abandoned_carts_recovery_session_id", table_name="abandoned_carts"
    )
    op.drop_column("abandoned_carts", "recovery_session_id")
