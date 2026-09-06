# -*- coding: utf-8 -*-
"""
Ensure production founder evaluation tenant Store + MerchantUser exist.

Idempotent. Does not touch demo / real merchants.
Does not enable WhatsApp. No Scheduler. No deploy hook — call explicitly.
"""
from __future__ import annotations

from typing import Any

from extensions import db
from models import MerchantUser, Store
from services.founder_production_evaluation_tenant_v1.contract_v1 import (
    FOUNDER_EVAL_DISPLAY_NAME,
    FOUNDER_EVAL_EMAIL,
    FOUNDER_EVAL_INTEGRATION_SOURCE,
    FOUNDER_EVAL_STORE_SLUG,
)
from services.merchant_auth_v1 import hash_password


# Local/bootstrap only — rotate in production ops before use.
FOUNDER_EVAL_BOOTSTRAP_PASSWORD = "FounderEval-Prod-Tenant-V1!"


def ensure_founder_production_evaluation_tenant_v1(
    *,
    password: str | None = None,
) -> dict[str, Any]:
    """
    Create or refresh the production founder evaluation merchant/store.

    Returns identity proof for ops / REPORT. Never creates secondary stores.
    """
    email = FOUNDER_EVAL_EMAIL.strip().lower()
    zid = FOUNDER_EVAL_STORE_SLUG
    pwd = password or FOUNDER_EVAL_BOOTSTRAP_PASSWORD

    user = db.session.query(MerchantUser).filter(MerchantUser.email == email).first()
    if user is None:
        user = MerchantUser(
            email=email,
            password_hash=hash_password(pwd),
            merchant_name=FOUNDER_EVAL_DISPLAY_NAME[:255],
        )
        db.session.add(user)
        db.session.flush()
    else:
        user.password_hash = hash_password(pwd)
        user.merchant_name = FOUNDER_EVAL_DISPLAY_NAME[:255]

    store = db.session.query(Store).filter(Store.zid_store_id == zid).first()
    if store is None:
        store = Store(
            zid_store_id=zid,
            merchant_user_id=int(user.id),
            widget_display_name=FOUNDER_EVAL_DISPLAY_NAME[:255],
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            is_active=True,
            integration_source=FOUNDER_EVAL_INTEGRATION_SOURCE,
            whatsapp_recovery_enabled=False,
        )
        db.session.add(store)
        db.session.flush()
    else:
        store.merchant_user_id = int(user.id)
        store.widget_display_name = FOUNDER_EVAL_DISPLAY_NAME[:255]
        store.integration_source = FOUNDER_EVAL_INTEGRATION_SOURCE
        store.is_active = True
        store.whatsapp_recovery_enabled = False
        db.session.flush()

    user.primary_store_id = int(store.id)
    db.session.commit()
    return {
        "ok": True,
        "store_slug": zid,
        "email": email,
        "merchant_user_id": int(user.id),
        "store_id": int(store.id),
        "integration_source": FOUNDER_EVAL_INTEGRATION_SOURCE,
        "whatsapp_recovery_enabled": False,
        "external_side_effects": "blocked_by_default",
    }


__all__ = [
    "FOUNDER_EVAL_BOOTSTRAP_PASSWORD",
    "ensure_founder_production_evaluation_tenant_v1",
]
