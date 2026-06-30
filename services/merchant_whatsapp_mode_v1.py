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

MODE_SELECTION_TITLE_AR = "كيف تريد التواصل مع عملائك؟"

WHATSAPP_MODE_TITLE_AR: Mapping[str, str] = {
    WHATSAPP_MODE_CARTFLOW_MANAGED: "🟢 واتساب CartFlow",
    WHATSAPP_MODE_MERCHANT_WHATSAPP: "🔵 واتساب أعمال الخاص بي",
    WHATSAPP_MODE_FUTURE_PROVIDER: "Future provider",
}

WHATSAPP_MODE_LABEL_AR: Mapping[str, str] = {
    WHATSAPP_MODE_CARTFLOW_MANAGED: "واتساب CartFlow",
    WHATSAPP_MODE_MERCHANT_WHATSAPP: "واتساب أعمال الخاص بي",
    WHATSAPP_MODE_FUTURE_PROVIDER: "Future provider",
}

WHATSAPP_MODE_DESC_AR: Mapping[str, str] = {
    WHATSAPP_MODE_CARTFLOW_MANAGED: (
        "CartFlow يتولى الإرسال — الأسرع للبدء ولا يتطلب إعداد Meta."
    ),
    WHATSAPP_MODE_MERCHANT_WHATSAPP: (
        "استخدم رقمك التجاري — يتطلب ربط منصة الأعمال."
    ),
    WHATSAPP_MODE_FUTURE_PROVIDER: "نماذج مزودين إضافية — محجوز للمستقبل.",
}

WHATSAPP_MODE_BULLETS_AR: Mapping[str, tuple[str, ...]] = {
    WHATSAPP_MODE_CARTFLOW_MANAGED: (
        "الأسرع للبدء.",
        "لا يتطلب إعداد Meta.",
        "CartFlow يتولى الإرسال.",
        "مناسب لمعظم المتاجر.",
    ),
    WHATSAPP_MODE_MERCHANT_WHATSAPP: (
        "استخدم رقمك التجاري.",
        "يتطلب ربط منصة الأعمال.",
        "الربط المباشر عبر Meta سيصبح متاحاً لاحقاً.",
    ),
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


def whatsapp_mode_title_ar(mode: str) -> str:
    return WHATSAPP_MODE_TITLE_AR.get(normalize_whatsapp_mode(mode), mode)


def whatsapp_mode_bullets_ar(mode: str) -> list[str]:
    return list(WHATSAPP_MODE_BULLETS_AR.get(normalize_whatsapp_mode(mode), ()))


def _merchant_owned_panel_for_api(store: Optional[Any]) -> dict[str, Any]:
    """Path B status: Meta pairing + Embedded Signup + connect page (read-only)."""
    from services.merchant_whatsapp_connection_readiness_v1 import (  # noqa: PLC0415
        connection_readiness_for_merchant_api,
    )
    from services.merchant_whatsapp_embedded_signup_readiness_v1 import (  # noqa: PLC0415
        embedded_signup_fields_for_api,
    )

    cr = connection_readiness_for_merchant_api(store)
    prod = cr.get("production_sending_readiness") or {}
    embedded = embedded_signup_fields_for_api(store).get("whatsapp_embedded_signup") or {}
    meta_status_ar = prod.get("status_ar") or "—"
    meta_instruction = prod.get("meta_pairing_instruction_ar") or ""
    pending = prod.get("pending_reason") or ""
    return {
        "visible": True,
        "meta_pairing_status_ar": meta_status_ar,
        "meta_pairing_instruction_ar": meta_instruction,
        "meta_pairing_pending_reason": pending,
        "embedded_signup_status_ar": embedded.get("status_ar") or "—",
        "embedded_signup_next_action_ar": embedded.get("next_action_ar") or "",
        "embedded_signup_launch_ready": bool(embedded.get("launch_ready")),
        "connect_page_href": embedded.get("connect_href") or "/dashboard#whatsapp-connect",
        "connect_page_label_ar": "صفحة ربط واتساب (Embedded Signup)",
        "connect_page_note_ar": "الربط المباشر عبر Meta سيصبح متاحاً لاحقاً.",
    }


def whatsapp_mode_selection_for_api(store: Optional[Any]) -> dict[str, Any]:
    mode = normalize_whatsapp_mode(
        getattr(store, "whatsapp_mode", None) if store is not None else None
    )
    options: list[dict[str, Any]] = []
    for key in (WHATSAPP_MODE_CARTFLOW_MANAGED, WHATSAPP_MODE_MERCHANT_WHATSAPP):
        options.append(
            {
                "key": key,
                "title_ar": whatsapp_mode_title_ar(key),
                "label_ar": whatsapp_mode_label_ar(key),
                "description_ar": whatsapp_mode_description_ar(key),
                "bullets_ar": whatsapp_mode_bullets_ar(key),
                "recommended": key == WHATSAPP_MODE_CARTFLOW_MANAGED,
                "selected": key == mode,
            }
        )
    payload: dict[str, Any] = {
        "whatsapp_mode_selection": {
            "title_ar": MODE_SELECTION_TITLE_AR,
            "selected": mode,
            "default_mode": DEFAULT_WHATSAPP_MODE,
            "options": options,
        }
    }
    if mode == WHATSAPP_MODE_MERCHANT_WHATSAPP:
        payload["whatsapp_mode_merchant_panel"] = _merchant_owned_panel_for_api(store)
    else:
        payload["whatsapp_mode_merchant_panel"] = {"visible": False}
    return payload


def whatsapp_customer_connection_status(
    store: Optional[Any],
) -> tuple[str, str]:
    """Return (legacy_pill_key, status_label_ar) for merchant-facing customers card."""
    from services.merchant_whatsapp_connection_readiness_v1 import (  # noqa: PLC0415
        CONNECTION_STATE_LABEL_AR,
        CONNECTION_STATE_NOT_CONNECTED,
        evaluate_whatsapp_connection_readiness,
    )

    ev = evaluate_whatsapp_connection_readiness(store)
    legacy = ev.get("connection_state_legacy_pill_key") or CONNECTION_STATUS_NOT_CONNECTED
    label = ev.get("connection_state_ar") or CONNECTION_STATE_LABEL_AR.get(
        ev.get("connection_state") or CONNECTION_STATE_NOT_CONNECTED, "غير متصل"
    )
    return legacy, label


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
    from services.merchant_whatsapp_connection_readiness_v1 import (  # noqa: PLC0415
        connection_readiness_for_merchant_api,
    )

    readiness = connection_readiness_for_merchant_api(store)
    payload = {
        "whatsapp_mode": mode,
        "whatsapp_mode_label_ar": whatsapp_mode_label_ar(mode),
        "whatsapp_mode_title_ar": whatsapp_mode_title_ar(mode),
        "whatsapp_mode_description_ar": whatsapp_mode_description_ar(mode),
        "whatsapp_mode_bullets_ar": whatsapp_mode_bullets_ar(mode),
        "whatsapp_mode_recommended": WHATSAPP_MODE_CARTFLOW_MANAGED,
        "whatsapp_customer_connection_status": status_key,
        "whatsapp_customer_connection_status_ar": status_label,
        "whatsapp_connection_state": readiness.get("connection_state"),
        "whatsapp_connection_state_ar": readiness.get("connection_state_ar"),
        "whatsapp_readiness_overall": readiness.get("readiness_overall"),
        "whatsapp_readiness_overall_ar": readiness.get("readiness_overall_ar"),
        "whatsapp_connection_readiness": readiness,
        "whatsapp_customers_title_ar": "رسائل العملاء عبر واتساب",
        "whatsapp_enable_recovery_cta_ar": "تفعيل استرجاع واتساب",
        "vip_destination_ar": vip["vip_destination_ar"],
        "vip_destination_source": vip["vip_destination_source"],
        "whatsapp_last_validation_ar": validation["last_validation_ar"],
        "whatsapp_last_validation_status_ar": validation["last_validation_status_ar"],
        "whatsapp_connection_summary_ar": validation["connection_status_summary_ar"],
        "whatsapp_mode_architecture_only_future": WHATSAPP_MODE_FUTURE_PROVIDER,
    }
    payload.update(whatsapp_mode_selection_for_api(store))
    return payload


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
