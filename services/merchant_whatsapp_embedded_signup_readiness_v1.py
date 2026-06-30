# -*- coding: utf-8 -*-
"""
WhatsApp Embedded Signup Foundation V1 — readiness states (architecture only).

Evaluates merchant-owned WhatsApp onboarding state for Path B (merchant_whatsapp).
Does not launch Embedded Signup, exchange tokens, or change send/recovery paths.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Optional

from services.merchant_whatsapp_mode_v1 import (
    WHATSAPP_MODE_MERCHANT_WHATSAPP,
    normalize_whatsapp_mode,
)

# ── Canonical Embedded Signup readiness states (V1) ─────────────────────────

EMBEDDED_SIGNUP_NOT_STARTED = "not_started"
EMBEDDED_SIGNUP_PAIRING_REQUIRED = "pairing_required"
EMBEDDED_SIGNUP_CONNECTED = "connected"
EMBEDDED_SIGNUP_FAILED = "failed"

CANONICAL_EMBEDDED_SIGNUP_STATES: frozenset[str] = frozenset(
    {
        EMBEDDED_SIGNUP_NOT_STARTED,
        EMBEDDED_SIGNUP_PAIRING_REQUIRED,
        EMBEDDED_SIGNUP_CONNECTED,
        EMBEDDED_SIGNUP_FAILED,
    }
)

EMBEDDED_SIGNUP_STATE_LABEL_AR: Mapping[str, str] = {
    EMBEDDED_SIGNUP_NOT_STARTED: "لم يبدأ الربط",
    EMBEDDED_SIGNUP_PAIRING_REQUIRED: "يلزم إكمال الربط",
    EMBEDDED_SIGNUP_CONNECTED: "متصل",
    EMBEDDED_SIGNUP_FAILED: "فشل الربط",
}

EMBEDDED_SIGNUP_STATE_NEXT_ACTION_AR: Mapping[str, str] = {
    EMBEDDED_SIGNUP_NOT_STARTED: "ابدأ ربط واتساب أعمال بنقرة واحدة.",
    EMBEDDED_SIGNUP_PAIRING_REQUIRED: (
        "أكمل ربط WhatsApp Business Platform أو Embedded Signup."
    ),
    EMBEDDED_SIGNUP_CONNECTED: "تم ربط واتساب المتجر — راجع حالة الإرسال.",
    EMBEDDED_SIGNUP_FAILED: "حدث خطأ أثناء الربط — أعد المحاولة أو راجع الإعدادات.",
}

EMBEDDED_SIGNUP_CONNECT_HREF = "/dashboard#whatsapp-connect"


def normalize_embedded_signup_status(raw: Any) -> Optional[str]:
    key = (raw or "").strip().lower()
    if key in CANONICAL_EMBEDDED_SIGNUP_STATES:
        return key
    return None


@dataclass
class EmbeddedSignupReadiness:
    """Per-store Embedded Signup readiness snapshot."""

    applicable: bool = False
    status: str = EMBEDDED_SIGNUP_NOT_STARTED
    status_ar: str = EMBEDDED_SIGNUP_STATE_LABEL_AR[EMBEDDED_SIGNUP_NOT_STARTED]
    next_action_ar: str = EMBEDDED_SIGNUP_STATE_NEXT_ACTION_AR[EMBEDDED_SIGNUP_NOT_STARTED]
    connect_href: str = EMBEDDED_SIGNUP_CONNECT_HREF
    launch_ready: bool = False
    foundation_only: bool = True
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _store_has_number(store: Optional[Any]) -> bool:
    if store is None:
        return False
    return bool((getattr(store, "store_whatsapp_number", None) or "").strip())


def _merchant_recovery_enabled(store: Optional[Any]) -> bool:
    if store is None:
        return False
    raw = getattr(store, "whatsapp_recovery_enabled", None)
    return True if raw is None else bool(raw)


def _persisted_status(store: Optional[Any]) -> Optional[str]:
    if store is None:
        return None
    return normalize_embedded_signup_status(
        getattr(store, "whatsapp_embedded_signup_status", None)
    )


def _has_connected_assets(store: Optional[Any]) -> bool:
    """Future: waba_id + phone_number_id on store. V1 foundation — persisted status only."""
    status = _persisted_status(store)
    if status == EMBEDDED_SIGNUP_CONNECTED:
        return True
    waba = (getattr(store, "whatsapp_waba_id", None) or "").strip()
    phone_id = (getattr(store, "whatsapp_phone_number_id", None) or "").strip()
    return bool(waba and phone_id)


def _needs_meta_pairing(store: Optional[Any]) -> bool:
    try:
        from services.merchant_whatsapp_readiness_presentation_v1 import (  # noqa: PLC0415
            PENDING_REASON_META_PAIRING_REQUIRED,
            _existing_whatsapp_business_needs_meta_pairing,
            _resolve_sending_pending_reason,
        )
        from services.merchant_whatsapp_onboarding_journeys_v1 import (  # noqa: PLC0415
            normalize_whatsapp_onboarding_journey,
        )

        journey = normalize_whatsapp_onboarding_journey(
            getattr(store, "whatsapp_onboarding_journey", None)
        )
        if _existing_whatsapp_business_needs_meta_pairing(store, journey):
            return True
        reason = _resolve_sending_pending_reason(store, journey_key=journey)
        return reason == PENDING_REASON_META_PAIRING_REQUIRED
    except Exception:  # noqa: BLE001
        return _store_has_number(store) and _merchant_recovery_enabled(store)


def evaluate_embedded_signup_readiness(store: Optional[Any]) -> EmbeddedSignupReadiness:
    """
    Derive Embedded Signup readiness for Path B merchants.

    Path A (cartflow_managed) → applicable=False, status not_started.
    """
    mode = normalize_whatsapp_mode(
        getattr(store, "whatsapp_mode", None) if store else None
    )
    out = EmbeddedSignupReadiness()
    out.evidence.append(f"whatsapp_mode={mode}")

    if mode != WHATSAPP_MODE_MERCHANT_WHATSAPP:
        out.evidence.append("embedded_signup_not_applicable_for_path_a")
        return out

    out.applicable = True
    persisted = _persisted_status(store)
    if persisted:
        out.evidence.append(f"persisted_status={persisted}")

    if persisted == EMBEDDED_SIGNUP_FAILED:
        out.status = EMBEDDED_SIGNUP_FAILED
    elif persisted == EMBEDDED_SIGNUP_CONNECTED or _has_connected_assets(store):
        out.status = EMBEDDED_SIGNUP_CONNECTED
        out.launch_ready = False
    elif _needs_meta_pairing(store):
        out.status = EMBEDDED_SIGNUP_PAIRING_REQUIRED
        out.launch_ready = True
    else:
        out.status = EMBEDDED_SIGNUP_NOT_STARTED
        out.launch_ready = True

    out.status_ar = EMBEDDED_SIGNUP_STATE_LABEL_AR.get(out.status, out.status)
    out.next_action_ar = EMBEDDED_SIGNUP_STATE_NEXT_ACTION_AR.get(
        out.status, out.next_action_ar
    )
    return out


def embedded_signup_fields_for_api(store: Optional[Any]) -> dict[str, Any]:
    """Read-only API block for recovery-settings / connect page."""
    ev = evaluate_embedded_signup_readiness(store)
    return {
        "whatsapp_embedded_signup": {
            "applicable": ev.applicable,
            "status": ev.status,
            "status_ar": ev.status_ar,
            "next_action_ar": ev.next_action_ar,
            "connect_href": ev.connect_href,
            "launch_ready": ev.launch_ready,
            "foundation_only": ev.foundation_only,
            "evidence": list(ev.evidence),
        }
    }


def ensure_store_whatsapp_embedded_signup_status_column(db: Any) -> None:
    """Idempotent DDL for stores.whatsapp_embedded_signup_status (foundation)."""
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import SQLAlchemyError

    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        cols = {c["name"] for c in insp.get_columns("stores")}
        if "whatsapp_embedded_signup_status" in cols:
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        if dialect in ("postgresql", "postgres"):
            stmt = (
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                "whatsapp_embedded_signup_status VARCHAR(32)"
            )
        else:
            stmt = (
                "ALTER TABLE stores ADD COLUMN whatsapp_embedded_signup_status "
                "VARCHAR(32)"
            )
        db.session.execute(text(stmt))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()


_schema_once = False


def ensure_whatsapp_embedded_signup_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    ensure_store_whatsapp_embedded_signup_status_column(db)
    _schema_once = True


def reset_whatsapp_embedded_signup_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False
