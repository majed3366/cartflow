"""add product metric values

Revision ID: v5w6x7y8z9a0
Revises: u4v5w6x7y8z9
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v5w6x7y8z9a0"
down_revision: Union[str, Sequence[str], None] = "u4v5w6x7y8z9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_metric_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column(
            "stable_identity_key",
            sa.String(length=256),
            nullable=False,
            server_default="",
        ),
        sa.Column("metric_key", sa.String(length=64), nullable=False),
        sa.Column("metric_family", sa.String(length=64), nullable=False),
        sa.Column(
            "window_code", sa.String(length=16), nullable=False, server_default="all"
        ),
        sa.Column("window_start", sa.DateTime(), nullable=True),
        sa.Column("window_end", sa.DateTime(), nullable=True),
        sa.Column(
            "window_start_key", sa.String(length=32), nullable=False, server_default=""
        ),
        sa.Column(
            "window_end_key", sa.String(length=32), nullable=False, server_default=""
        ),
        sa.Column("value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "source_signal_type", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column(
            "computation_version",
            sa.String(length=32),
            nullable=False,
            server_default="pmf_v1_count",
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
            "window_code",
            "window_start_key",
            "window_end_key",
            name="uq_product_metric_value_grain",
        ),
    )
    op.create_index(
        "ix_product_metric_values_store_slug",
        "product_metric_values",
        ["store_slug"],
    )
    op.create_index(
        "ix_product_metric_values_stable_identity_key",
        "product_metric_values",
        ["stable_identity_key"],
    )
    op.create_index(
        "ix_product_metric_values_metric_key",
        "product_metric_values",
        ["metric_key"],
    )
    op.create_index(
        "ix_product_metric_values_metric_family",
        "product_metric_values",
        ["metric_family"],
    )
    op.create_index(
        "ix_product_metric_values_window_code",
        "product_metric_values",
        ["window_code"],
    )
    op.create_index(
        "ix_product_metric_values_computed_at",
        "product_metric_values",
        ["computed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_product_metric_values_computed_at", table_name="product_metric_values")
    op.drop_index("ix_product_metric_values_window_code", table_name="product_metric_values")
    op.drop_index("ix_product_metric_values_metric_family", table_name="product_metric_values")
    op.drop_index("ix_product_metric_values_metric_key", table_name="product_metric_values")
    op.drop_index(
        "ix_product_metric_values_stable_identity_key",
        table_name="product_metric_values",
    )
    op.drop_index("ix_product_metric_values_store_slug", table_name="product_metric_values")
    op.drop_table("product_metric_values")
