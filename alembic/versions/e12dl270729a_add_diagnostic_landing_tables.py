# -*- coding: utf-8 -*-
"""E12 diagnostic / evidence gaps / landing events — 2a8d91dc / 570cec94 / 7918de1a.

Revision ID: e12dl270729a
Revises: e11rl040704a
Create Date: 2026-07-29
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e12dl270729a"
down_revision: Union[str, Sequence[str], None] = "e11rl040704a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "diagnostic_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("diagnostic_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=256), nullable=False),
        sa.Column("diagnostic_family", sa.String(length=96), nullable=False),
        sa.Column("diagnosis_status", sa.String(length=48), nullable=False),
        sa.Column("confidence_level", sa.String(length=32), nullable=False),
        sa.Column("selected_diagnosis", sa.String(length=96), nullable=True),
        sa.Column("observation_ar", sa.Text(), nullable=False),
        sa.Column("diagnosis_ar", sa.Text(), nullable=False),
        sa.Column("recommendation_ar", sa.Text(), nullable=False),
        sa.Column("contract_json", sa.Text(), nullable=False),
        sa.Column("publication_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("diagnostic_version", sa.String(length=64), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_good_contract_json", sa.Text(), nullable=False),
        sa.Column("last_good_generated_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_slug",
            "subject_type",
            "subject_id",
            "diagnostic_family",
            name="uq_diagnostic_snapshot_identity",
        ),
    )
    op.create_index(
        "ix_diagnostic_snapshots_diagnostic_id", "diagnostic_snapshots", ["diagnostic_id"]
    )
    op.create_index(
        "ix_diagnostic_snapshots_store_slug", "diagnostic_snapshots", ["store_slug"]
    )
    op.create_index(
        "ix_diagnostic_snapshots_diagnostic_family",
        "diagnostic_snapshots",
        ["diagnostic_family"],
    )
    op.create_index(
        "ix_diagnostic_snapshots_generated_at", "diagnostic_snapshots", ["generated_at"]
    )
    op.create_index(
        "ix_diagnostic_snapshots_expires_at", "diagnostic_snapshots", ["expires_at"]
    )
    op.create_index("ix_diagnostic_snapshots_status", "diagnostic_snapshots", ["status"])
    op.create_index(
        "ix_diagnostic_snapshots_store_family",
        "diagnostic_snapshots",
        ["store_slug", "diagnostic_family"],
    )

    op.create_table(
        "evidence_gaps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gap_id", sa.String(length=64), nullable=False),
        sa.Column("store_slug", sa.String(length=255), nullable=False),
        sa.Column("diagnostic_family", sa.String(length=96), nullable=False),
        sa.Column("diagnostic_id", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=256), nullable=False),
        sa.Column("diagnosis_status", sa.String(length=48), nullable=False),
        sa.Column("gap_status", sa.String(length=48), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("evidence_expansion_version", sa.String(length=64), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("internal_only", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evidence_gaps_gap_id", "evidence_gaps", ["gap_id"], unique=True
    )
    op.create_index("ix_evidence_gaps_store_slug", "evidence_gaps", ["store_slug"])
    op.create_index(
        "ix_evidence_gaps_diagnostic_family", "evidence_gaps", ["diagnostic_family"]
    )
    op.create_index("ix_evidence_gaps_gap_status", "evidence_gaps", ["gap_status"])
    op.create_index("ix_evidence_gaps_generated_at", "evidence_gaps", ["generated_at"])
    op.create_index(
        "ix_evidence_gaps_store_status", "evidence_gaps", ["store_slug", "gap_status"]
    )
    op.create_index("ix_evidence_gaps_family", "evidence_gaps", ["diagnostic_family"])

    op.create_table(
        "landing_page_events_v1",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("section", sa.String(length=64), nullable=True),
        sa.Column("device", sa.String(length=16), nullable=False),
        sa.Column("session_key", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_landing_page_events_v1_event_name", "landing_page_events_v1", ["event_name"]
    )
    op.create_index(
        "ix_landing_page_events_v1_created_at", "landing_page_events_v1", ["created_at"]
    )
    op.create_index(
        "ix_lp_events_v1_name_created",
        "landing_page_events_v1",
        ["event_name", "created_at"],
    )
    op.create_index("ix_lp_events_v1_session", "landing_page_events_v1", ["session_key"])


def downgrade() -> None:
    op.drop_index("ix_lp_events_v1_session", table_name="landing_page_events_v1")
    op.drop_index("ix_lp_events_v1_name_created", table_name="landing_page_events_v1")
    op.drop_index(
        "ix_landing_page_events_v1_created_at", table_name="landing_page_events_v1"
    )
    op.drop_index(
        "ix_landing_page_events_v1_event_name", table_name="landing_page_events_v1"
    )
    op.drop_table("landing_page_events_v1")
    op.drop_index("ix_evidence_gaps_family", table_name="evidence_gaps")
    op.drop_index("ix_evidence_gaps_store_status", table_name="evidence_gaps")
    op.drop_index("ix_evidence_gaps_generated_at", table_name="evidence_gaps")
    op.drop_index("ix_evidence_gaps_gap_status", table_name="evidence_gaps")
    op.drop_index("ix_evidence_gaps_diagnostic_family", table_name="evidence_gaps")
    op.drop_index("ix_evidence_gaps_store_slug", table_name="evidence_gaps")
    op.drop_index("ix_evidence_gaps_gap_id", table_name="evidence_gaps")
    op.drop_table("evidence_gaps")
    op.drop_index(
        "ix_diagnostic_snapshots_store_family", table_name="diagnostic_snapshots"
    )
    op.drop_index("ix_diagnostic_snapshots_status", table_name="diagnostic_snapshots")
    op.drop_index("ix_diagnostic_snapshots_expires_at", table_name="diagnostic_snapshots")
    op.drop_index(
        "ix_diagnostic_snapshots_generated_at", table_name="diagnostic_snapshots"
    )
    op.drop_index(
        "ix_diagnostic_snapshots_diagnostic_family", table_name="diagnostic_snapshots"
    )
    op.drop_index("ix_diagnostic_snapshots_store_slug", table_name="diagnostic_snapshots")
    op.drop_index(
        "ix_diagnostic_snapshots_diagnostic_id", table_name="diagnostic_snapshots"
    )
    op.drop_table("diagnostic_snapshots")
