"""add exit_intent_template_* columns to stores

Revision ID: j0k1l2m3n4o5
Revises: g7h8i9j0k1l2
Create Date: 2026-04-30

Pre-cart exit intent copy control (separate from discovery helper templates).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j0k1l2m3n4o5"
down_revision: Union[str, Sequence[str], None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column(
            "exit_intent_template_mode",
            sa.String(length=32),
            nullable=False,
            server_default="preset",
        ),
    )
    op.add_column(
        "stores",
        sa.Column(
            "exit_intent_template_tone",
            sa.String(length=32),
            nullable=False,
            server_default="friendly",
        ),
    )
    op.add_column(
        "stores",
        sa.Column("exit_intent_custom_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stores", "exit_intent_custom_text")
    op.drop_column("stores", "exit_intent_template_tone")
    op.drop_column("stores", "exit_intent_template_mode")
