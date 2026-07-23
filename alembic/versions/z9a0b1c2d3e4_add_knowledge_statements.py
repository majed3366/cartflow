"""add knowledge statements

Revision ID: z9a0b1c2d3e4
Revises: y8z9a0b1c2d3
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "z9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "y8z9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_statements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("knowledge_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("subject_id", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("knowledge_type", sa.String(length=64), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_confidence_id", sa.String(length=64), nullable=False),
        sa.Column(
            "confidence_level", sa.String(length=32), nullable=False, server_default=""
        ),
        sa.Column(
            "assembly_window", sa.String(length=16), nullable=False, server_default=""
        ),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("as_of_key", sa.String(length=32), nullable=False, server_default=""),
        sa.Column(
            "knowledge_version", sa.String(length=32), nullable=False, server_default="kf_v1"
        ),
        sa.Column("fingerprint", sa.String(length=64), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("knowledge_id", name="uq_knowledge_statement_id"),
    )
    for name, col in (
        ("ix_knowledge_statements_knowledge_id", "knowledge_id"),
        ("ix_knowledge_statements_store_slug", "store_slug"),
        ("ix_knowledge_statements_subject_type", "subject_type"),
        ("ix_knowledge_statements_subject_id", "subject_id"),
        ("ix_knowledge_statements_knowledge_type", "knowledge_type"),
        ("ix_knowledge_statements_evidence_confidence_id", "evidence_confidence_id"),
        ("ix_knowledge_statements_valid_from", "valid_from"),
        ("ix_knowledge_statements_valid_until", "valid_until"),
        ("ix_knowledge_statements_generated_at", "generated_at"),
        ("ix_knowledge_statements_as_of", "as_of"),
    ):
        op.create_index(name, "knowledge_statements", [col])


def downgrade() -> None:
    for name in (
        "ix_knowledge_statements_as_of",
        "ix_knowledge_statements_generated_at",
        "ix_knowledge_statements_valid_until",
        "ix_knowledge_statements_valid_from",
        "ix_knowledge_statements_evidence_confidence_id",
        "ix_knowledge_statements_knowledge_type",
        "ix_knowledge_statements_subject_id",
        "ix_knowledge_statements_subject_type",
        "ix_knowledge_statements_store_slug",
        "ix_knowledge_statements_knowledge_id",
    ):
        op.drop_index(name, table_name="knowledge_statements")
    op.drop_table("knowledge_statements")
