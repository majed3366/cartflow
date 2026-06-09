"""add product catalog entries

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-06-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, Sequence[str], None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_catalog_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("stable_identity_key", sa.String(length=256), nullable=False),
        sa.Column("identity_tier", sa.String(length=8), nullable=False),
        sa.Column("product_id", sa.String(length=128), nullable=True),
        sa.Column("variant_id", sa.String(length=128), nullable=True),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="SAR"),
        sa.Column("capture_confidence", sa.String(length=16), nullable=False),
        sa.Column("catalog_source", sa.String(length=64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_slug",
            "stable_identity_key",
            name="uq_product_catalog_identity",
        ),
    )
    op.create_index(
        "ix_product_catalog_entries_store_slug",
        "product_catalog_entries",
        ["store_slug"],
    )
    op.create_index(
        "ix_product_catalog_entries_stable_identity_key",
        "product_catalog_entries",
        ["stable_identity_key"],
    )
    op.create_index(
        "ix_product_catalog_entries_identity_tier",
        "product_catalog_entries",
        ["identity_tier"],
    )
    op.create_index(
        "ix_product_catalog_entries_product_id",
        "product_catalog_entries",
        ["product_id"],
    )
    op.create_index(
        "ix_product_catalog_entries_sku", "product_catalog_entries", ["sku"]
    )
    op.create_index(
        "ix_product_catalog_entries_catalog_source",
        "product_catalog_entries",
        ["catalog_source"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_catalog_entries_catalog_source", table_name="product_catalog_entries"
    )
    op.drop_index("ix_product_catalog_entries_sku", table_name="product_catalog_entries")
    op.drop_index(
        "ix_product_catalog_entries_product_id", table_name="product_catalog_entries"
    )
    op.drop_index(
        "ix_product_catalog_entries_identity_tier", table_name="product_catalog_entries"
    )
    op.drop_index(
        "ix_product_catalog_entries_stable_identity_key",
        table_name="product_catalog_entries",
    )
    op.drop_index(
        "ix_product_catalog_entries_store_slug", table_name="product_catalog_entries"
    )
    op.drop_table("product_catalog_entries")
