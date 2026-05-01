"""add trigger_templates_json to stores

Revision ID: q1w2e3r4t5y6
Revises: p6q7r8s9t0u1
Create Date: 2026-04-30

Trigger-based WhatsApp recovery templates per reason_tag (JSON blob).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "q1w2e3r4t5y6"
down_revision: Union[str, Sequence[str], None] = "p6q7r8s9t0u1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("trigger_templates_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stores", "trigger_templates_json")
