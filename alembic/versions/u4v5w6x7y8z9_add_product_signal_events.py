"""add product signal events

Revision ID: u4v5w6x7y8z9
Revises: t2u3v4w5x6y7
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "u4v5w6x7y8z9"
down_revision: Union[str, Sequence[str], None] = "t2u3v4w5x6y7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_signal_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("cart_id", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("recovery_key", sa.String(length=512), nullable=True),
        sa.Column("stable_identity_key", sa.String(length=256), nullable=False),
        sa.Column("identity_tier", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("product_id", sa.String(length=128), nullable=True),
        sa.Column("signal_family", sa.String(length=64), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("evidence_ref_type", sa.String(length=64), nullable=True),
        sa.Column("evidence_ref_id", sa.String(length=128), nullable=True),
        sa.Column("dedup_hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_hash", name="uq_product_signal_dedup"),
    )
    op.create_index(
        "ix_product_signal_events_store_slug",
        "product_signal_events",
        ["store_slug"],
    )
    op.create_index(
        "ix_product_signal_events_session_id",
        "product_signal_events",
        ["session_id"],
    )
    op.create_index(
        "ix_product_signal_events_cart_id",
        "product_signal_events",
        ["cart_id"],
    )
    op.create_index(
        "ix_product_signal_events_recovery_key",
        "product_signal_events",
        ["recovery_key"],
    )
    op.create_index(
        "ix_product_signal_events_stable_identity_key",
        "product_signal_events",
        ["stable_identity_key"],
    )
    op.create_index(
        "ix_product_signal_events_product_id",
        "product_signal_events",
        ["product_id"],
    )
    op.create_index(
        "ix_product_signal_events_signal_family",
        "product_signal_events",
        ["signal_family"],
    )
    op.create_index(
        "ix_product_signal_events_signal_type",
        "product_signal_events",
        ["signal_type"],
    )
    op.create_index(
        "ix_product_signal_events_observed_at",
        "product_signal_events",
        ["observed_at"],
    )
    op.create_index(
        "ix_product_signal_events_source",
        "product_signal_events",
        ["source"],
    )


def downgrade() -> None:
    for name in (
        "ix_product_signal_events_source",
        "ix_product_signal_events_observed_at",
        "ix_product_signal_events_signal_type",
        "ix_product_signal_events_signal_family",
        "ix_product_signal_events_product_id",
        "ix_product_signal_events_stable_identity_key",
        "ix_product_signal_events_recovery_key",
        "ix_product_signal_events_cart_id",
        "ix_product_signal_events_session_id",
        "ix_product_signal_events_store_slug",
    ):
        op.drop_index(name, table_name="product_signal_events")
    op.drop_table("product_signal_events")
