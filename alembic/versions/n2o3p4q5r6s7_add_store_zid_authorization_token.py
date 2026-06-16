"""add store zid oauth authorization token column

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6
Create Date: 2026-06-16

Per-store Zid OAuth Authorization (Partner API Bearer), distinct from access_token.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n2o3p4q5r6s7"
down_revision: Union[str, Sequence[str], None] = "m1n2o3p4q5r6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("zid_authorization_token", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stores", "zid_authorization_token")
