"""add widget_name widget_primary_color widget_style to stores

Revision ID: p6q7r8s9t0u1
Revises: j0k1l2m3n4o5
Create Date: 2026-04-30

Visual widget branding (dashboard + front-end only).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p6q7r8s9t0u1"
down_revision: Union[str, Sequence[str], None] = "j0k1l2m3n4o5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column(
            "widget_name",
            sa.String(length=255),
            nullable=False,
            server_default="مساعد المتجر",
        ),
    )
    op.add_column(
        "stores",
        sa.Column(
            "widget_primary_color",
            sa.String(length=16),
            nullable=False,
            server_default="#6C5CE7",
        ),
    )
    op.add_column(
        "stores",
        sa.Column(
            "widget_style",
            sa.String(length=16),
            nullable=False,
            server_default="modern",
        ),
    )


def downgrade() -> None:
    op.drop_column("stores", "widget_style")
    op.drop_column("stores", "widget_primary_color")
    op.drop_column("stores", "widget_name")
