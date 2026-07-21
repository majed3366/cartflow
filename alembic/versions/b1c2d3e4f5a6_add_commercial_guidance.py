"""add commercial guidance records

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_guidance_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guidance_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("subject_id", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("guidance_key", sa.String(length=64), nullable=False),
        sa.Column(
            "guidance_version",
            sa.String(length=32),
            nullable=False,
            server_default="cgf_v1",
        ),
        sa.Column(
            "guidance_scope",
            sa.String(length=64),
            nullable=False,
            server_default="commercial_v1",
        ),
        sa.Column("eligibility_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "eligibility_status", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column(
            "knowledge_reference_ids_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "source_contract_version",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column("rule_version", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("guidance_status", sa.String(length=32), nullable=False),
        sa.Column("rationale_code", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("rationale_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("known_facts_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("unknown_facts_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "prohibited_claims_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "input_fingerprint", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column(
            "guidance_fingerprint",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "generation_version",
            sa.String(length=32),
            nullable=False,
            server_default="cgf_v1_gen",
        ),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("as_of_key", sa.String(length=32), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("guidance_id", name="uq_commercial_guidance_id"),
    )
    for name, cols in (
        ("ix_commercial_guidance_records_guidance_id", ["guidance_id"]),
        ("ix_commercial_guidance_records_store_slug", ["store_slug"]),
        ("ix_commercial_guidance_records_subject_type", ["subject_type"]),
        ("ix_commercial_guidance_records_subject_id", ["subject_id"]),
        ("ix_commercial_guidance_records_guidance_key", ["guidance_key"]),
        ("ix_commercial_guidance_records_guidance_status", ["guidance_status"]),
        ("ix_commercial_guidance_records_is_current", ["is_current"]),
        ("ix_commercial_guidance_records_as_of", ["as_of"]),
        (
            "ix_commercial_guidance_current_grain",
            ["store_slug", "subject_type", "subject_id", "guidance_scope", "is_current"],
        ),
    ):
        op.create_index(name, "commercial_guidance_records", cols)


def downgrade() -> None:
    for name in (
        "ix_commercial_guidance_current_grain",
        "ix_commercial_guidance_records_as_of",
        "ix_commercial_guidance_records_is_current",
        "ix_commercial_guidance_records_guidance_status",
        "ix_commercial_guidance_records_guidance_key",
        "ix_commercial_guidance_records_subject_id",
        "ix_commercial_guidance_records_subject_type",
        "ix_commercial_guidance_records_store_slug",
        "ix_commercial_guidance_records_guidance_id",
    ):
        op.drop_index(name, table_name="commercial_guidance_records")
    op.drop_table("commercial_guidance_records")
