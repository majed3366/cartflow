"""add product purchase mappings

Revision ID: k1l2m3n4o5p6q7
Revises: j0k1l2m3n4o5p6
Create Date: 2026-06-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k1l2m3n4o5p6q7"
down_revision: Union[str, Sequence[str], None] = "j0k1l2m3n4o5p6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_purchase_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=512), nullable=False),
        sa.Column("cart_id", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("recovery_key", sa.String(length=512), nullable=True),
        sa.Column("order_id", sa.String(length=255), nullable=True),
        sa.Column("stable_identity_key", sa.String(length=256), nullable=False),
        sa.Column("product_id", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("unit_price", sa.Float(), nullable=True),
        sa.Column("purchase_confidence", sa.String(length=16), nullable=False),
        sa.Column("purchase_source", sa.String(length=128), nullable=False),
        sa.Column("purchased_at", sa.DateTime(), nullable=False),
        sa.Column("dedup_hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_hash", name="uq_product_purchase_dedup"),
    )
    op.create_index(
        "ix_product_purchase_mappings_store_slug",
        "product_purchase_mappings",
        ["store_slug"],
    )
    op.create_index(
        "ix_product_purchase_mappings_session_id",
        "product_purchase_mappings",
        ["session_id"],
    )
    op.create_index(
        "ix_product_purchase_mappings_cart_id",
        "product_purchase_mappings",
        ["cart_id"],
    )
    op.create_index(
        "ix_product_purchase_mappings_recovery_key",
        "product_purchase_mappings",
        ["recovery_key"],
    )
    op.create_index(
        "ix_product_purchase_mappings_order_id",
        "product_purchase_mappings",
        ["order_id"],
    )
    op.create_index(
        "ix_product_purchase_mappings_stable_identity_key",
        "product_purchase_mappings",
        ["stable_identity_key"],
    )
    op.create_index(
        "ix_product_purchase_mappings_product_id",
        "product_purchase_mappings",
        ["product_id"],
    )
    op.create_index(
        "ix_product_purchase_mappings_purchase_source",
        "product_purchase_mappings",
        ["purchase_source"],
    )
    op.create_index(
        "ix_product_purchase_mappings_purchased_at",
        "product_purchase_mappings",
        ["purchased_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_purchase_mappings_purchased_at",
        table_name="product_purchase_mappings",
    )
    op.drop_index(
        "ix_product_purchase_mappings_purchase_source",
        table_name="product_purchase_mappings",
    )
    op.drop_index(
        "ix_product_purchase_mappings_product_id",
        table_name="product_purchase_mappings",
    )
    op.drop_index(
        "ix_product_purchase_mappings_stable_identity_key",
        table_name="product_purchase_mappings",
    )
    op.drop_index(
        "ix_product_purchase_mappings_order_id",
        table_name="product_purchase_mappings",
    )
    op.drop_index(
        "ix_product_purchase_mappings_recovery_key",
        table_name="product_purchase_mappings",
    )
    op.drop_index(
        "ix_product_purchase_mappings_cart_id",
        table_name="product_purchase_mappings",
    )
    op.drop_index(
        "ix_product_purchase_mappings_session_id",
        table_name="product_purchase_mappings",
    )
    op.drop_index(
        "ix_product_purchase_mappings_store_slug",
        table_name="product_purchase_mappings",
    )
    op.drop_table("product_purchase_mappings")
