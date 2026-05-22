# -*- coding: utf-8 -*-
"""
Purchase Attribution v1 — confidence-based influence estimate after Purchase Truth.

Additive only: does not change Purchase Truth closure, lifecycle, WhatsApp, schedules,
widget, dashboard, or integrations gateway. Not absolute causality.

Delivery truth (v1): Twilio ``queued`` / ``accepted_by_provider`` is not delivery proof.
Future confidence may use ``whatsapp_delivery_truth_v1.customer_delivered_for_attribution_future``.
"""
from __future__ import annotations

import json
import logging
import re
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
    recovery_send_source: str = ""


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


_RECOVERY_SENT_STATUSES = frozenset({"sent_real", "mock_sent"})


def _digits_only(phone: Optional[str]) -> str:
    if not phone:
        return ""
    return re.sub(r"\D", "", str(phone).strip())[:32]


def _phone_matches(row_phone: Optional[str], phone_digits: str) -> bool:
    if not phone_digits:
        return True
    row_d = _digits_only(row_phone)
    if not row_d:
        return False
    return row_d == phone_digits or row_d.endswith(phone_digits) or phone_digits.endswith(row_d)


def _row_sent_timestamp(row: Any) -> Optional[datetime]:
    ts = getattr(row, "sent_at", None) or getattr(row, "created_at", None)
    if ts is None:
        return None
    return _ensure_aware(ts)


def pick_latest_recovery_send_from_log_rows(
    rows: list[Any],
    *,
    phone_digits: str = "",
) -> tuple[Optional[datetime], str]:
    """
    Choose the newest successful recovery send from already-scoped rows (same session).
    Prefer phone match when digits provided; never merge other sessions.
    """
    if not rows:
        return None, "no_send_log"
    ordered = sorted(
        rows,
        key=lambda r: (
            _row_sent_timestamp(r) or datetime.min.replace(tzinfo=timezone.utc),
            int(getattr(r, "id", 0) or 0),
        ),
        reverse=True,
    )
    if phone_digits:
        for row in ordered:
            if _phone_matches(getattr(row, "phone", None), phone_digits):
                ts = _row_sent_timestamp(row)
                if ts is not None:
                    return ts, "cart_recovery_log_latest_phone"
    row = ordered[0]
    ts = _row_sent_timestamp(row)
    if ts is None:
        return None, "no_send_log"
    return ts, "cart_recovery_log_latest_session"


def select_latest_recovery_send_at(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str = "",
    customer_phone: str = "",
) -> tuple[Optional[datetime], str]:
    """
    Latest ``CartRecoveryLog`` send for this recovery identity (not oldest, not other sessions).
    """
    sid = (session_id or "").strip()[:512]
    if not sid:
        return None, "missing_session_id"
    ss = (store_slug or "").strip()[:255]
    cid = (cart_id or "").strip()[:255]
    phone_digits = _digits_only(customer_phone)
    try:
        from sqlalchemy import and_

        from extensions import db
        from models import CartRecoveryLog

        db.create_all()
        filters: list[Any] = [
            CartRecoveryLog.session_id == sid,
            CartRecoveryLog.status.in_(tuple(_RECOVERY_SENT_STATUSES)),
            CartRecoveryLog.step.isnot(None),
            CartRecoveryLog.step >= 1,
        ]
        if ss:
            filters.append(CartRecoveryLog.store_slug == ss)
        if cid:
            filters.append(CartRecoveryLog.cart_id == cid)
        rows = (
            db.session.query(CartRecoveryLog)
            .filter(and_(*filters))
            .order_by(
                CartRecoveryLog.sent_at.desc(),
                CartRecoveryLog.created_at.desc(),
                CartRecoveryLog.id.desc(),
            )
            .limit(20)
            .all()
        )
        return pick_latest_recovery_send_from_log_rows(
            list(rows),
            phone_digits=phone_digits,
        )
    except Exception as exc:  # noqa: BLE001
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:
            pass
        log.debug("select_latest_recovery_send_at: %s", exc)
        return None, "query_failed"


def log_attribution_evidence(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    recovery_key: str,
    selected_recovery_sent_at: Optional[datetime],
    purchase_completed_at: Optional[datetime],
    source: str,
) -> None:
    sent_s = (
        selected_recovery_sent_at.isoformat()
        if selected_recovery_sent_at is not None
        else "-"
    )
    purch_s = (
        purchase_completed_at.isoformat()
        if purchase_completed_at is not None
        else "-"
    )
    elapsed_h = "-"
    if (
        selected_recovery_sent_at is not None
        and purchase_completed_at is not None
    ):
        delta = _ensure_aware(purchase_completed_at) - _ensure_aware(
            selected_recovery_sent_at
        )
        elapsed_h = f"{delta.total_seconds() / 3600:.2f}"
    block = (
        "[ATTRIBUTION EVIDENCE]\n"
        f"store_slug={(store_slug or '-')[:255]}\n"
        f"session_id={(session_id or '-')[:80]}\n"
        f"cart_id={(cart_id or '-')[:64]}\n"
        f"recovery_key={(recovery_key or '-')[:120]}\n"
        f"selected_recovery_sent_at={sent_s}\n"
        f"purchase_completed_at={purch_s}\n"
        f"elapsed_hours={elapsed_h}\n"
        f"source={(source or '-')[:64]}"
    )
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def _customer_phone_for_attribution(
    recovery_key: str,
    context_payload: Optional[dict[str, Any]],
) -> str:
    if isinstance(context_payload, dict):
        for key in ("phone", "customer_phone", "abandon_event_phone"):
            raw = context_payload.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()[:100]
    try:
        from services.recovery_session_phone import get_recovery_customer_phone

        p = get_recovery_customer_phone(recovery_key)
        return (p or "").strip()[:100]
    except Exception:  # noqa: BLE001
        return ""


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

    has_current_recovery_send = bool(
        sent_at is not None and purchase_after and (inp.recovery_sent or sent_at)
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
    if (
        not has_current_recovery_send
        and (
            inp.reason_captured
            or (inp.reason_tag or "").strip()
            or inp.returned_to_site
            or _strong_engagement(inp)
        )
    ):
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
    if not has_current_recovery_send:
        reason = "no_current_recovery_send_evidence"
        if "recovery_message_sent" in evidence and sent_at is None:
            evidence.append("stale_or_unscoped_send_log_ignored")
        return AttributionDecision(
            attribution_level=LEVEL_ORGANIC,
            confidence=CONFIDENCE_LOW,
            reason=reason,
            evidence=evidence or ["purchase_truth_only"],
            window_hours=window_h,
            purchase_after_recovery=False,
            recommended_label=RECOMMENDED_LABELS[LEVEL_ORGANIC],
        )

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
    except Exception as exc:  # noqa: BLE001
        log.debug("attribution behavioral gather: %s", exc)

    customer_phone = _customer_phone_for_attribution(rk, context_payload)
    send_source = ""
    latest_ts, send_source = select_latest_recovery_send_at(
        store_slug=ss,
        session_id=sid,
        cart_id=cid,
        customer_phone=customer_phone,
    )
    window_td = timedelta(hours=max(1.0, float(attribution_window_hours)))
    if latest_ts is not None:
        recovery_sent_at = latest_ts
        if purchase_at - recovery_sent_at <= window_td:
            recovery_sent = True
        else:
            recovery_sent_at = None
            send_source = f"{send_source}_stale_ignored"

    try:
        from extensions import db
        from models import CartRecoveryReason

        db.create_all()
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
            memory_sent = bool(_session_recovery_sent.get(rk))
        if memory_sent and recovery_sent_at is None and not recovery_sent:
            recovery_sent_at = purchase_at - timedelta(minutes=1)
            recovery_sent = True
            send_source = "session_memory_recent_send"
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
        recovery_send_source=send_source,
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
        log_attribution_evidence(
            store_slug=ss,
            session_id=inp.session_id or session_id,
            cart_id=inp.cart_id or cart_id,
            recovery_key=recovery_key,
            selected_recovery_sent_at=inp.recovery_sent_at,
            purchase_completed_at=inp.purchase_completed_at,
            source=inp.recovery_send_source or "gather",
        )
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
