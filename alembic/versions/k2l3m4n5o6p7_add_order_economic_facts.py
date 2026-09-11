"""add order economic facts

Revision ID: k2l3m4n5o6p7
Revises: j9k0l1m2n3o4
Create Date: 2026-09-11

Order Economic Fact V1 — sibling monetary owner. Not Purchase Truth.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, Sequence[str], None] = "j9k0l1m2n3o4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_economic_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("external_order_id", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("payment_state", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("paid_amount", sa.String(length=32), nullable=False),
        sa.Column("order_total", sa.String(length=32), nullable=True),
        sa.Column("transaction_amount", sa.String(length=32), nullable=True),
        sa.Column("customer_shipping_charge", sa.String(length=32), nullable=True),
        sa.Column("order_subtotal", sa.String(length=32), nullable=True),
        sa.Column("discount_amount", sa.String(length=32), nullable=True),
        sa.Column("tax_amount", sa.String(length=32), nullable=True),
        sa.Column("remaining_amount", sa.String(length=32), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("truth_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_slug",
            "external_order_id",
            "truth_version",
            name="uq_order_economic_fact_grain",
        ),
    )
    op.create_index("ix_order_economic_facts_store_slug", "order_economic_facts", ["store_slug"])
    op.create_index(
        "ix_order_economic_facts_external_order_id",
        "order_economic_facts",
        ["external_order_id"],
    )
    op.create_index("ix_order_economic_facts_observed_at", "order_economic_facts", ["observed_at"])
    op.create_index(
        "ix_oef_store_currency_observed",
        "order_economic_facts",
        ["store_slug", "currency", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_oef_store_currency_observed", table_name="order_economic_facts")
    op.drop_index("ix_order_economic_facts_observed_at", table_name="order_economic_facts")
    op.drop_index("ix_order_economic_facts_external_order_id", table_name="order_economic_facts")
    op.drop_index("ix_order_economic_facts_store_slug", table_name="order_economic_facts")
    op.drop_table("order_economic_facts")
