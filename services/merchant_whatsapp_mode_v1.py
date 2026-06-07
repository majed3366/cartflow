# -*- coding: utf-8 -*-
"""WhatsApp mode architecture — merchant experience & settings (no send/runtime)."""
from __future__ import annotations

from typing import Any, Mapping, Optional

WHATSAPP_MODE_CARTFLOW_MANAGED = "cartflow_managed"
WHATSAPP_MODE_MERCHANT_WHATSAPP = "merchant_whatsapp"
WHATSAPP_MODE_FUTURE_PROVIDER = "future_provider"

CANONICAL_WHATSAPP_MODES: frozenset[str] = frozenset(
    {
        WHATSAPP_MODE_CARTFLOW_MANAGED,
        WHATSAPP_MODE_MERCHANT_WHATSAPP,
        WHATSAPP_MODE_FUTURE_PROVIDER,
    }
)

SELECTABLE_WHATSAPP_MODES: frozenset[str] = frozenset(
    {
        WHATSAPP_MODE_CARTFLOW_MANAGED,
        WHATSAPP_MODE_MERCHANT_WHATSAPP,
    }
)

DEFAULT_WHATSAPP_MODE = WHATSAPP_MODE_CARTFLOW_MANAGED

WHATSAPP_MODE_LABEL_AR: Mapping[str, str] = {
    WHATSAPP_MODE_CARTFLOW_MANAGED: "CartFlow Managed",
    WHATSAPP_MODE_MERCHANT_WHATSAPP: "Merchant WhatsApp",
    WHATSAPP_MODE_FUTURE_PROVIDER: "Future provider",
}

WHATSAPP_MODE_DESC_AR: Mapping[str, str] = {
    WHATSAPP_MODE_CARTFLOW_MANAGED: (
        "CartFlow يتولى الإرسال والمتابعة — وأنت تحدد متى وكيف يتم الاسترجاع."
    ),
    WHATSAPP_MODE_MERCHANT_WHATSAPP: (
        "رسائل العملاء من بنية واتساب تخص متجرك — للمتاجر المتقدمة."
    ),
    WHATSAPP_MODE_FUTURE_PROVIDER: "نماذج مزودين إضافية — محجوز للمستقبل.",
}

CONNECTION_STATUS_NOT_CONNECTED = "not_connected"
CONNECTION_STATUS_SETUP = "setup_in_progress"
CONNECTION_STATUS_CONNECTED = "connected"


def normalize_whatsapp_mode(raw: Any) -> str:
    key = (raw or "").strip().lower()
    if key in SELECTABLE_WHATSAPP_MODES:
        return key
    if key == WHATSAPP_MODE_FUTURE_PROVIDER:
        return WHATSAPP_MODE_FUTURE_PROVIDER
    return DEFAULT_WHATSAPP_MODE


def whatsapp_mode_label_ar(mode: str) -> str:
    return WHATSAPP_MODE_LABEL_AR.get(normalize_whatsapp_mode(mode), mode)


def whatsapp_mode_description_ar(mode: str) -> str:
    return WHATSAPP_MODE_DESC_AR.get(normalize_whatsapp_mode(mode), "")


def whatsapp_customer_connection_status(
    store: Optional[Any],
) -> tuple[str, str]:
    """Return (status_key, status_label_ar) for merchant-facing customers card."""
    if store is None:
        return CONNECTION_STATUS_NOT_CONNECTED, "غير متصل"
    enabled_raw = getattr(store, "whatsapp_recovery_enabled", None)
    recovery_on = True if enabled_raw is None else bool(enabled_raw)
    if not recovery_on:
        return CONNECTION_STATUS_NOT_CONNECTED, "غير متصل"

    from services.merchant_whatsapp_readiness_ui import (  # noqa: PLC0415
        build_merchant_whatsapp_readiness_card,
    )

    card = build_merchant_whatsapp_readiness_card(store)
    card_key = (card.get("key") or "").strip().lower()
    if card_key == "ready":
        return CONNECTION_STATUS_CONNECTED, "متصل"

    number = (getattr(store, "store_whatsapp_number", None) or "").strip()
    if card_key in ("sandbox", "setup", "test") or number:
        return CONNECTION_STATUS_SETUP, "قيد الإعداد"

    return CONNECTION_STATUS_NOT_CONNECTED, "غير متصل"


def vip_destination_display_for_store(store: Optional[Any]) -> dict[str, str]:
    if store is None:
        return {"vip_destination_ar": "—", "vip_destination_source": "—"}
    try:
        from services.vip_merchant_alert import resolve_vip_alert_destination  # noqa: PLC0415

        phone, src, _digits = resolve_vip_alert_destination(store)
    except Exception:  # noqa: BLE001
        return {"vip_destination_ar": "—", "vip_destination_source": "—"}
    if not phone:
        return {"vip_destination_ar": "—", "vip_destination_source": src or "—"}
    return {
        "vip_destination_ar": phone,
        "vip_destination_source": src or "—",
    }


def last_validation_display_for_store(store: Optional[Any]) -> dict[str, str]:
    from services.merchant_whatsapp_settings import (  # noqa: PLC0415
        last_send_status_for_store,
        whatsapp_status_display_ar,
    )

    last = last_send_status_for_store(store)
    return {
        "last_validation_ar": last.get("last_send_at_ar") or "—",
        "last_validation_status_ar": last.get("last_send_status_ar") or "—",
        "connection_status_summary_ar": whatsapp_status_display_ar(store),
    }


def merchant_whatsapp_mode_fields_for_api(store: Optional[Any]) -> dict[str, Any]:
    mode = normalize_whatsapp_mode(
        getattr(store, "whatsapp_mode", None) if store is not None else None
    )
    status_key, status_label = whatsapp_customer_connection_status(store)
    vip = vip_destination_display_for_store(store)
    validation = last_validation_display_for_store(store)
    return {
        "whatsapp_mode": mode,
        "whatsapp_mode_label_ar": whatsapp_mode_label_ar(mode),
        "whatsapp_mode_description_ar": whatsapp_mode_description_ar(mode),
        "whatsapp_mode_recommended": WHATSAPP_MODE_CARTFLOW_MANAGED,
        "whatsapp_customer_connection_status": status_key,
        "whatsapp_customer_connection_status_ar": status_label,
        "whatsapp_customers_title_ar": "رسائل العملاء عبر واتساب",
        "whatsapp_enable_recovery_cta_ar": "تفعيل استرجاع واتساب",
        "vip_destination_ar": vip["vip_destination_ar"],
        "vip_destination_source": vip["vip_destination_source"],
        "whatsapp_last_validation_ar": validation["last_validation_ar"],
        "whatsapp_last_validation_status_ar": validation["last_validation_status_ar"],
        "whatsapp_connection_summary_ar": validation["connection_status_summary_ar"],
        "whatsapp_mode_architecture_only_future": WHATSAPP_MODE_FUTURE_PROVIDER,
    }


def apply_whatsapp_mode_from_body(row: Any, body: Mapping[str, Any]) -> None:
    if "whatsapp_mode" not in body:
        return
    mode = normalize_whatsapp_mode(body.get("whatsapp_mode"))
    row.whatsapp_mode = mode


def ensure_store_whatsapp_mode_column(db: Any) -> None:
    """Idempotent DDL for stores.whatsapp_mode."""
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import SQLAlchemyError

    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        cols = {c["name"] for c in insp.get_columns("stores")}
        if "whatsapp_mode" in cols:
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        if dialect in ("postgresql", "postgres"):
            stmt = (
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS whatsapp_mode "
                "VARCHAR(32) DEFAULT 'cartflow_managed'"
            )
        else:
            stmt = (
                "ALTER TABLE stores ADD COLUMN whatsapp_mode "
                "VARCHAR(32) DEFAULT 'cartflow_managed'"
            )
        db.session.execute(text(stmt))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()


def reset_whatsapp_mode_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


_schema_once = False


def ensure_whatsapp_mode_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    ensure_store_whatsapp_mode_column(db)
    _schema_once = True
