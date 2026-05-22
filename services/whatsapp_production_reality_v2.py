# -*- coding: utf-8 -*-
"""
WhatsApp Production Reality v2 — 24h window + template routing foundation (observe only).

Does not block sends, alter recovery, lifecycle, attribution, queue, or widget.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

log = logging.getLogger("cartflow")

WINDOW_INSIDE = "inside_24h"
WINDOW_OUTSIDE = "outside_24h"
WINDOW_UNKNOWN = "unknown"

CONVERSATION_WINDOW_HOURS = 24.0

READINESS_SANDBOX_ONLY = "sandbox_only"
READINESS_PARTIAL = "partial"
READINESS_PRODUCTION_READY = "production_ready"

_inbound_lock = threading.Lock()
_inbound_observed_at: dict[str, datetime] = {}


@dataclass
class ConversationWindowResult:
    conversation_window_status: str = WINDOW_UNKNOWN
    last_customer_inbound_at: Optional[datetime] = None
    hours_since_inbound: Optional[float] = None
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.last_customer_inbound_at is not None:
            d["last_customer_inbound_at"] = self.last_customer_inbound_at.isoformat()
        return d


@dataclass
class TemplateRoutingDecision:
    freeform_allowed: bool = False
    template_required: bool = True
    conversation_window_status: str = WINDOW_UNKNOWN
    reason: str = ""
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StoreWhatsAppProductionReadiness:
    store_slug: str = ""
    provider_connected: bool = False
    templates_ready: bool = False
    delivery_truth_ready: bool = False
    merchant_readiness_level: str = READINESS_SANDBOX_ONLY
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _phone_key(raw: Any) -> str:
    from services.whatsapp_positive_reply import normalize_wa_customer_digits

    return normalize_wa_customer_digits(raw)


def _parse_iso_utc(iso_s: Any) -> Optional[datetime]:
    if iso_s is None:
        return None
    if isinstance(iso_s, datetime):
        return _ensure_aware(iso_s)
    if not str(iso_s).strip():
        return None
    s = str(iso_s).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return _ensure_aware(datetime.fromisoformat(s))
    except ValueError:
        return None


def _emit_lines(lines: list[str]) -> None:
    for line in lines:
        print(line, flush=True)
        log.info("%s", line)


def record_customer_inbound_observed(
    *,
    customer_phone_key: str,
    observed_at: Optional[datetime] = None,
    store_slug: str = "",
) -> None:
    """In-process + optional DB hint; does not send messages."""
    key = _phone_key(customer_phone_key)
    if len(key) < 11:
        return
    at = _ensure_aware(observed_at or _utc_now())
    with _inbound_lock:
        prev = _inbound_observed_at.get(key)
        if prev is None or at > _ensure_aware(prev):
            _inbound_observed_at[key] = at
    _persist_inbound_observation_event(key, at, store_slug)


def _persist_inbound_observation_event(
    phone_key: str, at: datetime, store_slug: str
) -> None:
    try:
        from extensions import db
        from models import RecoveryEvent

        db.create_all()
        payload = {
            "event": "wa_customer_inbound_v2",
            "customer_phone_key": phone_key,
            "observed_at": at.isoformat(),
            "store_slug": (store_slug or "")[:255],
        }
        row = RecoveryEvent(
            event_type="wa_customer_inbound_v2",
            payload=json.dumps(payload, ensure_ascii=False)[:65000],
        )
        db.session.add(row)
        db.session.commit()
    except Exception:  # noqa: BLE001
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:
            pass


def _lookup_last_inbound_from_db(
    phone_key: str, *, store_id: Optional[int] = None
) -> Optional[datetime]:
    if len(phone_key) < 11:
        return None
    try:
        from extensions import db
        from models import MerchantFollowupAction, RecoveryEvent
        from sqlalchemy import desc

        db.create_all()
        q = (
            db.session.query(MerchantFollowupAction)
            .filter(MerchantFollowupAction.customer_phone == phone_key)
            .order_by(desc(MerchantFollowupAction.updated_at))
        )
        if store_id is not None:
            q = q.filter(MerchantFollowupAction.store_id == int(store_id))
        row = q.first()
        if row is not None and getattr(row, "updated_at", None) is not None:
            if getattr(row, "inbound_message", None):
                return _ensure_aware(row.updated_at)

        ev = (
            db.session.query(RecoveryEvent)
            .filter(RecoveryEvent.event_type == "wa_customer_inbound_v2")
            .order_by(desc(RecoveryEvent.created_at))
            .limit(200)
            .all()
        )
        best: Optional[datetime] = None
        for e in ev:
            raw = getattr(e, "payload", None) or ""
            try:
                data = json.loads(raw) if isinstance(raw, str) else {}
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(data, dict):
                continue
            if str(data.get("customer_phone_key") or "") != phone_key:
                continue
            dt = _parse_iso_utc(data.get("observed_at")) or _parse_iso_utc(
                getattr(e, "created_at", None)
            )
            if dt and (best is None or dt > best):
                best = dt
        return best
    except Exception as exc:  # noqa: BLE001
        log.debug("wa v2 inbound db lookup failed: %s", exc)
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:
            pass
        return None


def resolve_last_customer_inbound_at(
    customer_phone_key: str,
    *,
    abandoned_cart: Optional[Any] = None,
    store: Optional[Any] = None,
) -> Optional[datetime]:
    key = _phone_key(customer_phone_key)
    if len(key) < 11:
        return None
    candidates: list[datetime] = []
    with _inbound_lock:
        cached = _inbound_observed_at.get(key)
        if cached is not None:
            candidates.append(_ensure_aware(cached))
    if abandoned_cart is not None:
        try:
            from services.behavioral_recovery.state_store import (
                behavioral_dict_for_abandoned_cart,
            )

            bh = behavioral_dict_for_abandoned_cart(abandoned_cart)
            for fld in (
                "last_customer_reply_at",
                "latest_customer_reply_at",
                "customer_replied_at",
            ):
                dt = _parse_iso_utc(bh.get(fld))
                if dt is not None:
                    candidates.append(dt)
        except Exception:  # noqa: BLE001
            pass
    store_id = getattr(store, "id", None) if store is not None else None
    if store_id is None and abandoned_cart is not None:
        store_id = getattr(abandoned_cart, "store_id", None)
    db_dt = _lookup_last_inbound_from_db(key, store_id=store_id)
    if db_dt is not None:
        candidates.append(db_dt)
    if not candidates:
        return None
    return max(candidates)


def evaluate_conversation_window(
    *,
    customer_phone_key: str,
    abandoned_cart: Optional[Any] = None,
    store: Optional[Any] = None,
    now: Optional[datetime] = None,
) -> ConversationWindowResult:
    now = _ensure_aware(now or _utc_now())
    last = resolve_last_customer_inbound_at(
        customer_phone_key,
        abandoned_cart=abandoned_cart,
        store=store,
    )
    evidence: list[str] = []
    if last is None:
        evidence.append("no_inbound_history")
        return ConversationWindowResult(
            conversation_window_status=WINDOW_UNKNOWN,
            evidence=evidence,
        )
    hours = (now - _ensure_aware(last)).total_seconds() / 3600.0
    evidence.append(f"last_inbound_hours_ago={hours:.2f}")
    if hours < CONVERSATION_WINDOW_HOURS:
        status = WINDOW_INSIDE
    else:
        status = WINDOW_OUTSIDE
    return ConversationWindowResult(
        conversation_window_status=status,
        last_customer_inbound_at=last,
        hours_since_inbound=hours,
        evidence=evidence,
    )


def decide_template_routing(
    window: ConversationWindowResult,
) -> TemplateRoutingDecision:
    st = (window.conversation_window_status or WINDOW_UNKNOWN).strip()
    if st == WINDOW_INSIDE:
        return TemplateRoutingDecision(
            freeform_allowed=True,
            template_required=False,
            conversation_window_status=st,
            reason="inside_24h_session",
            evidence=list(window.evidence),
        )
    if st == WINDOW_OUTSIDE:
        return TemplateRoutingDecision(
            freeform_allowed=False,
            template_required=True,
            conversation_window_status=st,
            reason="outside_24h_requires_approved_template",
            evidence=list(window.evidence),
        )
    return TemplateRoutingDecision(
        freeform_allowed=False,
        template_required=True,
        conversation_window_status=WINDOW_UNKNOWN,
        reason="unknown_window_conservative_template",
        evidence=list(window.evidence) + ["no_send_policy_change_v2"],
    )


def _store_slug(store: Optional[Any]) -> str:
    if store is None:
        return ""
    for attr in ("slug", "zid_store_id"):
        v = getattr(store, attr, None)
        if isinstance(v, str) and v.strip():
            return v.strip()[:255]
    return ""


def _store_has_template_catalog(store: Any) -> bool:
    for attr in ("reason_templates_json", "trigger_templates_json"):
        raw = getattr(store, attr, None)
        if isinstance(raw, str) and raw.strip() and raw.strip() not in ("{}", "[]"):
            return True
    return False


def evaluate_store_whatsapp_production_readiness(
    store: Optional[Any],
) -> StoreWhatsAppProductionReadiness:
    from services.whatsapp_send import (
        recovery_uses_real_whatsapp,
        resolve_twilio_status_callback_url,
        whatsapp_real_configured,
    )

    slug = _store_slug(store)
    evidence: list[str] = []
    sandbox = not bool(recovery_uses_real_whatsapp())
    recovery_on = bool(getattr(store, "whatsapp_recovery_enabled", False)) if store else False

    provider_connected = False
    if not sandbox and recovery_on:
        try:
            from services.cartflow_provider_readiness import get_twilio_readiness

            tw = get_twilio_readiness()
            provider_connected = bool(tw.get("ready"))
            if provider_connected:
                evidence.append("twilio_provider_ready")
            else:
                evidence.append("twilio_provider_not_ready")
        except Exception:  # noqa: BLE001
            evidence.append("provider_readiness_lookup_failed")
    elif sandbox:
        evidence.append("sandbox_or_mock_path")
    else:
        evidence.append("recovery_disabled_or_no_store")

    templates_ready = False
    if store is not None and recovery_on and _store_has_template_catalog(store):
        templates_ready = True
        evidence.append("local_template_catalog_configured")
    else:
        evidence.append("templates_not_configured_or_not_ready")

    delivery_truth_ready = bool(
        not sandbox
        and whatsapp_real_configured()
        and resolve_twilio_status_callback_url()
    )
    if delivery_truth_ready:
        evidence.append("status_callback_url_resolved")
    else:
        evidence.append("delivery_truth_callback_missing_or_mock")

    if sandbox:
        level = READINESS_SANDBOX_ONLY
    elif provider_connected and templates_ready and delivery_truth_ready:
        level = READINESS_PRODUCTION_READY
    else:
        level = READINESS_PARTIAL

    return StoreWhatsAppProductionReadiness(
        store_slug=slug,
        provider_connected=provider_connected,
        templates_ready=templates_ready,
        delivery_truth_ready=delivery_truth_ready,
        merchant_readiness_level=level,
        evidence=evidence,
    )


def build_platform_whatsapp_production_snapshot() -> dict[str, Any]:
    """Admin / ops: platform-level merchant readiness signal (no store)."""
    from services.whatsapp_send import recovery_uses_real_whatsapp

    if not recovery_uses_real_whatsapp():
        return {
            "merchant_readiness_level": READINESS_SANDBOX_ONLY,
            "provider_connected": False,
            "templates_ready": False,
            "delivery_truth_ready": False,
            "note": "PRODUCTION_MODE off or Twilio not configured — mock/sandbox path",
        }
    sr = evaluate_store_whatsapp_production_readiness(None)
    sr.provider_connected = bool(
        recovery_uses_real_whatsapp()
        and _platform_provider_ready()
    )
    if sr.provider_connected and sr.delivery_truth_ready:
        sr.merchant_readiness_level = (
            READINESS_PRODUCTION_READY
            if sr.templates_ready
            else READINESS_PARTIAL
        )
    else:
        sr.merchant_readiness_level = READINESS_PARTIAL
    return sr.to_dict()


def _platform_provider_ready() -> bool:
    try:
        from services.cartflow_provider_readiness import get_twilio_readiness

        return bool(get_twilio_readiness().get("ready"))
    except Exception:  # noqa: BLE001
        return False


def log_window_and_template_decision(
    *,
    customer_phone_key: str,
    window: ConversationWindowResult,
    template: TemplateRoutingDecision,
    context: str = "",
) -> None:
    key = _phone_key(customer_phone_key)
    ctx = f" context={context}" if context else ""
    _emit_lines(
        [
            f"[WA WINDOW CHECK] window={window.conversation_window_status} "
            f"phone_key={key[:20]}{ctx}",
            (
                "[WA TEMPLATE DECISION] "
                f"freeform_allowed={'true' if template.freeform_allowed else 'false'} "
                f"template_required={'true' if template.template_required else 'false'} "
                f"window={template.conversation_window_status}"
            ),
        ]
    )


def observe_inbound_whatsapp_message(body: Any, from_number: Any) -> dict[str, Any]:
    """Record inbound + window/template logs (foundation only)."""
    raw = str(body or "").strip()
    if not raw:
        return {"observed": False, "reason": "empty_body"}
    key = _phone_key(from_number)
    if len(key) < 11:
        return {"observed": False, "reason": "invalid_phone"}
    record_customer_inbound_observed(customer_phone_key=key)
    window = evaluate_conversation_window(customer_phone_key=key)
    template = decide_template_routing(window)
    log_window_and_template_decision(
        customer_phone_key=key,
        window=window,
        template=template,
        context="inbound",
    )
    return {
        "observed": True,
        "window": window.to_dict(),
        "template": template.to_dict(),
    }


def observe_outbound_whatsapp_context(
    *,
    customer_phone: str,
    store_slug: str = "",
    abandoned_cart: Optional[Any] = None,
    store: Optional[Any] = None,
    context: str = "outbound_send",
) -> dict[str, Any]:
    """Before send: log window + template decision only — does not block."""
    key = _phone_key(customer_phone)
    window = evaluate_conversation_window(
        key,
        abandoned_cart=abandoned_cart,
        store=store,
    )
    template = decide_template_routing(window)
    log_window_and_template_decision(
        customer_phone_key=key,
        window=window,
        template=template,
        context=context,
    )
    store_ready = evaluate_store_whatsapp_production_readiness(store)
    if store_slug and not store_ready.store_slug:
        store_ready.store_slug = store_slug[:255]
    return {
        "window": window.to_dict(),
        "template": template.to_dict(),
        "store_readiness": store_ready.to_dict(),
    }


def clear_inbound_observations_for_tests() -> None:
    with _inbound_lock:
        _inbound_observed_at.clear()
