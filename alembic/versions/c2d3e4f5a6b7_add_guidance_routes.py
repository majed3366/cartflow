"""add guidance routes

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guidance_routes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("route_id", sa.String(length=64), nullable=False),
        sa.Column("guidance_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("subject_id", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("surface_key", sa.String(length=64), nullable=False),
        sa.Column("guidance_key", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("route_scope", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("route_role", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("route_status", sa.String(length=32), nullable=False),
        sa.Column(
            "routing_rationale_code", sa.String(length=128), nullable=False, server_default=""
        ),
        sa.Column(
            "routing_context_digest", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "routing_version", sa.String(length=32), nullable=False, server_default="grf_v1"
        ),
        sa.Column(
            "routing_rule_version", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column(
            "surface_registry_version",
            sa.String(length=32),
            nullable=False,
            server_default="gsurf_v1",
        ),
        sa.Column(
            "routing_registry_version",
            sa.String(length=32),
            nullable=False,
            server_default="grule_v1",
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
            "route_fingerprint", sa.String(length=64), nullable=False, server_default=""
        ),
        sa.Column(
            "generation_version",
            sa.String(length=32),
            nullable=False,
            server_default="grf_v1_eval",
        ),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("as_of_key", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("route_id", name="uq_guidance_route_id"),
    )
    for name, cols in (
        ("ix_guidance_routes_route_id", ["route_id"]),
        ("ix_guidance_routes_guidance_id", ["guidance_id"]),
        ("ix_guidance_routes_store_slug", ["store_slug"]),
        ("ix_guidance_routes_surface_key", ["surface_key"]),
        ("ix_guidance_routes_route_status", ["route_status"]),
        ("ix_guidance_routes_is_current", ["is_current"]),
        ("ix_guidance_routes_valid_until", ["valid_until"]),
        ("ix_guidance_routes_route_fingerprint", ["route_fingerprint"]),
        (
            "ix_guidance_routes_store_surface_current",
            ["store_slug", "surface_key", "is_current"],
        ),
        (
            "ix_guidance_routes_store_guidance",
            ["store_slug", "guidance_id"],
        ),
        (
            "ix_guidance_routes_guidance_surface",
            ["guidance_id", "surface_key"],
        ),
        (
            "ix_guidance_routes_store_subject",
            ["store_slug", "subject_type", "subject_id"],
        ),
    ):
        op.create_index(name, "guidance_routes", cols)


def downgrade() -> None:
    for name in (
        "ix_guidance_routes_store_subject",
        "ix_guidance_routes_guidance_surface",
        "ix_guidance_routes_store_guidance",
        "ix_guidance_routes_store_surface_current",
        "ix_guidance_routes_route_fingerprint",
        "ix_guidance_routes_valid_until",
        "ix_guidance_routes_is_current",
        "ix_guidance_routes_route_status",
        "ix_guidance_routes_surface_key",
        "ix_guidance_routes_store_slug",
        "ix_guidance_routes_guidance_id",
        "ix_guidance_routes_route_id",
    ):
        op.drop_index(name, table_name="guidance_routes")
    op.drop_table("guidance_routes")
