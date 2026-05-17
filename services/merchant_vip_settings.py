# -*- coding: utf-8 -*-
"""Merchant dashboard VIP preferences — persist/display only (no runtime lane changes)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import inspect, or_, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryLog, Store
from services.merchant_dashboard_reference_ui import merchant_relative_time_arabic
from services.vip_cart import (
    abandoned_cart_in_vip_operational_lane,
    merchant_vip_threshold_int,
    vip_cart_threshold_fields_for_api,
)

DEFAULT_VIP_THRESHOLD = 500
_VIP_ALERT_LOG_STATUSES = ("vip_manual_handling",)
_VIP_PATCH_KEYS = frozenset(
    {
        "vip_enabled",
        "vip_cart_threshold",
        "vip_notify_enabled",
        "vip_note",
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


def _ensure_store_merchant_vip_settings_columns() -> None:
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
            ("vip_enabled", "INTEGER DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
            ("vip_notify_enabled", "INTEGER DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
            ("vip_note", "TEXT", "TEXT"),
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


def ensure_store_merchant_vip_settings_schema() -> None:
    _ensure_store_merchant_vip_settings_columns()


def merchant_vip_enabled(store: Optional[Any]) -> bool:
    if store is None:
        return True
    raw = getattr(store, "vip_enabled", None)
    if raw is None:
        return True
    return bool(raw)


def merchant_vip_notify_enabled(store: Optional[Any]) -> bool:
    if store is None:
        return True
    raw = getattr(store, "vip_notify_enabled", None)
    if raw is None:
        return True
    return bool(raw)


def vip_threshold_display_ar(store: Optional[Any]) -> str:
    th = merchant_vip_threshold_int(store)
    if th is not None:
        return f"{int(th):,} ريال"
    return "غير محددة"


def vip_status_display_ar(store: Optional[Any]) -> str:
    return "مفعّل" if merchant_vip_enabled(store) else "غير مفعّل"


def _abandoned_carts_for_store_query(store: Any):
    store_id = getattr(store, "id", None)
    if store_id is None:
        return None
    try:
        vid = int(store_id)
    except (TypeError, ValueError):
        return None
    return db.session.query(AbandonedCart).filter(
        or_(
            AbandonedCart.store_id == vid,
            AbandonedCart.store_id.is_(None),  # type: ignore[union-attr]
        )
    )


def last_vip_cart_display_for_store(store: Optional[Any]) -> Dict[str, str]:
    out = {"last_vip_cart_ar": "—", "last_vip_cart_at_ar": "—"}
    if store is None:
        return out
    q = _abandoned_carts_for_store_query(store)
    if q is None:
        return out
    th = merchant_vip_threshold_int(store)
    try:
        ordered = q.order_by(
            AbandonedCart.last_seen_at.desc(),
            AbandonedCart.first_seen_at.desc(),
            AbandonedCart.id.desc(),
        )
        if th is not None:
            ac = ordered.filter(AbandonedCart.cart_value >= float(th)).first()
        else:
            ac = None
            for row in ordered.limit(80).all():
                if abandoned_cart_in_vip_operational_lane(row, store) or bool(
                    getattr(row, "vip_mode", False)
                ):
                    ac = row
                    break
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return out
    if ac is None:
        return out
    try:
        val = float(getattr(ac, "cart_value", None) or 0)
    except (TypeError, ValueError):
        val = 0.0
    out["last_vip_cart_ar"] = f"{val:,.0f} ريال"
    ts = getattr(ac, "last_seen_at", None) or getattr(ac, "first_seen_at", None)
    if ts is not None:
        out["last_vip_cart_at_ar"] = merchant_relative_time_arabic(
            ts, now_utc=datetime.now(timezone.utc)
        )
    return out


def last_vip_alert_display_for_store(store: Optional[Any]) -> Dict[str, str]:
    out = {"last_vip_alert_ar": "—", "last_vip_alert_at_ar": "—"}
    if store is None:
        return out
    slug = (getattr(store, "zid_store_id", None) or "").strip()[:255]
    if not slug:
        return out
    try:
        lg = (
            db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.store_slug == slug,
                CartRecoveryLog.status.in_(tuple(_VIP_ALERT_LOG_STATUSES)),
            )
            .order_by(
                CartRecoveryLog.sent_at.desc(),
                CartRecoveryLog.created_at.desc(),
                CartRecoveryLog.id.desc(),
            )
            .first()
        )
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return out
    if lg is None:
        return out
    out["last_vip_alert_ar"] = "تنبيه سلة مهمة"
    ts = getattr(lg, "sent_at", None) or getattr(lg, "created_at", None)
    if ts is not None:
        out["last_vip_alert_at_ar"] = merchant_relative_time_arabic(
            ts, now_utc=datetime.now(timezone.utc)
        )
    return out


def _vip_note_for_api(store: Optional[Any]) -> Optional[str]:
    if store is None:
        return None
    raw = getattr(store, "vip_note", None)
    if not isinstance(raw, str):
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    return trimmed[:2000]


def is_merchant_vip_only_patch(body: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(body, dict) or not body:
        return False
    keys = {k for k in body if not str(k).startswith("_")}
    if not keys:
        return False
    return keys <= _VIP_PATCH_KEYS and bool(keys & {"vip_cart_threshold", "vip_note", "vip_enabled", "vip_notify_enabled"})


def merchant_vip_settings_fields_for_api(
    store: Optional[Any], *, include_activity: bool = True
) -> Dict[str, Any]:
    ensure_store_merchant_vip_settings_schema()
    out: Dict[str, Any] = {
        "vip_enabled": merchant_vip_enabled(store),
        "vip_notify_enabled": merchant_vip_notify_enabled(store),
        "vip_note": _vip_note_for_api(store),
        "vip_status_display_ar": vip_status_display_ar(store),
        "vip_threshold_display_ar": vip_threshold_display_ar(store),
    }
    out.update(vip_cart_threshold_fields_for_api(store))
    if include_activity:
        last_cart = last_vip_cart_display_for_store(store)
        last_alert = last_vip_alert_display_for_store(store)
        out["last_vip_cart_ar"] = last_cart.get("last_vip_cart_ar") or "—"
        out["last_vip_cart_at_ar"] = last_cart.get("last_vip_cart_at_ar") or "—"
        out["last_vip_alert_ar"] = last_alert.get("last_vip_alert_ar") or "—"
        out["last_vip_alert_at_ar"] = last_alert.get("last_vip_alert_at_ar") or "—"
    return out


def merchant_vip_settings_patch_response(store: Optional[Any]) -> Dict[str, Any]:
    """Small POST response for VIP-only saves (faster than full recovery-settings payload)."""
    payload: Dict[str, Any] = {"ok": True}
    payload.update(merchant_vip_settings_fields_for_api(store, include_activity=False))
    return payload


def apply_merchant_vip_settings_from_body(row: Store, body: Dict[str, Any]) -> None:
    ensure_store_merchant_vip_settings_schema()
    if "vip_enabled" in body:
        row.vip_enabled = _bool_from_body(body.get("vip_enabled"), default=True)
    if "vip_notify_enabled" in body:
        row.vip_notify_enabled = _bool_from_body(
            body.get("vip_notify_enabled"), default=True
        )
    if "vip_note" in body:
        raw = body.get("vip_note")
        if raw is None:
            row.vip_note = None
        elif isinstance(raw, str) and not raw.strip():
            row.vip_note = None
        else:
            row.vip_note = str(raw).strip()[:2000]
