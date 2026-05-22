# -*- coding: utf-8 -*-
"""
Purchase Attribution v1 — confidence-based influence estimate after Purchase Truth.

Additive only: does not change Purchase Truth closure, lifecycle, WhatsApp, schedules,
widget, dashboard, or integrations gateway. Not absolute causality.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

log = logging.getLogger("cartflow")

DEFAULT_ATTRIBUTION_WINDOW_HOURS = 72

LEVEL_CONFIRMED = "confirmed_recovery"
LEVEL_LIKELY = "likely_recovery"
LEVEL_ASSISTED = "assisted_recovery"
LEVEL_ORGANIC = "organic_or_unknown"
LEVEL_NOT_ATTRIBUTED = "not_attributed"

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
CONFIDENCE_NONE = "none"

RECOMMENDED_LABELS: dict[str, str] = {
    LEVEL_CONFIRMED: "Confirmed recovery (high confidence)",
    LEVEL_LIKELY: "Likely recovery (medium confidence)",
    LEVEL_ASSISTED: "Assisted recovery (uncertain influence)",
    LEVEL_ORGANIC: "Organic or unknown",
    LEVEL_NOT_ATTRIBUTED: "Not attributed to recovery",
}


@dataclass
class AttributionInputs:
    recovery_key: str = ""
    store_slug: str = ""
    session_id: str = ""
    cart_id: str = ""
    reason_tag: str = ""
    recovery_sent_at: Optional[datetime] = None
    purchase_completed_at: Optional[datetime] = None
    customer_replied: bool = False
    returned_to_site: bool = False
    recovery_click: bool = False
    reason_captured: bool = False
    recovery_sent: bool = False
    recovery_blocked: bool = False
    attribution_window_hours: float = DEFAULT_ATTRIBUTION_WINDOW_HOURS


@dataclass
class AttributionDecision:
    attribution_level: str
    confidence: str
    reason: str
    evidence: list[str] = field(default_factory=list)
    window_hours: float = DEFAULT_ATTRIBUTION_WINDOW_HOURS
    purchase_after_recovery: bool = False
    recommended_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_aware(value)
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return _ensure_aware(datetime.fromisoformat(s))
    except (TypeError, ValueError):
        return None


def _split_recovery_key(recovery_key: str) -> tuple[str, str]:
    rk = (recovery_key or "").strip()
    if ":" in rk:
        store, _, sess = rk.partition(":")
        return store.strip(), sess.strip()
    return rk, ""


def _strong_engagement(inp: AttributionInputs) -> bool:
    return bool(inp.customer_replied or inp.returned_to_site or inp.recovery_click)


def compute_attribution_decision(inp: AttributionInputs) -> AttributionDecision:
    """
    Pure confidence-based classifier — no side effects.

    Does not claim absolute causality; levels reflect evidence strength only.
    """
    window_h = max(1.0, float(inp.attribution_window_hours or DEFAULT_ATTRIBUTION_WINDOW_HOURS))
    evidence: list[str] = []
    purchase_at = inp.purchase_completed_at or _utc_now()
    purchase_at = _ensure_aware(purchase_at)
    sent_at = inp.recovery_sent_at
    if sent_at is not None:
        sent_at = _ensure_aware(sent_at)

    if inp.recovery_sent or sent_at is not None:
        evidence.append("recovery_message_sent")
    if inp.reason_captured or (inp.reason_tag or "").strip():
        evidence.append("reason_captured")
    if inp.customer_replied:
        evidence.append("customer_replied")
    if inp.returned_to_site:
        evidence.append("returned_to_site")
    if inp.recovery_click:
        evidence.append("recovery_click")
    if inp.recovery_blocked:
        evidence.append("recovery_blocked")

    purchase_after = False
    if sent_at is not None:
        purchase_after = purchase_at >= sent_at
        if purchase_after:
            evidence.append("purchase_after_recovery_send")
        else:
            evidence.append("purchase_before_recovery_send")

    # --- not_attributed ---
    if inp.recovery_blocked and not inp.recovery_sent and sent_at is None:
        return AttributionDecision(
            attribution_level=LEVEL_NOT_ATTRIBUTED,
            confidence=CONFIDENCE_NONE,
            reason="recovery_blocked_or_stopped",
            evidence=evidence,
            window_hours=window_h,
            purchase_after_recovery=False,
            recommended_label=RECOMMENDED_LABELS[LEVEL_NOT_ATTRIBUTED],
        )

    if sent_at is not None and not purchase_after:
        return AttributionDecision(
            attribution_level=LEVEL_NOT_ATTRIBUTED,
            confidence=CONFIDENCE_NONE,
            reason="purchase_before_recovery",
            evidence=evidence,
            window_hours=window_h,
            purchase_after_recovery=False,
            recommended_label=RECOMMENDED_LABELS[LEVEL_NOT_ATTRIBUTED],
        )

    if sent_at is not None and purchase_after:
        delta = purchase_at - sent_at
        if delta > timedelta(hours=window_h):
            return AttributionDecision(
                attribution_level=LEVEL_NOT_ATTRIBUTED,
                confidence=CONFIDENCE_NONE,
                reason="outside_attribution_window",
                evidence=evidence + [f"elapsed_hours={delta.total_seconds() / 3600:.1f}"],
                window_hours=window_h,
                purchase_after_recovery=True,
                recommended_label=RECOMMENDED_LABELS[LEVEL_NOT_ATTRIBUTED],
            )

    # --- confirmed_recovery ---
    if (inp.recovery_sent or sent_at is not None) and purchase_after and _strong_engagement(inp):
        reason = "reply_after_recovery_then_purchase"
        if inp.recovery_click and not inp.customer_replied:
            reason = "click_after_recovery_then_purchase"
        elif inp.returned_to_site and not inp.customer_replied:
            reason = "return_after_recovery_then_purchase"
        return AttributionDecision(
            attribution_level=LEVEL_CONFIRMED,
            confidence=CONFIDENCE_HIGH,
            reason=reason,
            evidence=evidence,
            window_hours=window_h,
            purchase_after_recovery=True,
            recommended_label=RECOMMENDED_LABELS[LEVEL_CONFIRMED],
        )

    # --- likely_recovery ---
    if (inp.recovery_sent or sent_at is not None) and purchase_after:
        return AttributionDecision(
            attribution_level=LEVEL_LIKELY,
            confidence=CONFIDENCE_MEDIUM,
            reason=f"purchase_within_{int(window_h)}h_after_recovery",
            evidence=evidence,
            window_hours=window_h,
            purchase_after_recovery=True,
            recommended_label=RECOMMENDED_LABELS[LEVEL_LIKELY],
        )

    # --- assisted_recovery ---
    if inp.reason_captured or (inp.reason_tag or "").strip() or inp.returned_to_site or _strong_engagement(inp):
        reason = "widget_or_reason_without_confirmed_recovery_chain"
        if inp.returned_to_site:
            reason = "return_or_widget_engagement_uncertain_influence"
        return AttributionDecision(
            attribution_level=LEVEL_ASSISTED,
            confidence=CONFIDENCE_LOW,
            reason=reason,
            evidence=evidence,
            window_hours=window_h,
            purchase_after_recovery=purchase_after,
            recommended_label=RECOMMENDED_LABELS[LEVEL_ASSISTED],
        )

    # --- organic_or_unknown ---
    return AttributionDecision(
        attribution_level=LEVEL_ORGANIC,
        confidence=CONFIDENCE_LOW,
        reason="no_recovery_evidence",
        evidence=evidence or ["purchase_truth_only"],
        window_hours=window_h,
        purchase_after_recovery=purchase_after,
        recommended_label=RECOMMENDED_LABELS[LEVEL_ORGANIC],
    )


def log_attribution_decision(
    decision: AttributionDecision,
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    recovery_key: str,
) -> None:
    lines = [
        "[ATTRIBUTION DECISION]",
        f"store_slug={(store_slug or '-')[:255]}",
        f"session_id={(session_id or '-')[:80]}",
        f"cart_id={(cart_id or '-')[:64]}",
        f"recovery_key={(recovery_key or '-')[:120]}",
        f"attribution_level={decision.attribution_level}",
        f"confidence={decision.confidence}",
        f"reason={decision.reason[:120]}",
        f"purchase_after_recovery={'true' if decision.purchase_after_recovery else 'false'}",
        f"window_hours={decision.window_hours}",
    ]
    if decision.evidence:
        lines.append(f"evidence={','.join(decision.evidence)[:200]}")
    block = "\n".join(lines)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def _persist_attribution_event_readonly(
    decision: AttributionDecision,
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    recovery_key: str,
) -> None:
    """Optional lightweight row on existing ``recovery_events`` — failures are ignored."""
    try:
        from extensions import db
        from models import RecoveryEvent, Store

        db.create_all()
        store_id = None
        if store_slug:
            row = (
                db.session.query(Store.id)
                .filter(Store.slug == store_slug)
                .limit(1)
                .first()
            )
            if row is not None:
                store_id = row[0]
        payload = {
            "kind": "purchase_attribution_v1",
            "recovery_key": recovery_key,
            "session_id": session_id,
            "cart_id": cart_id,
            "decision": decision.to_dict(),
        }
        ev = RecoveryEvent(
            store_id=store_id,
            abandoned_cart_id=None,
            event_type="purchase_attribution_v1",
            payload=json.dumps(payload, ensure_ascii=False, default=str)[:65000],
        )
        db.session.add(ev)
        db.session.commit()
    except Exception as exc:  # noqa: BLE001
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:
            pass
        log.debug("attribution event persist skipped: %s", exc)


def gather_attribution_inputs(
    recovery_key: str,
    *,
    session_id: str = "",
    cart_id: str = "",
    store_slug: str = "",
    ac: Any = None,
    context_payload: Optional[dict[str, Any]] = None,
    attribution_window_hours: float = DEFAULT_ATTRIBUTION_WINDOW_HOURS,
) -> AttributionInputs:
    """Collect evidence from DB / behavioral state (best-effort, no guessing)."""
    rk = (recovery_key or "").strip()
    ss = (store_slug or "").strip() or _split_recovery_key(rk)[0]
    sid = (session_id or "").strip() or _split_recovery_key(rk)[1]
    cid = (cart_id or "").strip()

    purchase_at = _utc_now()
    if isinstance(context_payload, dict):
        for key in (
            "purchase_completed_at",
            "converted_at",
            "order_paid_at",
            "purchased_at",
        ):
            parsed = _parse_dt(context_payload.get(key))
            if parsed is not None:
                purchase_at = parsed
                break

    recovery_sent_at: Optional[datetime] = None
    recovery_sent = False
    customer_replied = False
    returned_to_site = False
    recovery_click = False
    reason_tag = ""
    reason_captured = False
    recovery_blocked = False

    try:
        from services.behavioral_recovery.state_store import (
            abandoned_carts_for_session_or_cart,
            behavioral_dict_for_abandoned_cart,
            customer_replied_flagged_for_session,
            normal_recovery_message_was_sent_for_abandoned,
        )

        carts = []
        if ac is not None:
            carts = [ac]
        else:
            carts = abandoned_carts_for_session_or_cart(sid, cid or None)
        for cart in carts:
            bh = behavioral_dict_for_abandoned_cart(cart)
            if bh.get("customer_replied") is True:
                customer_replied = True
            if bh.get("user_returned_to_site") is True or bh.get("returned_to_site") is True:
                returned_to_site = True
            if bh.get("recovery_link_clicked") is True:
                recovery_click = True
            if bh.get("future_recovery_allowed") is False and not normal_recovery_message_was_sent_for_abandoned(cart):
                recovery_blocked = True
            rt = str(bh.get("reason_tag") or bh.get("recovery_reason") or "").strip()
            if rt:
                reason_tag = rt
        if sid or cid:
            customer_replied = customer_replied or customer_replied_flagged_for_session(
                sid, cid or None
            )
            for cart in carts:
                if normal_recovery_message_was_sent_for_abandoned(cart):
                    recovery_sent = True
                    break
    except Exception as exc:  # noqa: BLE001
        log.debug("attribution behavioral gather: %s", exc)

    try:
        from extensions import db
        from models import CartRecoveryLog, CartRecoveryReason

        db.create_all()
        conds = []
        if sid:
            conds.append(CartRecoveryLog.session_id == sid)
        if cid:
            conds.append(CartRecoveryLog.cart_id == cid)
        if ss:
            conds.append(CartRecoveryLog.store_slug == ss)
        if conds:
            from sqlalchemy import or_

            row = (
                db.session.query(CartRecoveryLog)
                .filter(
                    CartRecoveryLog.status.in_(("sent_real", "mock_sent")),
                    or_(*conds),
                )
                .order_by(CartRecoveryLog.sent_at.asc(), CartRecoveryLog.created_at.asc())
                .first()
            )
            if row is not None:
                recovery_sent = True
                ts = row.sent_at or row.created_at
                if ts is not None:
                    recovery_sent_at = _ensure_aware(ts)
        if ss and sid:
            rr = (
                db.session.query(CartRecoveryReason.reason)
                .filter(
                    CartRecoveryReason.store_slug == ss,
                    CartRecoveryReason.session_id == sid,
                )
                .limit(1)
                .first()
            )
            if rr and rr[0]:
                reason_captured = True
                if not reason_tag:
                    reason_tag = str(rr[0]).strip()
    except Exception as exc:  # noqa: BLE001
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:
            pass
        log.debug("attribution db gather: %s", exc)

    try:
        from main import _recovery_session_lock, _session_recovery_sent  # noqa: PLC0415

        with _recovery_session_lock:
            if _session_recovery_sent.get(rk):
                recovery_sent = True
    except Exception:
        pass

    return AttributionInputs(
        recovery_key=rk,
        store_slug=ss,
        session_id=sid,
        cart_id=cid,
        reason_tag=reason_tag,
        recovery_sent_at=recovery_sent_at,
        purchase_completed_at=purchase_at,
        customer_replied=customer_replied,
        returned_to_site=returned_to_site,
        recovery_click=recovery_click,
        reason_captured=reason_captured,
        recovery_sent=recovery_sent,
        recovery_blocked=recovery_blocked,
        attribution_window_hours=attribution_window_hours,
    )


def run_purchase_attribution_after_truth_closure(
    recovery_key: str,
    *,
    session_id: str = "",
    cart_id: str = "",
    store_slug: str = "",
    ac: Any = None,
    context_payload: Optional[dict[str, Any]] = None,
    purchase_truth_source: str = "",
) -> Optional[AttributionDecision]:
    """
    Run after ``[PURCHASE LIFECYCLE CLOSED]`` from Purchase Truth.

    Never raises — failures are logged only.
    """
    try:
        inp = gather_attribution_inputs(
            recovery_key,
            session_id=session_id,
            cart_id=cart_id,
            store_slug=store_slug,
            ac=ac,
            context_payload=context_payload,
        )
        decision = compute_attribution_decision(inp)
        ss = inp.store_slug or _split_recovery_key(recovery_key)[0]
        log_attribution_decision(
            decision,
            store_slug=ss,
            session_id=inp.session_id or session_id,
            cart_id=inp.cart_id or cart_id,
            recovery_key=recovery_key,
        )
        _persist_attribution_event_readonly(
            decision,
            store_slug=ss,
            session_id=inp.session_id or session_id,
            cart_id=inp.cart_id or cart_id,
            recovery_key=recovery_key,
        )
        if purchase_truth_source:
            log.debug(
                "attribution after purchase_truth source=%s level=%s",
                purchase_truth_source,
                decision.attribution_level,
            )
        return decision
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "purchase attribution failed (closure unaffected): %s",
            exc,
            exc_info=True,
        )
        try:
            print(
                f"[ATTRIBUTION DECISION] status=failed recovery_key={(recovery_key or '-')[:120]} "
                f"error={str(exc)[:200]}",
                flush=True,
            )
        except OSError:
            pass
        return None
