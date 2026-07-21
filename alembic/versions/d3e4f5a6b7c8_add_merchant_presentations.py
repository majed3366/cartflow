"""add merchant presentations

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "merchant_presentations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("presentation_id", sa.String(length=64), nullable=False),
        sa.Column("route_id", sa.String(length=64), nullable=False),
        sa.Column("guidance_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("subject_id", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("surface_key", sa.String(length=64), nullable=False),
        sa.Column("route_scope", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("route_role", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("guidance_key", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("presentation_type", sa.String(length=64), nullable=False),
        sa.Column("presentation_state", sa.String(length=32), nullable=False),
        sa.Column("headline_key", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("headline_text", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "primary_statement_key", sa.String(length=128), nullable=False, server_default=""
        ),
        sa.Column("primary_statement_text", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "supporting_statement_key",
            sa.String(length=128),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "supporting_statement_text", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column("known_facts_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("unknown_facts_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_state", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "merchant_relevance_key", sa.String(length=128), nullable=False, server_default=""
        ),
        sa.Column(
            "merchant_relevance_text", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column(
            "action_affordance", sa.String(length=32), nullable=False, server_default="none"
        ),
        sa.Column("action_label_key", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("disclaimer_key", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("status_label_key", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("template_key", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("template_version", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "presentation_rule_version",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column("language_code", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("failure_reason", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "presentation_version",
            sa.String(length=32),
            nullable=False,
            server_default="mpf_v1",
        ),
        sa.Column(
            "generation_version",
            sa.String(length=32),
            nullable=False,
            server_default="mpf_v1_gen",
        ),
        sa.Column(
            "source_contract_version",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "input_fingerprint", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column(
            "presentation_fingerprint",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("as_of_key", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("presentation_id", name="uq_merchant_presentation_id"),
    )
    for name, cols in (
        ("ix_merchant_presentations_presentation_id", ["presentation_id"]),
        ("ix_merchant_presentations_route_id", ["route_id"]),
        ("ix_merchant_presentations_store_slug", ["store_slug"]),
        ("ix_merchant_presentations_surface_key", ["surface_key"]),
        ("ix_merchant_presentations_presentation_type", ["presentation_type"]),
        ("ix_merchant_presentations_presentation_state", ["presentation_state"]),
        ("ix_merchant_presentations_is_current", ["is_current"]),
        ("ix_merchant_presentations_valid_until", ["valid_until"]),
        ("ix_merchant_presentations_presentation_fingerprint", ["presentation_fingerprint"]),
        (
            "ix_merchant_presentations_store_surface_current",
            ["store_slug", "surface_key", "is_current"],
        ),
        ("ix_merchant_presentations_store_route", ["store_slug", "route_id"]),
        (
            "ix_merchant_presentations_store_subject",
            ["store_slug", "subject_type", "subject_id"],
        ),
        ("ix_merchant_presentations_route_current", ["route_id", "is_current"]),
    ):
        op.create_index(name, "merchant_presentations", cols)


def downgrade() -> None:
    for name in (
        "ix_merchant_presentations_route_current",
        "ix_merchant_presentations_store_subject",
        "ix_merchant_presentations_store_route",
        "ix_merchant_presentations_store_surface_current",
        "ix_merchant_presentations_presentation_fingerprint",
        "ix_merchant_presentations_valid_until",
        "ix_merchant_presentations_is_current",
        "ix_merchant_presentations_presentation_state",
        "ix_merchant_presentations_presentation_type",
        "ix_merchant_presentations_surface_key",
        "ix_merchant_presentations_store_slug",
        "ix_merchant_presentations_route_id",
        "ix_merchant_presentations_presentation_id",
    ):
        op.drop_index(name, table_name="merchant_presentations")
    op.drop_table("merchant_presentations")
