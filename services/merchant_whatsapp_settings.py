# -*- coding: utf-8 -*-
"""Merchant dashboard WhatsApp settings — read/save on Store (no send runtime)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from models import CartRecoveryLog, Store
from services.merchant_whatsapp_readiness_ui import build_merchant_whatsapp_readiness_card

_VALID_PROVIDER_MODES = frozenset({"sandbox", "test", "production"})

_LOG_STATUS_AR = {
    "sent_real": "تم الإرسال",
    "mock_sent": "تم الإرسال (وضع تجريبي)",
    "whatsapp_failed": "فشل الإرسال",
    "skipped": "تم التخطي",
    "blocked": "محظور",
}

_schema_ensured = False


def normalize_whatsapp_provider_mode(raw: Any) -> Optional[str]:
    if raw is None or raw == "":
        return None
    v = str(raw).strip().lower()
    return v if v in _VALID_PROVIDER_MODES else None


def _ensure_store_whatsapp_merchant_settings_columns() -> None:
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
            ("whatsapp_recovery_enabled", "INTEGER DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
            ("whatsapp_provider_mode", "VARCHAR(32)", "VARCHAR(32)"),
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


def ensure_store_whatsapp_merchant_settings_schema() -> None:
    """Idempotent columns for merchant WhatsApp settings."""
    _ensure_store_whatsapp_merchant_settings_columns()


def inferred_whatsapp_provider_mode(store: Optional[Any]) -> str:
    if store is None:
        return "sandbox"
    stored = normalize_whatsapp_provider_mode(getattr(store, "whatsapp_provider_mode", None))
    if stored is not None:
        return stored
    try:
        from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

        ob = evaluate_onboarding_readiness(store)
        flags = dict(ob.get("flags") or {})
        if flags.get("sandbox_mode_active"):
            return "sandbox"
        if flags.get("provider_ready"):
            return "production"
        return "test"
    except Exception:  # noqa: BLE001
        return "sandbox"


def provider_mode_label_ar(mode: str) -> str:
    m = (mode or "").strip().lower()
    if m == "production":
        return "إنتاج"
    if m == "test":
        return "اختبار"
    return "تجريبي"


def provider_mode_hint_ar(store: Optional[Any], mode: Optional[str] = None) -> str:
    m = (mode or inferred_whatsapp_provider_mode(store)).strip().lower()
    if m == "sandbox":
        return "وضع تجربة — مناسب للاختبار وليس للإنتاج"
    if m == "production":
        try:
            from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

            ob = evaluate_onboarding_readiness(store)
            flags = dict(ob.get("flags") or {})
            if not flags.get("provider_ready"):
                return "الإنتاج غير مفعّل بعد"
        except Exception:  # noqa: BLE001
            return "الإنتاج غير مفعّل بعد"
        return "وضع الإنتاج"
    if m == "test":
        return "وضع اختبار"
    return ""


def whatsapp_status_display_ar(store: Optional[Any]) -> str:
    card = build_merchant_whatsapp_readiness_card(store)
    badge = (card.get("badge") or "").strip()
    title = (card.get("title") or "").strip()
    if badge and title:
        return f"{badge} — {title}"
    return badge or title or "—"


def last_send_status_for_store(store: Optional[Any]) -> Dict[str, str]:
    out = {"last_send_status_ar": "—", "last_send_at_ar": "—"}
    if store is None:
        return out
    slug = (getattr(store, "zid_store_id", None) or "").strip()[:255]
    if not slug:
        return out
    try:
        lg = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.store_slug == slug)
            .order_by(
                CartRecoveryLog.sent_at.desc().nullslast(),
                CartRecoveryLog.created_at.desc(),
            )
            .first()
        )
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return out
    if lg is None:
        return out
    st = (getattr(lg, "status", None) or "").strip().lower()
    out["last_send_status_ar"] = _LOG_STATUS_AR.get(st, st or "—")
    ts = getattr(lg, "sent_at", None) or getattr(lg, "created_at", None)
    if ts is not None:
        try:
            from services.merchant_dashboard_reference_ui import (
                merchant_relative_time_arabic,
            )

            out["last_send_at_ar"] = merchant_relative_time_arabic(
                ts, now_utc=datetime.now(timezone.utc)
            )
        except Exception:  # noqa: BLE001
            out["last_send_at_ar"] = str(ts)
    return out


def merchant_whatsapp_settings_fields_for_api(store: Optional[Any]) -> Dict[str, Any]:
    ensure_store_whatsapp_merchant_settings_schema()
    enabled_raw = getattr(store, "whatsapp_recovery_enabled", None) if store else None
    if enabled_raw is None:
        recovery_on = True
    else:
        recovery_on = bool(enabled_raw)
    mode = inferred_whatsapp_provider_mode(store)
    last = last_send_status_for_store(store)
    return {
        "whatsapp_recovery_enabled": recovery_on,
        "whatsapp_provider_mode": mode,
        "whatsapp_provider_mode_label_ar": provider_mode_label_ar(mode),
        "whatsapp_provider_mode_hint_ar": provider_mode_hint_ar(store, mode),
        "whatsapp_status_display": whatsapp_status_display_ar(store),
        "last_send_status_ar": last.get("last_send_status_ar") or "—",
        "last_send_at_ar": last.get("last_send_at_ar") or "—",
    }


def apply_merchant_whatsapp_settings_from_body(
    row: Store, body: Dict[str, Any]
) -> None:
    ensure_store_whatsapp_merchant_settings_schema()
    if "whatsapp_recovery_enabled" in body:
        raw = body.get("whatsapp_recovery_enabled")
        if isinstance(raw, str):
            row.whatsapp_recovery_enabled = raw.strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
        else:
            row.whatsapp_recovery_enabled = bool(raw)
    if "whatsapp_provider_mode" in body:
        row.whatsapp_provider_mode = normalize_whatsapp_provider_mode(
            body.get("whatsapp_provider_mode")
        )
