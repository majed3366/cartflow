"""add evidence confidence evaluations

Revision ID: y8z9a0b1c2d3
Revises: x7y8z9a0b1c2
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "y8z9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "x7y8z9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_confidence_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("confidence_id", sa.String(length=64), nullable=False),
        sa.Column("evidence_bundle_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("subject_id", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("confidence_level", sa.String(length=32), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "confidence_version", sa.String(length=32), nullable=False, server_default="ecf_v1"
        ),
        sa.Column(
            "evaluator_version",
            sa.String(length=32),
            nullable=False,
            server_default="ecf_v1_eval",
        ),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("as_of_key", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("completeness", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("freshness", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consistency", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_diversity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "missing_sources_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column(
            "conflicting_signals", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column(
            "confidence_notes_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column("factors_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("confidence_id", name="uq_evidence_confidence_id"),
        sa.UniqueConstraint(
            "evidence_bundle_id",
            "confidence_version",
            "evaluator_version",
            "as_of_key",
            name="uq_evidence_confidence_grain",
        ),
    )
    for name, col in (
        ("ix_evidence_confidence_evaluations_confidence_id", "confidence_id"),
        ("ix_evidence_confidence_evaluations_evidence_bundle_id", "evidence_bundle_id"),
        ("ix_evidence_confidence_evaluations_store_slug", "store_slug"),
        ("ix_evidence_confidence_evaluations_confidence_level", "confidence_level"),
        ("ix_evidence_confidence_evaluations_evaluated_at", "evaluated_at"),
        ("ix_evidence_confidence_evaluations_as_of", "as_of"),
    ):
        op.create_index(name, "evidence_confidence_evaluations", [col])


def downgrade() -> None:
    for name in (
        "ix_evidence_confidence_evaluations_as_of",
        "ix_evidence_confidence_evaluations_evaluated_at",
        "ix_evidence_confidence_evaluations_confidence_level",
        "ix_evidence_confidence_evaluations_store_slug",
        "ix_evidence_confidence_evaluations_evidence_bundle_id",
        "ix_evidence_confidence_evaluations_confidence_id",
    ):
        op.drop_index(name, table_name="evidence_confidence_evaluations")
    op.drop_table("evidence_confidence_evaluations")
