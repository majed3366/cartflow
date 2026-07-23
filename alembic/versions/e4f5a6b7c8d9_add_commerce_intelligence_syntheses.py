"""add commerce intelligence syntheses

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commerce_intelligence_syntheses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("synthesis_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("synthesis_key", sa.String(length=64), nullable=False),
        sa.Column("synthesis_rule_key", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("subject_id", sa.String(length=256), nullable=False, server_default=""),
        sa.Column(
            "comparison_subject_type",
            sa.String(length=32),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "comparison_subject_id",
            sa.String(length=256),
            nullable=False,
            server_default="",
        ),
        sa.Column("time_window_key", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("window_end", sa.DateTime(), nullable=False),
        sa.Column("synthesis_state", sa.String(length=32), nullable=False),
        sa.Column("pattern_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "pattern_direction", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column(
            "commercial_domain", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column("source_domains_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "source_record_ids_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column(
            "source_contributions_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "required_source_domains_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "missing_source_domains_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("known_facts_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("unknown_facts_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "conflicting_facts_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column(
            "prohibited_claims_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column(
            "supporting_evidence_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "contradicting_evidence_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "minimum_sample_size", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "evidence_coverage", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column(
            "confidence_input_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "significance_input_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "commercial_relevance_input_json",
            sa.Text(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "synthesis_summary_key",
            sa.String(length=128),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "input_fingerprint", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column(
            "synthesis_fingerprint",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column("rule_version", sa.String(length=32), nullable=False, server_default=""),
        sa.Column(
            "contract_version", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column(
            "synthesis_version",
            sa.String(length=32),
            nullable=False,
            server_default="cisyn_v1",
        ),
        sa.Column(
            "generation_version",
            sa.String(length=32),
            nullable=False,
            server_default="cisyn_v1_gen",
        ),
        sa.Column(
            "failure_reason", sa.String(length=128), nullable=False, server_default=""
        ),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("as_of_key", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("synthesis_id", name="uq_commerce_intelligence_synthesis_id"),
    )
    for name, cols in (
        ("ix_cisyn_synthesis_id", ["synthesis_id"]),
        ("ix_cisyn_store_slug", ["store_slug"]),
        ("ix_cisyn_synthesis_key", ["synthesis_key"]),
        ("ix_cisyn_synthesis_rule_key", ["synthesis_rule_key"]),
        ("ix_cisyn_subject_type", ["subject_type"]),
        ("ix_cisyn_pattern_type", ["pattern_type"]),
        ("ix_cisyn_synthesis_state", ["synthesis_state"]),
        ("ix_cisyn_is_current", ["is_current"]),
        ("ix_cisyn_valid_until", ["valid_until"]),
        ("ix_cisyn_synthesis_fingerprint", ["synthesis_fingerprint"]),
        ("ix_cisyn_store_current", ["store_slug", "is_current"]),
        ("ix_cisyn_store_key_current", ["store_slug", "synthesis_key", "is_current"]),
        ("ix_cisyn_store_subject_current", ["store_slug", "subject_type", "is_current"]),
        ("ix_cisyn_store_pattern_current", ["store_slug", "pattern_type", "is_current"]),
        ("ix_cisyn_store_state_current", ["store_slug", "synthesis_state", "is_current"]),
        (
            "ix_cisyn_rule_subject_window",
            ["synthesis_rule_key", "subject_type", "time_window_key"],
        ),
    ):
        op.create_index(name, "commerce_intelligence_syntheses", cols)


def downgrade() -> None:
    for name in (
        "ix_cisyn_rule_subject_window",
        "ix_cisyn_store_state_current",
        "ix_cisyn_store_pattern_current",
        "ix_cisyn_store_subject_current",
        "ix_cisyn_store_key_current",
        "ix_cisyn_store_current",
        "ix_cisyn_synthesis_fingerprint",
        "ix_cisyn_valid_until",
        "ix_cisyn_is_current",
        "ix_cisyn_synthesis_state",
        "ix_cisyn_pattern_type",
        "ix_cisyn_subject_type",
        "ix_cisyn_synthesis_rule_key",
        "ix_cisyn_synthesis_key",
        "ix_cisyn_store_slug",
        "ix_cisyn_synthesis_id",
    ):
        op.drop_index(name, table_name="commerce_intelligence_syntheses")
    op.drop_table("commerce_intelligence_syntheses")
