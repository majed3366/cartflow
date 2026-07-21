"""add guidance eligibility evaluations

Revision ID: a0b1c2d3e4f5
Revises: z9a0b1c2d3e4
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "z9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guidance_eligibility_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("eligibility_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("subject_id", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("eligibility_status", sa.String(length=64), nullable=False),
        sa.Column("eligibility_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("knowledge_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "required_knowledge_count", sa.Integer(), nullable=False, server_default="2"
        ),
        sa.Column(
            "blocking_conditions_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column("knowledge_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("as_of_key", sa.String(length=32), nullable=False, server_default=""),
        sa.Column(
            "eligibility_version",
            sa.String(length=32),
            nullable=False,
            server_default="gef_v1",
        ),
        sa.Column("fingerprint", sa.String(length=64), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("eligibility_id", name="uq_guidance_eligibility_id"),
        sa.UniqueConstraint(
            "store_slug",
            "subject_type",
            "subject_id",
            "eligibility_version",
            "as_of_key",
            name="uq_guidance_eligibility_grain",
        ),
    )
    for name, col in (
        ("ix_guidance_eligibility_evaluations_eligibility_id", "eligibility_id"),
        ("ix_guidance_eligibility_evaluations_store_slug", "store_slug"),
        ("ix_guidance_eligibility_evaluations_subject_type", "subject_type"),
        ("ix_guidance_eligibility_evaluations_subject_id", "subject_id"),
        ("ix_guidance_eligibility_evaluations_eligibility_status", "eligibility_status"),
        ("ix_guidance_eligibility_evaluations_evaluated_at", "evaluated_at"),
        ("ix_guidance_eligibility_evaluations_as_of", "as_of"),
    ):
        op.create_index(name, "guidance_eligibility_evaluations", [col])


def downgrade() -> None:
    for name in (
        "ix_guidance_eligibility_evaluations_as_of",
        "ix_guidance_eligibility_evaluations_evaluated_at",
        "ix_guidance_eligibility_evaluations_eligibility_status",
        "ix_guidance_eligibility_evaluations_subject_id",
        "ix_guidance_eligibility_evaluations_subject_type",
        "ix_guidance_eligibility_evaluations_store_slug",
        "ix_guidance_eligibility_evaluations_eligibility_id",
    ):
        op.drop_index(name, table_name="guidance_eligibility_evaluations")
    op.drop_table("guidance_eligibility_evaluations")
