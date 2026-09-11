# -*- coding: utf-8 -*-
"""Follow-on ALTER: Zid widget install + storefront runtime truth on stores.

Revision ID: f5altstorezi01
Revises: f4altstoreui01
Create Date: 2026-06-03

widget_installation_status is TEXT on production (create_all helper),
not VARCHAR(32) from the current Store class.

| COLUMN | FIRST COMMIT | OWNER | PROD | CONF |
|--------|--------------|-------|------|------|
| widget_installation_status / installed_at / last_seen / install_error | 06f93d78 2026-06-03 | schema_zid_widget_install | live TEXT | HIGH |
| widget_last_runtime_slug / beacon / runtime_truth_* | 61c3b3e2 2026-06-03 | schema_storefront_runtime_truth | live | HIGH |
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f5altstorezi01"
down_revision: Union[str, Sequence[str], None] = "f4altstoreui01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("widget_installation_status", sa.Text(), nullable=True))
    op.add_column("stores", sa.Column("widget_installed_at", sa.DateTime(), nullable=True))
    op.add_column("stores", sa.Column("widget_last_seen_at", sa.DateTime(), nullable=True))
    op.add_column("stores", sa.Column("widget_install_error", sa.Text(), nullable=True))
    op.add_column(
        "stores",
        sa.Column("widget_last_runtime_slug", sa.String(length=255), nullable=True),
    )
    op.add_column("stores", sa.Column("widget_last_beacon_json", sa.Text(), nullable=True))
    op.add_column(
        "stores",
        sa.Column("widget_runtime_truth_status", sa.String(length=32), nullable=True),
    )
    op.add_column("stores", sa.Column("widget_runtime_truth_json", sa.Text(), nullable=True))
    op.add_column("stores", sa.Column("widget_runtime_truth_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "widget_runtime_truth_at")
    op.drop_column("stores", "widget_runtime_truth_json")
    op.drop_column("stores", "widget_runtime_truth_status")
    op.drop_column("stores", "widget_last_beacon_json")
    op.drop_column("stores", "widget_last_runtime_slug")
    op.drop_column("stores", "widget_install_error")
    op.drop_column("stores", "widget_last_seen_at")
    op.drop_column("stores", "widget_installed_at")
    op.drop_column("stores", "widget_installation_status")
