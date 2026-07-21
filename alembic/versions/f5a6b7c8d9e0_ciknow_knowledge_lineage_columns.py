"""ciknow knowledge lineage columns

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "knowledge_statements",
        sa.Column(
            "source_type",
            sa.String(length=64),
            nullable=False,
            server_default="evidence_confidence",
        ),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column(
            "source_contract_version",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column(
            "source_synthesis_id",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column(
            "source_synthesis_key",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column(
            "source_rule_key", sa.String(length=64), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column(
            "source_rule_version",
            sa.String(length=32),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column(
            "source_fingerprint",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column("source_window_start", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column("source_window_end", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column(
            "source_domains_json", sa.Text(), nullable=False, server_default="[]"
        ),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column("known_facts_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column("unknown_facts_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column(
            "prohibited_claims_json", sa.Text(), nullable=False, server_default="[]"
        ),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "knowledge_statements",
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_knowledge_statements_source_synthesis_id",
        "knowledge_statements",
        ["source_synthesis_id"],
    )
    op.create_index(
        "ix_knowledge_statements_source_rule_key",
        "knowledge_statements",
        ["source_rule_key"],
    )
    op.create_index(
        "ix_knowledge_statements_is_current",
        "knowledge_statements",
        ["is_current"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_statements_is_current", table_name="knowledge_statements")
    op.drop_index(
        "ix_knowledge_statements_source_rule_key", table_name="knowledge_statements"
    )
    op.drop_index(
        "ix_knowledge_statements_source_synthesis_id",
        table_name="knowledge_statements",
    )
    for col in (
        "superseded_at",
        "is_current",
        "prohibited_claims_json",
        "unknown_facts_json",
        "known_facts_json",
        "source_domains_json",
        "source_window_end",
        "source_window_start",
        "source_fingerprint",
        "source_rule_version",
        "source_rule_key",
        "source_synthesis_key",
        "source_synthesis_id",
        "source_contract_version",
        "source_type",
    ):
        op.drop_column("knowledge_statements", col)
