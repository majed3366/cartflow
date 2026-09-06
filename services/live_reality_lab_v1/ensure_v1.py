# -*- coding: utf-8 -*-
"""Ensure Live Reality Lab Store + MerchantUser (idempotent)."""
from __future__ import annotations

from typing import Any

from extensions import db
from models import MerchantUser, Store
from services.live_reality_lab_v1.contract_v1 import (
    LAB_BOOTSTRAP_PASSWORD,
    LAB_DISPLAY_NAME,
    LAB_EMAIL,
    LAB_INTEGRATION_SOURCE,
    LAB_STORE_SLUG,
)
from services.merchant_auth_v1 import hash_password


def ensure_live_reality_lab_tenant_v1(
    *,
    password: str | None = None,
) -> dict[str, Any]:
    email = LAB_EMAIL.strip().lower()
    zid = LAB_STORE_SLUG
    pwd = password or LAB_BOOTSTRAP_PASSWORD

    user = db.session.query(MerchantUser).filter(MerchantUser.email == email).first()
    if user is None:
        user = MerchantUser(
            email=email,
            password_hash=hash_password(pwd),
            merchant_name=LAB_DISPLAY_NAME[:255],
        )
        db.session.add(user)
        db.session.flush()
    else:
        user.password_hash = hash_password(pwd)
        user.merchant_name = LAB_DISPLAY_NAME[:255]

    store = db.session.query(Store).filter(Store.zid_store_id == zid).first()
    if store is None:
        store = Store(
            zid_store_id=zid,
            merchant_user_id=int(user.id),
            widget_display_name=LAB_DISPLAY_NAME[:255],
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            is_active=True,
            integration_source=LAB_INTEGRATION_SOURCE,
            whatsapp_recovery_enabled=False,
        )
        db.session.add(store)
        db.session.flush()
    else:
        store.merchant_user_id = int(user.id)
        store.widget_display_name = LAB_DISPLAY_NAME[:255]
        store.integration_source = LAB_INTEGRATION_SOURCE
        store.is_active = True
        store.whatsapp_recovery_enabled = False
        db.session.flush()

    user.primary_store_id = int(store.id)
    db.session.commit()
    return {
        "ok": True,
        "store_slug": zid,
        "email": email,
        "integration_source": LAB_INTEGRATION_SOURCE,
        "store_id": int(store.id),
        "merchant_user_id": int(user.id),
        "whatsapp_recovery_enabled": False,
    }


__all__ = ["ensure_live_reality_lab_tenant_v1"]
