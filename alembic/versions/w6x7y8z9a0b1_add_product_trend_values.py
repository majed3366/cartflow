"""add product trend values

Revision ID: w6x7y8z9a0b1
Revises: v5w6x7y8z9a0
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "w6x7y8z9a0b1"
down_revision: Union[str, Sequence[str], None] = "v5w6x7y8z9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_trend_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column(
            "stable_identity_key",
            sa.String(length=256),
            nullable=False,
            server_default="",
        ),
        sa.Column("metric_key", sa.String(length=64), nullable=False),
        sa.Column(
            "metric_family", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column("trend_window", sa.String(length=16), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("as_of_key", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("current_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("previous_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delta_abs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trend_direction", sa.String(length=32), nullable=False),
        sa.Column(
            "computation_version",
            sa.String(length=32),
            nullable=False,
            server_default="ptf_v1_delta",
        ),
        sa.Column(
            "content_hash", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_slug",
            "stable_identity_key",
            "metric_key",
            "trend_window",
            "as_of_key",
            name="uq_product_trend_value_grain",
        ),
    )
    for name, col in (
        ("ix_product_trend_values_store_slug", "store_slug"),
        ("ix_product_trend_values_stable_identity_key", "stable_identity_key"),
        ("ix_product_trend_values_metric_key", "metric_key"),
        ("ix_product_trend_values_metric_family", "metric_family"),
        ("ix_product_trend_values_trend_window", "trend_window"),
        ("ix_product_trend_values_as_of", "as_of"),
        ("ix_product_trend_values_trend_direction", "trend_direction"),
        ("ix_product_trend_values_computed_at", "computed_at"),
    ):
        op.create_index(name, "product_trend_values", [col])


def downgrade() -> None:
    for name in (
        "ix_product_trend_values_computed_at",
        "ix_product_trend_values_trend_direction",
        "ix_product_trend_values_as_of",
        "ix_product_trend_values_trend_window",
        "ix_product_trend_values_metric_family",
        "ix_product_trend_values_metric_key",
        "ix_product_trend_values_stable_identity_key",
        "ix_product_trend_values_store_slug",
    ):
        op.drop_index(name, table_name="product_trend_values")
    op.drop_table("product_trend_values")
