# -*- coding: utf-8 -*-
"""Follow-on ALTER: later create_all WhatsApp / delay columns on stores.

Revision ID: f3altstorewa01
Revises: f2altacarts01a
Create Date: 2026-05-02

Do not fold these into E0. Surviving Alembic already owns recovery_delay*,
templates, trigger/reason JSON, template_mode/tone, exit_intent, widget
appearance, vip_cart_threshold, integration_source, connected_at,
zid_authorization_token.

| COLUMN | FIRST COMMIT | OWNER | PROD | CONF |
|--------|--------------|-------|------|------|
| whatsapp_support_url | 83cb7edf 2026-04-26 | Store + schema_widget | live | HIGH |
| store_whatsapp_number | fa43421c 2026-05-02 | Store + schema_widget | live | HIGH |
| second_attempt_delay_minutes | cf09f2c9 2026-05-06 | Store + schema_widget | live | HIGH |
| whatsapp_recovery_enabled | 7314ad55 2026-05-17 | Store + merchant_whatsapp_settings | live | HIGH |
| whatsapp_provider_mode | 7314ad55 | Store + merchant_whatsapp_settings | live | HIGH |
| whatsapp_mode | 455717c8 2026-06-07 | Store + merchant_whatsapp_mode_v1 | live | HIGH |
| whatsapp_template_overrides_json | 803d9f16 2026-06-07 | runtime helper (not Store class) | live | HIGH |
| whatsapp_onboarding_journey | 030ecc69 2026-06-08 | Store + onboarding journeys | live | HIGH |
| whatsapp_onboarding_journey_status | 3a1e7efc 2026-06-08 | Store + journey execution | live | HIGH |
| whatsapp_embedded_signup_status | 4c3c07db 2026-06-30 | runtime helper | live | HIGH |
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3altstorewa01"
down_revision: Union[str, Sequence[str], None] = "f2altacarts01a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("whatsapp_support_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("store_whatsapp_number", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("second_attempt_delay_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("whatsapp_recovery_enabled", sa.Boolean(), nullable=False),
    )
    op.add_column(
        "stores",
        sa.Column("whatsapp_provider_mode", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("whatsapp_mode", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("whatsapp_template_overrides_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("whatsapp_onboarding_journey", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column(
            "whatsapp_onboarding_journey_status", sa.String(length=32), nullable=True
        ),
    )
    op.add_column(
        "stores",
        sa.Column(
            "whatsapp_embedded_signup_status", sa.String(length=32), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column("stores", "whatsapp_embedded_signup_status")
    op.drop_column("stores", "whatsapp_onboarding_journey_status")
    op.drop_column("stores", "whatsapp_onboarding_journey")
    op.drop_column("stores", "whatsapp_template_overrides_json")
    op.drop_column("stores", "whatsapp_mode")
    op.drop_column("stores", "whatsapp_provider_mode")
    op.drop_column("stores", "whatsapp_recovery_enabled")
    op.drop_column("stores", "second_attempt_delay_minutes")
    op.drop_column("stores", "store_whatsapp_number")
    op.drop_column("stores", "whatsapp_support_url")
