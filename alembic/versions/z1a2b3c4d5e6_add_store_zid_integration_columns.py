"""add store zid oauth integration columns

Revision ID: z1a2b3c4d5e6
Revises: x9y8z7w6v5u4
Create Date: 2026-06-02

integration_source + connected_at for Zid dev-store OAuth (stores table).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "z1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "x9y8z7w6v5u4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INTEGRATION_SOURCE_INDEX = "ix_stores_integration_source"


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("integration_source", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        _INTEGRATION_SOURCE_INDEX,
        "stores",
        ["integration_source"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(_INTEGRATION_SOURCE_INDEX, table_name="stores")
    op.drop_column("stores", "connected_at")
    op.drop_column("stores", "integration_source")
