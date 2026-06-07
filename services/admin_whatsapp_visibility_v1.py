# -*- coding: utf-8 -*-
"""Admin operational visibility for merchant WhatsApp mode — read-only."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from extensions import db
from models import MerchantUser, Store
from services.merchant_onboarding_store import merchant_store_display_name
from services.merchant_whatsapp_mode_v1 import (
    ensure_whatsapp_mode_schema,
    merchant_whatsapp_mode_fields_for_api,
    whatsapp_mode_label_ar,
)
from services.merchant_whatsapp_settings import (
    ensure_store_whatsapp_merchant_settings_schema,
    inferred_whatsapp_provider_mode,
)


@dataclass
class AdminWhatsappStoreRow:
    store_id: int
    store_name: str
    store_slug: str
    merchant_email: str
    whatsapp_mode: str
    whatsapp_mode_label: str
    connection_status_ar: str
    connection_status_key: str
    vip_destination_ar: str
    last_validation_ar: str
    last_validation_status_ar: str
    provider_mode: str

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "store_id": self.store_id,
            "store_name": self.store_name,
            "store_slug": self.store_slug,
            "merchant_email": self.merchant_email,
            "whatsapp_mode": self.whatsapp_mode,
            "whatsapp_mode_label": self.whatsapp_mode_label,
            "connection_status_ar": self.connection_status_ar,
            "connection_status_key": self.connection_status_key,
            "vip_destination_ar": self.vip_destination_ar,
            "last_validation_ar": self.last_validation_ar,
            "last_validation_status_ar": self.last_validation_status_ar,
            "provider_mode": self.provider_mode,
        }


def _merchant_for_store(store: Store) -> Optional[MerchantUser]:
    mid = getattr(store, "merchant_user_id", None)
    if mid:
        row = db.session.get(MerchantUser, int(mid))
        if row is not None:
            return row
    return None


def build_admin_whatsapp_store_row(store: Store) -> AdminWhatsappStoreRow:
    ensure_store_whatsapp_merchant_settings_schema()
    ensure_whatsapp_mode_schema(db)
    merchant = _merchant_for_store(store)
    mode_fields = merchant_whatsapp_mode_fields_for_api(store)
    mode = mode_fields["whatsapp_mode"]
    return AdminWhatsappStoreRow(
        store_id=int(store.id),
        store_name=merchant_store_display_name(store, merchant_user=merchant),
        store_slug=(getattr(store, "zid_store_id", None) or "").strip(),
        merchant_email=(getattr(merchant, "email", None) or "").strip() if merchant else "",
        whatsapp_mode=mode,
        whatsapp_mode_label=whatsapp_mode_label_ar(mode),
        connection_status_ar=mode_fields["whatsapp_customer_connection_status_ar"],
        connection_status_key=mode_fields["whatsapp_customer_connection_status"],
        vip_destination_ar=mode_fields["vip_destination_ar"],
        last_validation_ar=mode_fields["whatsapp_last_validation_ar"],
        last_validation_status_ar=mode_fields["whatsapp_last_validation_status_ar"],
        provider_mode=inferred_whatsapp_provider_mode(store),
    )


def list_admin_whatsapp_store_rows(
    *,
    query: Optional[str] = None,
    limit: int = 50,
) -> list[AdminWhatsappStoreRow]:
    ensure_store_whatsapp_merchant_settings_schema()
    ensure_whatsapp_mode_schema(db)
    q = db.session.query(Store).order_by(Store.id.desc())
    needle = (query or "").strip().lower()
    if needle:
        like = f"%{needle}%"
        q = q.filter(Store.zid_store_id.ilike(like))
    rows = q.limit(max(1, min(int(limit), 200))).all()
    return [build_admin_whatsapp_store_row(s) for s in rows]
