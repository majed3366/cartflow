"""cguide_v1 Knowledge lineage columns on commercial_guidance_records

Revision ID: g6a7b8c9d0e1
Revises: f5a6b7c8d9e0
Create Date: 2026-07-22
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("commercial_guidance_records"):
        return
    existing = {c["name"] for c in insp.get_columns("commercial_guidance_records")}
    cols = [
        ("knowledge_id", sa.String(64), ""),
        ("knowledge_type", sa.String(64), ""),
        ("merchant_objective", sa.Text(), ""),
        ("eligible_actions_json", sa.Text(), "[]"),
        ("forbidden_actions_json", sa.Text(), "[]"),
        ("confidence_level", sa.String(32), ""),
        ("source_knowledge_fingerprint", sa.String(64), ""),
    ]
    for name, col_type, default in cols:
        if name in existing:
            continue
        op.add_column(
            "commercial_guidance_records",
            sa.Column(name, col_type, nullable=False, server_default=default),
        )
    if "knowledge_id" not in existing:
        op.create_index(
            "ix_commercial_guidance_records_knowledge_id",
            "commercial_guidance_records",
            ["knowledge_id"],
            unique=False,
        )
    if "knowledge_type" not in existing:
        op.create_index(
            "ix_commercial_guidance_records_knowledge_type",
            "commercial_guidance_records",
            ["knowledge_type"],
            unique=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("commercial_guidance_records"):
        return
    existing = {c["name"] for c in insp.get_columns("commercial_guidance_records")}
    for idx in (
        "ix_commercial_guidance_records_knowledge_type",
        "ix_commercial_guidance_records_knowledge_id",
    ):
        try:
            op.drop_index(idx, table_name="commercial_guidance_records")
        except Exception:  # noqa: BLE001
            pass
    for name in (
        "source_knowledge_fingerprint",
        "confidence_level",
        "forbidden_actions_json",
        "eligible_actions_json",
        "merchant_objective",
        "knowledge_type",
        "knowledge_id",
    ):
        if name in existing:
            op.drop_column("commercial_guidance_records", name)
