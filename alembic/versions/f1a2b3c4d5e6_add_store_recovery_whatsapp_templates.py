"""add per-store WhatsApp recovery template columns

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-04-30

Optional TEXT templates per reason bucket; NULL or empty = built-in default.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for name in (
        "template_price",
        "template_shipping",
        "template_quality",
        "template_delivery",
        "template_warranty",
        "template_other",
    ):
        op.add_column("stores", sa.Column(name, sa.Text(), nullable=True))


def downgrade() -> None:
    for name in (
        "template_other",
        "template_warranty",
        "template_delivery",
        "template_quality",
        "template_shipping",
        "template_price",
    ):
        op.drop_column("stores", name)
