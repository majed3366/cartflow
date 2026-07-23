"""add surface compositions

Revision ID: h7i8j9k0l1m2
Revises: g6a7b8c9d0e1
Create Date: 2026-07-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h7i8j9k0l1m2"
down_revision: Union[str, Sequence[str], None] = "g6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "surface_compositions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("composition_id", sa.String(length=64), nullable=False),
        sa.Column("surface_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("source_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("source_lineage_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("information_class", sa.String(length=64), nullable=False),
        sa.Column(
            "presentation_intent", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column("merchant_value", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("urgency", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("freshness_state", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("confidence", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("expiry", sa.DateTime(), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default=""),
        sa.Column(
            "visibility_reason", sa.String(length=128), nullable=False, server_default=""
        ),
        sa.Column(
            "destination_surfaces_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column("duplicate_group", sa.String(length=128), nullable=False, server_default=""),
        sa.Column(
            "owns_full_explanation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "suppression_rules_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "accounting_outcome", sa.String(length=32), nullable=False, server_default=""
        ),
        sa.Column("lifecycle", sa.String(length=32), nullable=False, server_default="create"),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "composition_version",
            sa.String(length=32),
            nullable=False,
            server_default="scf_v1",
        ),
        sa.Column(
            "generation_version",
            sa.String(length=32),
            nullable=False,
            server_default="scf_v1_gen",
        ),
        sa.Column(
            "surface_registry_version",
            sa.String(length=32),
            nullable=False,
            server_default="sreg_v1",
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
        sa.Column("fingerprint", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("failure_reason", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("as_of_key", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("composition_id", name="uq_surface_composition_id"),
    )
    op.create_index(
        "ix_surface_compositions_composition_id",
        "surface_compositions",
        ["composition_id"],
    )
    op.create_index(
        "ix_surface_compositions_surface_id", "surface_compositions", ["surface_id"]
    )
    op.create_index(
        "ix_surface_compositions_store_slug", "surface_compositions", ["store_slug"]
    )
    op.create_index(
        "ix_surface_compositions_source_id", "surface_compositions", ["source_id"]
    )
    op.create_index(
        "ix_surface_compositions_information_class",
        "surface_compositions",
        ["information_class"],
    )
    op.create_index(
        "ix_surface_compositions_freshness_state",
        "surface_compositions",
        ["freshness_state"],
    )
    op.create_index(
        "ix_surface_compositions_visibility", "surface_compositions", ["visibility"]
    )
    op.create_index(
        "ix_surface_compositions_duplicate_group",
        "surface_compositions",
        ["duplicate_group"],
    )
    op.create_index(
        "ix_surface_compositions_priority", "surface_compositions", ["priority"]
    )
    op.create_index(
        "ix_surface_compositions_accounting_outcome",
        "surface_compositions",
        ["accounting_outcome"],
    )
    op.create_index(
        "ix_surface_compositions_valid_until", "surface_compositions", ["valid_until"]
    )
    op.create_index(
        "ix_surface_compositions_is_current", "surface_compositions", ["is_current"]
    )
    op.create_index(
        "ix_surface_compositions_fingerprint", "surface_compositions", ["fingerprint"]
    )


def downgrade() -> None:
    op.drop_table("surface_compositions")
