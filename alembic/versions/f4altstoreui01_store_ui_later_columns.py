# -*- coding: utf-8 -*-
"""Follow-on ALTER: later create_all merchant UI / VIP / widget columns on stores.

Revision ID: f4altstoreui01
Revises: f3altstorewa01
Create Date: 2026-05-05

| COLUMN | FIRST COMMIT | OWNER | PROD | CONF |
|--------|--------------|-------|------|------|
| widget_enabled / cartflow_widget_* | 7dc2051d 2026-05-05 | Store + schema_widget | live | HIGH |
| cf_widget_trigger_settings_json | f94dac67 2026-05-10 | Store + schema_widget | live | HIGH |
| cf_product_catalog_json / offer cols | 75e20a90 2026-05-10 | Store + schema_widget | live | HIGH |
| vip_enabled / vip_notify_enabled / vip_note | f50ab7e7 2026-05-17 | Store + merchant_vip_settings | live | HIGH |
| settings_notify_* / widget_display_name / merchant_automation_mode | d5b88747 2026-05-18 | Store + merchant_general_settings | live | HIGH |
| vip_offer_* | schema_widget VIP offer | Store | live | HIGH |

merchant_automation_mode is nullable on production (create_all-era ADD).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4altstoreui01"
down_revision: Union[str, Sequence[str], None] = "f3altstorewa01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("widget_enabled", sa.Boolean(), nullable=False))
    op.add_column(
        "stores", sa.Column("widget_display_name", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "stores",
        sa.Column("merchant_automation_mode", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "stores", sa.Column("cartflow_widget_enabled", sa.Boolean(), nullable=False)
    )
    op.add_column(
        "stores", sa.Column("cartflow_widget_delay_value", sa.Integer(), nullable=False)
    )
    op.add_column(
        "stores",
        sa.Column("cartflow_widget_delay_unit", sa.String(length=20), nullable=False),
    )
    op.add_column(
        "stores", sa.Column("cf_widget_trigger_settings_json", sa.Text(), nullable=True)
    )
    op.add_column(
        "stores", sa.Column("cf_product_catalog_json", sa.Text(), nullable=True)
    )
    op.add_column(
        "stores", sa.Column("cf_merchant_offer_settings_json", sa.Text(), nullable=True)
    )
    op.add_column(
        "stores", sa.Column("cf_offer_applications_count", sa.Integer(), nullable=False)
    )
    op.add_column("stores", sa.Column("vip_enabled", sa.Boolean(), nullable=False))
    op.add_column(
        "stores", sa.Column("vip_notify_enabled", sa.Boolean(), nullable=False)
    )
    op.add_column("stores", sa.Column("vip_note", sa.Text(), nullable=True))
    op.add_column("stores", sa.Column("vip_offer_enabled", sa.Boolean(), nullable=False))
    op.add_column(
        "stores", sa.Column("vip_offer_type", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "stores", sa.Column("vip_offer_value", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "stores", sa.Column("settings_notify_vip", sa.Boolean(), nullable=False)
    )
    op.add_column(
        "stores",
        sa.Column("settings_notify_recovery_success", sa.Boolean(), nullable=False),
    )
    op.add_column(
        "stores",
        sa.Column("settings_notify_whatsapp_failure", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("stores", "settings_notify_whatsapp_failure")
    op.drop_column("stores", "settings_notify_recovery_success")
    op.drop_column("stores", "settings_notify_vip")
    op.drop_column("stores", "vip_offer_value")
    op.drop_column("stores", "vip_offer_type")
    op.drop_column("stores", "vip_offer_enabled")
    op.drop_column("stores", "vip_note")
    op.drop_column("stores", "vip_notify_enabled")
    op.drop_column("stores", "vip_enabled")
    op.drop_column("stores", "cf_offer_applications_count")
    op.drop_column("stores", "cf_merchant_offer_settings_json")
    op.drop_column("stores", "cf_product_catalog_json")
    op.drop_column("stores", "cf_widget_trigger_settings_json")
    op.drop_column("stores", "cartflow_widget_delay_unit")
    op.drop_column("stores", "cartflow_widget_delay_value")
    op.drop_column("stores", "cartflow_widget_enabled")
    op.drop_column("stores", "merchant_automation_mode")
    op.drop_column("stores", "widget_display_name")
    op.drop_column("stores", "widget_enabled")
