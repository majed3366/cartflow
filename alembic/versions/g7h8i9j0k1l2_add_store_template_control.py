"""add template_mode template_tone template_custom_text to stores

Revision ID: g7h8i9j0k1l2
Revises: f1a2b3c4d5e6
Create Date: 2026-04-30

Widget template tone control (preset/custom + tone); nullable custom override text.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column(
            "template_mode",
            sa.String(length=32),
            nullable=False,
            server_default="preset",
        ),
    )
    op.add_column(
        "stores",
        sa.Column(
            "template_tone",
            sa.String(length=32),
            nullable=False,
            server_default="friendly",
        ),
    )
    op.add_column(
        "stores",
        sa.Column("template_custom_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stores", "template_custom_text")
    op.drop_column("stores", "template_tone")
    op.drop_column("stores", "template_mode")
