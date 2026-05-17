# -*- coding: utf-8 -*-
"""Merchant dashboard general operational preferences — persist/display only."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from models import Store
from services.merchant_dashboard_reference_ui import merchant_relative_time_arabic

_VALID_AUTOMATION_MODES = frozenset({"manual", "assistant", "auto"})
_AUTOMATION_MODE_AR = {
    "manual": "يدوي",
    "assistant": "مساعد",
    "auto": "تلقائي",
}
_GENERAL_PATCH_KEYS = frozenset(
    {
        "settings_notify_vip",
        "settings_notify_recovery_success",
        "settings_notify_whatsapp_failure",
        "widget_enabled",
        "widget_display_name",
        "merchant_automation_mode",
        "merchant_settings_scope",
    }
)

_schema_ensured = False


def _bool_from_body(raw: Any, *, default: bool) -> bool:
    if raw is None:
        return default
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return bool(raw)


def _bool_from_store(raw: Any, *, default: bool) -> bool:
    if raw is None:
        return default
    return bool(raw)


def _ensure_store_merchant_general_settings_columns() -> None:
    global _schema_ensured
    if _schema_ensured:
        return
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        specs = (
            ("settings_notify_vip", "INTEGER DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
            (
                "settings_notify_recovery_success",
                "INTEGER DEFAULT 1",
                "BOOLEAN NOT NULL DEFAULT TRUE",
            ),
            (
                "settings_notify_whatsapp_failure",
                "INTEGER DEFAULT 1",
                "BOOLEAN NOT NULL DEFAULT TRUE",
            ),
            ("widget_enabled", "INTEGER DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
            ("widget_display_name", "VARCHAR(255)", "VARCHAR(255)"),
            (
                "merchant_automation_mode",
                "VARCHAR(32) DEFAULT 'manual'",
                "VARCHAR(32) DEFAULT 'manual'",
            ),
        )
        for name, sqlite_sql, pg_sql in specs:
            existing = {c["name"] for c in insp.get_columns("stores")}
            if name in existing:
                continue
            if dialect in ("postgresql", "postgres"):
                stmt = f"ALTER TABLE stores ADD COLUMN IF NOT EXISTS {name} {pg_sql}"
            else:
                stmt = f"ALTER TABLE stores ADD COLUMN {name} {sqlite_sql}"
            try:
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
        _schema_ensured = True
    except (OSError, SQLAlchemyError):
        db.session.rollback()


def ensure_store_merchant_general_settings_schema() -> None:
    _ensure_store_merchant_general_settings_columns()


def normalize_automation_mode(raw: Any) -> str:
    if raw is None:
        return "manual"
    v = str(raw).strip().lower()
    if v in ("يدوي", "manual"):
        return "manual"
    if v in ("مساعد", "assistant", "assist"):
        return "assistant"
    if v in ("تلقائي", "auto", "automatic"):
        return "auto"
    return "manual"


def merchant_automation_mode(store: Optional[Any]) -> str:
    if store is None:
        return "manual"
    return normalize_automation_mode(getattr(store, "merchant_automation_mode", None))


def automation_mode_label_ar(mode: str) -> str:
    return _AUTOMATION_MODE_AR.get(normalize_automation_mode(mode), "يدوي")


def notifications_summary_ar(store: Optional[Any]) -> str:
    if store is None:
        return "—"
    parts: list[str] = []
    if _bool_from_store(getattr(store, "settings_notify_vip", None), default=True):
        parts.append("تنبيه VIP")
    if _bool_from_store(
        getattr(store, "settings_notify_recovery_success", None), default=True
    ):
        parts.append("إيراد مسترجع")
    if _bool_from_store(
        getattr(store, "settings_notify_whatsapp_failure", None), default=True
    ):
        parts.append("انقطاع واتساب")
    return "، ".join(parts) if parts else "لا إشعارات مفعّلة"


def widget_display_name_for_api(store: Optional[Any]) -> Optional[str]:
    if store is None:
        return None
    raw = getattr(store, "widget_display_name", None)
    if not isinstance(raw, str):
        return None
    trimmed = raw.strip()[:255]
    return trimmed or None


def settings_updated_at_ar(store: Optional[Any]) -> str:
    if store is None:
        return "—"
    ts = getattr(store, "updated_at", None) or getattr(store, "created_at", None)
    if ts is None:
        return "—"
    return merchant_relative_time_arabic(ts, now_utc=datetime.now(timezone.utc))


def merchant_general_settings_fields_for_api(store: Optional[Any]) -> Dict[str, Any]:
    ensure_store_merchant_general_settings_schema()
    mode = merchant_automation_mode(store)
    wname = widget_display_name_for_api(store)
    return {
        "settings_notify_vip": _bool_from_store(
            getattr(store, "settings_notify_vip", None), default=True
        ),
        "settings_notify_recovery_success": _bool_from_store(
            getattr(store, "settings_notify_recovery_success", None), default=True
        ),
        "settings_notify_whatsapp_failure": _bool_from_store(
            getattr(store, "settings_notify_whatsapp_failure", None), default=True
        ),
        "widget_enabled": _bool_from_store(
            getattr(store, "widget_enabled", None), default=True
        ),
        "widget_display_name": wname,
        "merchant_automation_mode": mode,
        "merchant_automation_mode_ar": automation_mode_label_ar(mode),
        "settings_notifications_summary_ar": notifications_summary_ar(store),
        "settings_widget_name_display_ar": wname or "—",
        "settings_updated_at_ar": settings_updated_at_ar(store),
    }


def is_merchant_general_settings_only_patch(body: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(body, dict) or not body:
        return False
    keys = {k for k in body if not str(k).startswith("_")}
    if not keys:
        return False
    if not keys <= _GENERAL_PATCH_KEYS:
        return False
    return bool(
        keys
        & {
            "settings_notify_vip",
            "settings_notify_recovery_success",
            "settings_notify_whatsapp_failure",
            "widget_enabled",
            "widget_display_name",
            "merchant_automation_mode",
        }
    )


def merchant_general_settings_patch_response(store: Optional[Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"ok": True}
    payload.update(merchant_general_settings_fields_for_api(store))
    return payload


def apply_merchant_general_settings_from_body(row: Store, body: Dict[str, Any]) -> None:
    ensure_store_merchant_general_settings_schema()
    if "settings_notify_vip" in body:
        row.settings_notify_vip = _bool_from_body(
            body.get("settings_notify_vip"), default=True
        )
    if "settings_notify_recovery_success" in body:
        row.settings_notify_recovery_success = _bool_from_body(
            body.get("settings_notify_recovery_success"), default=True
        )
    if "settings_notify_whatsapp_failure" in body:
        row.settings_notify_whatsapp_failure = _bool_from_body(
            body.get("settings_notify_whatsapp_failure"), default=True
        )
    if "widget_enabled" in body:
        row.widget_enabled = _bool_from_body(body.get("widget_enabled"), default=True)
    if "widget_display_name" in body:
        raw = body.get("widget_display_name")
        if raw is None:
            row.widget_display_name = None
        elif isinstance(raw, str) and not raw.strip():
            row.widget_display_name = None
        else:
            row.widget_display_name = str(raw).strip()[:255]
    if "merchant_automation_mode" in body:
        row.merchant_automation_mode = normalize_automation_mode(
            body.get("merchant_automation_mode")
        )
