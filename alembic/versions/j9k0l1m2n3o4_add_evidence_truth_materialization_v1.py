"""add evidence truth materialization bridge tables

Revision ID: j9k0l1m2n3o4
Revises: i8j9k0l1m2n3
Create Date: 2026-07-24

WP-ET-10.6 durable shadow artifacts + materialization runs.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j9k0l1m2n3o4"
down_revision: Union[str, Sequence[str], None] = "i8j9k0l1m2n3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_truth_materialization_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("materialization_run_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="dry_run"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="started"),
        sa.Column("batch_limit", sa.Integer(), nullable=False, server_default="50"),
        sa.Column(
            "composer_version",
            sa.String(length=64),
            nullable=False,
            server_default="wp_et_10_6_v1",
        ),
        sa.Column("accounting_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_json", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "materialization_run_id", name="uq_et_materialization_run_id"
        ),
    )
    op.create_index(
        "ix_et_mat_runs_run_id",
        "evidence_truth_materialization_runs",
        ["materialization_run_id"],
    )
    op.create_index(
        "ix_et_mat_runs_store_slug",
        "evidence_truth_materialization_runs",
        ["store_slug"],
    )
    op.create_index(
        "ix_et_mat_runs_status",
        "evidence_truth_materialization_runs",
        ["status"],
    )
    op.create_index(
        "ix_et_mat_runs_created_at",
        "evidence_truth_materialization_runs",
        ["created_at"],
    )

    op.create_table(
        "evidence_truth_shadow_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("artifact_kind", sa.String(length=32), nullable=False),
        sa.Column("artifact_id", sa.String(length=128), nullable=False),
        sa.Column("artifact_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("materialization_run_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=192), nullable=False),
        sa.Column("source_ref", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("lineage_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "composer_version",
            sa.String(length=64),
            nullable=False,
            server_default="wp_et_10_6_v1",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_et_shadow_artifact_idempotency"
        ),
    )
    for name, cols in (
        ("ix_et_shadow_artifacts_kind", ["artifact_kind"]),
        ("ix_et_shadow_artifacts_artifact_id", ["artifact_id"]),
        ("ix_et_shadow_artifacts_store_slug", ["store_slug"]),
        ("ix_et_shadow_artifacts_run_id", ["materialization_run_id"]),
        ("ix_et_shadow_artifacts_created_at", ["created_at"]),
        ("ix_et_shadow_artifacts_store_kind", ["store_slug", "artifact_kind"]),
    ):
        op.create_index(name, "evidence_truth_shadow_artifacts", cols)


def downgrade() -> None:
    op.drop_table("evidence_truth_shadow_artifacts")
    op.drop_table("evidence_truth_materialization_runs")
