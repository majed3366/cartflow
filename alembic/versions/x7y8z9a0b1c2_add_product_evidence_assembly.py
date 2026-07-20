"""add product evidence assembly tables

Revision ID: x7y8z9a0b1c2
Revises: w6x7y8z9a0b1
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "x7y8z9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "w6x7y8z9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_evidence_bundles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evidence_bundle_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=256), nullable=False),
        sa.Column(
            "bundle_version", sa.String(length=32), nullable=False, server_default="pea_v1"
        ),
        sa.Column("assembled_at", sa.DateTime(), nullable=False),
        sa.Column("assembly_window", sa.String(length=16), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("as_of_key", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fingerprint", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "computation_version",
            sa.String(length=32),
            nullable=False,
            server_default="pea_v1_assemble",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_bundle_id", name="uq_product_evidence_bundle_id"),
        sa.UniqueConstraint(
            "store_slug",
            "subject_type",
            "subject_id",
            "assembly_window",
            "as_of_key",
            "bundle_version",
            name="uq_product_evidence_bundle_grain",
        ),
    )
    for name, col in (
        ("ix_product_evidence_bundles_evidence_bundle_id", "evidence_bundle_id"),
        ("ix_product_evidence_bundles_store_slug", "store_slug"),
        ("ix_product_evidence_bundles_subject_type", "subject_type"),
        ("ix_product_evidence_bundles_subject_id", "subject_id"),
        ("ix_product_evidence_bundles_assembled_at", "assembled_at"),
        ("ix_product_evidence_bundles_assembly_window", "assembly_window"),
        ("ix_product_evidence_bundles_as_of", "as_of"),
    ):
        op.create_index(name, "product_evidence_bundles", [col])

    op.create_table(
        "product_evidence_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evidence_bundle_id", sa.String(length=64), nullable=False),
        sa.Column("evidence_item_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("subject_id", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("metric_key", sa.String(length=64), nullable=False),
        sa.Column("metric_value", sa.Integer(), nullable=True),
        sa.Column("trend_direction", sa.String(length=32), nullable=True),
        sa.Column("trend_window", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("source_layer", sa.String(length=32), nullable=False),
        sa.Column(
            "source_record_id", sa.String(length=128), nullable=False, server_default=""
        ),
        sa.Column("observed_from", sa.DateTime(), nullable=True),
        sa.Column("observed_to", sa.DateTime(), nullable=True),
        sa.Column("lineage_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("assembled_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evidence_bundle_id",
            "evidence_item_id",
            name="uq_product_evidence_item_id",
        ),
    )
    for name, col in (
        ("ix_product_evidence_items_evidence_bundle_id", "evidence_bundle_id"),
        ("ix_product_evidence_items_evidence_item_id", "evidence_item_id"),
        ("ix_product_evidence_items_store_slug", "store_slug"),
        ("ix_product_evidence_items_metric_key", "metric_key"),
        ("ix_product_evidence_items_source_layer", "source_layer"),
        ("ix_product_evidence_items_assembled_at", "assembled_at"),
    ):
        op.create_index(name, "product_evidence_items", [col])


def downgrade() -> None:
    for name in (
        "ix_product_evidence_items_assembled_at",
        "ix_product_evidence_items_source_layer",
        "ix_product_evidence_items_metric_key",
        "ix_product_evidence_items_store_slug",
        "ix_product_evidence_items_evidence_item_id",
        "ix_product_evidence_items_evidence_bundle_id",
    ):
        op.drop_index(name, table_name="product_evidence_items")
    op.drop_table("product_evidence_items")
    for name in (
        "ix_product_evidence_bundles_as_of",
        "ix_product_evidence_bundles_assembly_window",
        "ix_product_evidence_bundles_assembled_at",
        "ix_product_evidence_bundles_subject_id",
        "ix_product_evidence_bundles_subject_type",
        "ix_product_evidence_bundles_store_slug",
        "ix_product_evidence_bundles_evidence_bundle_id",
    ):
        op.drop_index(name, table_name="product_evidence_bundles")
    op.drop_table("product_evidence_bundles")
