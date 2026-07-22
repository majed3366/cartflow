"""add business findings lifecycle table

Revision ID: i8j9k0l1m2n3
Revises: h7i8j9k0l1m2
Create Date: 2026-07-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i8j9k0l1m2n3"
down_revision: Union[str, Sequence[str], None] = "h7i8j9k0l1m2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("finding_id", sa.String(length=128), nullable=False),
        sa.Column("finding_type", sa.String(length=96), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("merchant_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("product_id", sa.String(length=256), nullable=True),
        sa.Column("category_id", sa.String(length=128), nullable=True),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("confidence", sa.String(length=32), nullable=False, server_default=""),
        sa.Column(
            "confidence_score", sa.String(length=32), nullable=False, server_default=""
        ),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column(
            "lifecycle_state",
            sa.String(length=48),
            nullable=False,
            server_default="detected",
        ),
        sa.Column(
            "visibility_state",
            sa.String(length=32),
            nullable=False,
            server_default="hidden",
        ),
        sa.Column("reasoning_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("recommended_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("merchant_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("routing_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "lifecycle_events_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column("diagnostics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("fingerprint", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("engine_version", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "lifecycle_version",
            sa.String(length=32),
            nullable=False,
            server_default="bfl_v1",
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("as_of_key", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("finding_id", name="uq_business_finding_id"),
    )
    op.create_index("ix_business_findings_finding_id", "business_findings", ["finding_id"])
    op.create_index("ix_business_findings_store_slug", "business_findings", ["store_slug"])
    op.create_index(
        "ix_business_findings_lifecycle_state", "business_findings", ["lifecycle_state"]
    )
    op.create_index(
        "ix_business_findings_is_current", "business_findings", ["is_current"]
    )
    op.create_index(
        "ix_business_findings_finding_type", "business_findings", ["finding_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_business_findings_finding_type", table_name="business_findings")
    op.drop_index("ix_business_findings_is_current", table_name="business_findings")
    op.drop_index("ix_business_findings_lifecycle_state", table_name="business_findings")
    op.drop_index("ix_business_findings_store_slug", table_name="business_findings")
    op.drop_index("ix_business_findings_finding_id", table_name="business_findings")
    op.drop_table("business_findings")
