"""add product hesitation mappings

Revision ID: j0k1l2m3n4o5p6
Revises: i9j0k1l2m3n4
Create Date: 2026-06-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j0k1l2m3n4o5p6"
down_revision: Union[str, Sequence[str], None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_hesitation_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=512), nullable=False),
        sa.Column("cart_id", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("recovery_key", sa.String(length=512), nullable=True),
        sa.Column("stable_identity_key", sa.String(length=256), nullable=False),
        sa.Column("identity_tier", sa.String(length=8), nullable=False),
        sa.Column("product_id", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("sub_reason", sa.String(length=64), nullable=True),
        sa.Column("mapping_confidence", sa.String(length=16), nullable=False),
        sa.Column(
            "mapping_source",
            sa.String(length=32),
            nullable=False,
            server_default="reason_capture",
        ),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("dedup_hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_hash", name="uq_product_hesitation_dedup"),
    )
    op.create_index(
        "ix_product_hesitation_mappings_store_slug",
        "product_hesitation_mappings",
        ["store_slug"],
    )
    op.create_index(
        "ix_product_hesitation_mappings_session_id",
        "product_hesitation_mappings",
        ["session_id"],
    )
    op.create_index(
        "ix_product_hesitation_mappings_cart_id",
        "product_hesitation_mappings",
        ["cart_id"],
    )
    op.create_index(
        "ix_product_hesitation_mappings_recovery_key",
        "product_hesitation_mappings",
        ["recovery_key"],
    )
    op.create_index(
        "ix_product_hesitation_mappings_stable_identity_key",
        "product_hesitation_mappings",
        ["stable_identity_key"],
    )
    op.create_index(
        "ix_product_hesitation_mappings_product_id",
        "product_hesitation_mappings",
        ["product_id"],
    )
    op.create_index(
        "ix_product_hesitation_mappings_reason",
        "product_hesitation_mappings",
        ["reason"],
    )
    op.create_index(
        "ix_product_hesitation_mappings_sub_reason",
        "product_hesitation_mappings",
        ["sub_reason"],
    )
    op.create_index(
        "ix_product_hesitation_mappings_captured_at",
        "product_hesitation_mappings",
        ["captured_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_hesitation_mappings_captured_at",
        table_name="product_hesitation_mappings",
    )
    op.drop_index(
        "ix_product_hesitation_mappings_sub_reason",
        table_name="product_hesitation_mappings",
    )
    op.drop_index(
        "ix_product_hesitation_mappings_reason",
        table_name="product_hesitation_mappings",
    )
    op.drop_index(
        "ix_product_hesitation_mappings_product_id",
        table_name="product_hesitation_mappings",
    )
    op.drop_index(
        "ix_product_hesitation_mappings_stable_identity_key",
        table_name="product_hesitation_mappings",
    )
    op.drop_index(
        "ix_product_hesitation_mappings_recovery_key",
        table_name="product_hesitation_mappings",
    )
    op.drop_index(
        "ix_product_hesitation_mappings_cart_id",
        table_name="product_hesitation_mappings",
    )
    op.drop_index(
        "ix_product_hesitation_mappings_session_id",
        table_name="product_hesitation_mappings",
    )
    op.drop_index(
        "ix_product_hesitation_mappings_store_slug",
        table_name="product_hesitation_mappings",
    )
    op.drop_table("product_hesitation_mappings")
