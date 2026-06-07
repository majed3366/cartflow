# -*- coding: utf-8 -*-
"""Admin operational visibility for WhatsApp template registry — read-only."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from extensions import db
from models import MerchantUser, Store
from services.merchant_onboarding_store import merchant_store_display_name
from services.merchant_whatsapp_template_layer_v1 import (
    build_merchant_template_row,
    ensure_whatsapp_template_overrides_schema,
    parse_whatsapp_template_overrides_column,
)
from services.merchant_whatsapp_template_registry_v1 import (
    TEMPLATE_REGISTRY,
    TemplateRegistryEntry,
    list_registry_dicts,
    meta_status_label_ar,
)


@dataclass
class AdminTemplateRegistryRow:
    template_key: str
    reason_tag: Optional[str]
    display_name_ar: str
    template_type: str
    enabled: bool
    default_or_customized_ar: str
    future_meta_status: str
    future_meta_status_ar: str
    future_meta_template_name: str

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "template_key": self.template_key,
            "reason_tag": self.reason_tag,
            "display_name_ar": self.display_name_ar,
            "template_type": self.template_type,
            "enabled": self.enabled,
            "default_or_customized_ar": self.default_or_customized_ar,
            "future_meta_status": self.future_meta_status,
            "future_meta_status_ar": self.future_meta_status_ar,
            "future_meta_template_name": self.future_meta_template_name,
        }


@dataclass
class AdminStoreTemplateRow:
    store_id: int
    store_name: str
    store_slug: str
    merchant_email: str
    template_key: str
    reason_tag: Optional[str]
    enabled: bool
    default_or_customized_ar: str
    future_meta_status: str
    future_meta_status_ar: str

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "store_id": self.store_id,
            "store_name": self.store_name,
            "store_slug": self.store_slug,
            "merchant_email": self.merchant_email,
            "template_key": self.template_key,
            "reason_tag": self.reason_tag,
            "enabled": self.enabled,
            "default_or_customized_ar": self.default_or_customized_ar,
            "future_meta_status": self.future_meta_status,
            "future_meta_status_ar": self.future_meta_status_ar,
        }


def _registry_row(entry: TemplateRegistryEntry) -> AdminTemplateRegistryRow:
    return AdminTemplateRegistryRow(
        template_key=entry.template_key,
        reason_tag=entry.reason_tag,
        display_name_ar=entry.display_name_ar,
        template_type=entry.template_type,
        enabled=entry.enabled,
        default_or_customized_ar="افتراضي",
        future_meta_status=entry.future_meta_status,
        future_meta_status_ar=meta_status_label_ar(entry.future_meta_status),
        future_meta_template_name=entry.future_meta_template_name,
    )


def list_admin_template_registry_rows() -> list[AdminTemplateRegistryRow]:
    return [_registry_row(e) for e in TEMPLATE_REGISTRY.values()]


def list_admin_template_registry_api() -> list[dict[str, Any]]:
    return list_registry_dicts()


def _merchant_for_store(store: Store) -> Optional[MerchantUser]:
    mid = getattr(store, "merchant_user_id", None)
    if mid:
        row = db.session.get(MerchantUser, int(mid))
        if row is not None:
            return row
    return None


def build_admin_store_template_rows(store: Store) -> list[AdminStoreTemplateRow]:
    ensure_whatsapp_template_overrides_schema(db)
    merchant = _merchant_for_store(store)
    overrides = parse_whatsapp_template_overrides_column(
        getattr(store, "whatsapp_template_overrides_json", None)
    )
    store_name = merchant_store_display_name(store, merchant_user=merchant)
    slug = (getattr(store, "zid_store_id", None) or "").strip()
    email = (getattr(merchant, "email", None) or "").strip() if merchant else ""
    rows: list[AdminStoreTemplateRow] = []
    for entry in TEMPLATE_REGISTRY.values():
        if not entry.merchant_editable:
            continue
        merged = build_merchant_template_row(entry, overrides.get(entry.template_key))
        rows.append(
            AdminStoreTemplateRow(
                store_id=int(store.id),
                store_name=store_name,
                store_slug=slug,
                merchant_email=email,
                template_key=entry.template_key,
                reason_tag=entry.reason_tag,
                enabled=bool(merged.get("enabled")),
                default_or_customized_ar=str(
                    merged.get("customization_state_ar") or "افتراضي"
                ),
                future_meta_status=entry.future_meta_status,
                future_meta_status_ar=meta_status_label_ar(entry.future_meta_status),
            )
        )
    return rows


def list_admin_store_template_rows(
    *,
    query: Optional[str] = None,
    store_id: Optional[int] = None,
    limit: int = 50,
) -> list[AdminStoreTemplateRow]:
    ensure_whatsapp_template_overrides_schema(db)
    q = db.session.query(Store).order_by(Store.id.desc())
    if store_id is not None:
        q = q.filter(Store.id == int(store_id))
    needle = (query or "").strip().lower()
    if needle:
        like = f"%{needle}%"
        q = q.filter(Store.zid_store_id.ilike(like))
    stores = q.limit(max(1, min(int(limit), 200))).all()
    out: list[AdminStoreTemplateRow] = []
    for store in stores:
        out.extend(build_admin_store_template_rows(store))
    return out
