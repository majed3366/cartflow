"""add cart line snapshots

Revision ID: h8i9j0k1l2m3
Revises: z1a2b3c4d5e6
Create Date: 2026-06-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, Sequence[str], None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cart_line_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=512), nullable=False),
        sa.Column("cart_id", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("recovery_key", sa.String(length=512), nullable=True),
        sa.Column("product_id", sa.String(length=128), nullable=True),
        sa.Column("variant_id", sa.String(length=128), nullable=True),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("unit_price", sa.Float(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("capture_source", sa.String(length=64), nullable=False),
        sa.Column("capture_confidence", sa.String(length=16), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_slug",
            "session_id",
            "cart_id",
            "capture_source",
            "content_hash",
            name="uq_cart_line_snapshot_dedup",
        ),
    )
    op.create_index(
        "ix_cart_line_snapshots_store_slug", "cart_line_snapshots", ["store_slug"]
    )
    op.create_index(
        "ix_cart_line_snapshots_session_id", "cart_line_snapshots", ["session_id"]
    )
    op.create_index(
        "ix_cart_line_snapshots_cart_id", "cart_line_snapshots", ["cart_id"]
    )
    op.create_index(
        "ix_cart_line_snapshots_recovery_key", "cart_line_snapshots", ["recovery_key"]
    )
    op.create_index(
        "ix_cart_line_snapshots_product_id", "cart_line_snapshots", ["product_id"]
    )
    op.create_index(
        "ix_cart_line_snapshots_captured_at", "cart_line_snapshots", ["captured_at"]
    )
    op.create_index(
        "ix_cart_line_snapshots_capture_source",
        "cart_line_snapshots",
        ["capture_source"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cart_line_snapshots_capture_source", table_name="cart_line_snapshots"
    )
    op.drop_index("ix_cart_line_snapshots_captured_at", table_name="cart_line_snapshots")
    op.drop_index("ix_cart_line_snapshots_product_id", table_name="cart_line_snapshots")
    op.drop_index("ix_cart_line_snapshots_recovery_key", table_name="cart_line_snapshots")
    op.drop_index("ix_cart_line_snapshots_cart_id", table_name="cart_line_snapshots")
    op.drop_index("ix_cart_line_snapshots_session_id", table_name="cart_line_snapshots")
    op.drop_index("ix_cart_line_snapshots_store_slug", table_name="cart_line_snapshots")
    op.drop_table("cart_line_snapshots")
