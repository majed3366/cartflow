"""add reason_templates_json to stores

Revision ID: s9t0u1v2w3x4
Revises: q1w2e3r4t5y6
Create Date: 2026-04-30

Per-reason automation toggle + message for recovery WhatsApp (dashboard reason_templates).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s9t0u1v2w3x4"
down_revision: Union[str, Sequence[str], None] = "q1w2e3r4t5y6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("reason_templates_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stores", "reason_templates_json")
