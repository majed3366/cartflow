# -*- coding: utf-8 -*-
"""
Canonical recovery message context — one truth for send, logs, carts, messages, admin.

Does not change WhatsApp provider transport or queue scheduling behavior.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("cartflow")

CONTEXT_OK = "ok"
CONTEXT_MISSING = "context_missing"
LEGACY_CONTEXT_MISSING = "legacy_context_missing"

_SENT_LOG_STATUSES = frozenset({"sent_real", "mock_sent"})
_MESSAGE_PREVIEW_MAX = 220


@dataclass
class RecoveryMessageContext:
    recovery_key: str = ""
    store_slug: str = ""
    cart_id: str = ""
    session_id: str = ""
    customer_phone: str = ""
    cart_value: Optional[float] = None
    items_count: Optional[int] = None
    product_names: list[str] = field(default_factory=list)
    reason_tag: str = ""
    message_body: str = ""
    message_type: str = ""
    attempt: int = 1
    provider: str = ""
    provider_message_sid: str = ""
    send_status: str = ""
    sent_at: Optional[str] = None
    delivery_status: str = ""
    read_status: str = ""
    source: str = ""
    context_status: str = LEGACY_CONTEXT_MISSING

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm(s: Optional[str]) -> str:
    return (s or "").strip()


def recovery_key_from_parts(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
) -> str:
    try:
        from main import _recovery_key_from_payload  # noqa: PLC0415

        return _recovery_key_from_payload(
            {
                "store": (store_slug or "").strip(),
                "session_id": (session_id or "").strip(),
                "cart_id": (cart_id or "").strip(),
            }
        )
    except Exception:  # noqa: BLE001
        ss = _norm(store_slug)
        sid = _norm(session_id)
        cid = _norm(cart_id)
        if ss and sid:
            return f"{ss}:{sid}" if not cid else f"{ss}:{sid}:{cid}"
        return ""


def classify_context_linkage(
    *,
    recovery_key: str,
    store_slug: str,
    session_id: str,
    cart_id: str,
) -> str:
    rk = _norm(recovery_key)
    ss = _norm(store_slug)
    sid = _norm(session_id)
    cid = _norm(cart_id)
    if not rk or not ss:
        return CONTEXT_MISSING
    if not sid and not cid:
        return CONTEXT_MISSING
    return CONTEXT_OK


def _parse_raw_payload(ac: Any) -> dict[str, Any]:
    raw = getattr(ac, "raw_payload", None)
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        data = json.loads(str(raw))
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def extract_cart_snapshot(
    ac: Optional[Any] = None,
    *,
    reason_row: Optional[Any] = None,
) -> dict[str, Any]:
    cart_value: Optional[float] = None
    items_count: Optional[int] = None
    product_names: list[str] = []
    reason_tag = ""
    if reason_row is not None:
        reason_tag = _norm(getattr(reason_row, "reason", None) or getattr(reason_row, "reason_tag", None))
    if ac is None:
        return {
            "cart_value": cart_value,
            "items_count": items_count,
            "product_names": product_names,
            "reason_tag": reason_tag,
        }
    try:
        cv = getattr(ac, "cart_value", None)
        if cv is not None:
            cart_value = float(cv)
    except (TypeError, ValueError):
        cart_value = None
    payload = _parse_raw_payload(ac)
    items = payload.get("items") or payload.get("line_items") or payload.get("products")
    if isinstance(items, list):
        items_count = len(items)
        for it in items[:8]:
            if isinstance(it, dict):
                nm = _norm(it.get("name") or it.get("title") or it.get("product_name"))
                if nm:
                    product_names.append(nm[:120])
            elif isinstance(it, str) and it.strip():
                product_names.append(it.strip()[:120])
    if not reason_tag:
        reason_tag = _norm(payload.get("reason_tag") or payload.get("reason"))
    return {
        "cart_value": cart_value,
        "items_count": items_count,
        "product_names": product_names,
        "reason_tag": reason_tag,
    }


def resolve_message_body_for_send(
    *,
    reason_tag: Optional[str],
    store: Optional[Any],
    snapshot: dict[str, Any],
    explicit_body: str = "",
    multi_message_text: str = "",
) -> tuple[str, str]:
    """Return (message_body, message_type). Safe generic only when templates unavailable."""
    body = _norm(explicit_body)
    if body:
        return body, "explicit"
    multi = _norm(multi_message_text)
    if multi:
        return multi, "multi_slot"
    rt = _norm(reason_tag) or _norm(snapshot.get("reason_tag"))
    if rt and store is not None:
        try:
            from services.reason_template_recovery import (  # noqa: PLC0415
                reason_template_blocks_recovery_whatsapp,
                resolve_recovery_whatsapp_message_with_reason_templates,
            )

            if not reason_template_blocks_recovery_whatsapp(rt, store):
                msg = resolve_recovery_whatsapp_message_with_reason_templates(rt, store=store)
                if _norm(msg):
                    return msg, "reason_template"
        except Exception:  # noqa: BLE001
            pass
        try:
            from services.recovery_messages import get_recovery_message  # noqa: PLC0415

            msg2 = get_recovery_message(rt, 1, store)
            if _norm(msg2):
                return msg2, "reason_fallback"
        except Exception:  # noqa: BLE001
            pass
    try:
        from main import _DEFAULT_DECISION_FALLBACK_MESSAGE, _default_recovery_message  # noqa: PLC0415

        generic = _default_recovery_message() or _DEFAULT_DECISION_FALLBACK_MESSAGE
        return _norm(generic) or "مرحباً، نود مساعدتك في إكمال طلبك.", "generic_fallback"
    except Exception:  # noqa: BLE001
        return "مرحباً، نود مساعدتك في إكمال طلبك.", "generic_fallback"


def build_recovery_message_context(
    *,
    recovery_key: str = "",
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    customer_phone: str = "",
    reason_tag: Optional[str] = None,
    message_body: str = "",
    message_type: str = "",
    attempt: int = 1,
    provider: str = "",
    provider_message_sid: str = "",
    send_status: str = "",
    sent_at: Optional[datetime] = None,
    delivery_status: str = "",
    read_status: str = "",
    source: str = "recovery_sequence",
    store: Optional[Any] = None,
    abandoned_cart: Optional[Any] = None,
    reason_row: Optional[Any] = None,
) -> RecoveryMessageContext:
    rk = _norm(recovery_key) or recovery_key_from_parts(
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
    )
    snap = extract_cart_snapshot(abandoned_cart, reason_row=reason_row)
    rt = _norm(reason_tag) or snap.get("reason_tag") or ""
    body = _norm(message_body)
    mtype = _norm(message_type)
    if not body:
        body, mtype = resolve_message_body_for_send(
            reason_tag=rt,
            store=store,
            snapshot=snap,
        )
    elif not mtype:
        mtype = "explicit"
    linkage = classify_context_linkage(
        recovery_key=rk,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
    )
    sent_iso: Optional[str] = None
    if sent_at is not None:
        try:
            dt = sent_at
            if getattr(dt, "tzinfo", None) is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            sent_iso = dt.isoformat()
        except (TypeError, ValueError, AttributeError):
            sent_iso = None
    return RecoveryMessageContext(
        recovery_key=rk,
        store_slug=_norm(store_slug)[:255],
        cart_id=_norm(cart_id)[:255],
        session_id=_norm(session_id)[:512],
        customer_phone=_norm(customer_phone)[:100],
        cart_value=snap.get("cart_value"),
        items_count=snap.get("items_count"),
        product_names=list(snap.get("product_names") or []),
        reason_tag=rt[:64],
        message_body=body[:65000],
        message_type=mtype[:64],
        attempt=max(1, int(attempt or 1)),
        provider=_norm(provider)[:32],
        provider_message_sid=_norm(provider_message_sid)[:128],
        send_status=_norm(send_status)[:50],
        sent_at=sent_iso,
        delivery_status=_norm(delivery_status)[:64],
        read_status=_norm(read_status)[:64],
        source=_norm(source)[:64] or "recovery_sequence",
        context_status=linkage,
    )


def serialize_context_json(ctx: RecoveryMessageContext | dict[str, Any]) -> str:
    if isinstance(ctx, RecoveryMessageContext):
        payload = ctx.to_dict()
    else:
        payload = dict(ctx)
    return json.dumps(payload, ensure_ascii=False)[:65000]


def context_from_log_row(lg: Any) -> dict[str, Any]:
    if lg is None:
        return {}
    raw = getattr(lg, "context_json", None)
    if raw:
        try:
            data = json.loads(str(raw))
            if isinstance(data, dict):
                return data
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    rk = _norm(getattr(lg, "recovery_key", None))
    ss = _norm(getattr(lg, "store_slug", None))
    sid = _norm(getattr(lg, "session_id", None))
    cid = _norm(getattr(lg, "cart_id", None))
    if not rk:
        rk = recovery_key_from_parts(store_slug=ss, session_id=sid, cart_id=cid)
    status = _norm(getattr(lg, "context_status", None))
    if not status:
        status = classify_context_linkage(
            recovery_key=rk, store_slug=ss, session_id=sid, cart_id=cid
        )
        if status == CONTEXT_OK and not getattr(lg, "context_json", None):
            status = LEGACY_CONTEXT_MISSING
    return {
        "recovery_key": rk,
        "store_slug": ss,
        "session_id": sid,
        "cart_id": cid,
        "customer_phone": _norm(getattr(lg, "phone", None)),
        "message_body": _norm(getattr(lg, "message", None)),
        "send_status": _norm(getattr(lg, "status", None)),
        "reason_tag": _norm(getattr(lg, "reason_tag", None)),
        "message_type": _norm(getattr(lg, "message_type", None)),
        "source": _norm(getattr(lg, "source", None)),
        "provider": _norm(getattr(lg, "provider", None)),
        "provider_message_sid": _norm(getattr(lg, "provider_message_sid", None)),
        "context_status": status,
        "attempt": int(getattr(lg, "step", None) or 1),
    }


def merge_persist_context(
    *,
    message_context: Optional[dict[str, Any] | RecoveryMessageContext] = None,
    recovery_key: str = "",
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    phone: Optional[str] = None,
    message: str = "",
    status: str = "",
    step: Optional[int] = None,
    sent_at: Optional[datetime] = None,
    reason_tag: Optional[str] = None,
    provider: str = "",
    provider_message_sid: str = "",
    source: str = "",
    message_type: str = "",
) -> RecoveryMessageContext:
    if isinstance(message_context, RecoveryMessageContext):
        base = message_context
    elif isinstance(message_context, dict) and message_context:
        base = build_recovery_message_context(
            recovery_key=_norm(message_context.get("recovery_key")) or recovery_key,
            store_slug=message_context.get("store_slug") or store_slug,
            session_id=message_context.get("session_id") or session_id,
            cart_id=message_context.get("cart_id") or cart_id,
            customer_phone=message_context.get("customer_phone") or (phone or ""),
            reason_tag=message_context.get("reason_tag") or reason_tag,
            message_body=message_context.get("message_body") or message,
            message_type=message_context.get("message_type") or message_type,
            attempt=int(message_context.get("attempt") or step or 1),
            provider=message_context.get("provider") or provider,
            provider_message_sid=message_context.get("provider_message_sid")
            or provider_message_sid,
            send_status=status or message_context.get("send_status") or "",
            sent_at=sent_at,
            source=message_context.get("source") or source,
        )
    else:
        base = build_recovery_message_context(
            recovery_key=recovery_key,
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id or "",
            customer_phone=phone or "",
            reason_tag=reason_tag,
            message_body=message,
            message_type=message_type,
            attempt=int(step or 1),
            provider=provider,
            provider_message_sid=provider_message_sid,
            send_status=status,
            sent_at=sent_at,
            source=source or "recovery_sequence",
        )
    if status:
        base.send_status = _norm(status)[:50]
    if message:
        base.message_body = _norm(message)[:65000]
    if phone:
        base.customer_phone = _norm(phone)[:100]
    if provider:
        base.provider = _norm(provider)[:32]
    if provider_message_sid:
        base.provider_message_sid = _norm(provider_message_sid)[:128]
    if step is not None:
        base.attempt = max(1, int(step))
    base.context_status = classify_context_linkage(
        recovery_key=base.recovery_key,
        store_slug=base.store_slug,
        session_id=base.session_id,
        cart_id=base.cart_id,
    )
    return base


def derive_messages_page_status(
    log_status: str,
    *,
    context_status: str = "",
) -> str:
    st = _norm(log_status)
    if st in _SENT_LOG_STATUSES:
        if context_status == CONTEXT_MISSING:
            return "sent_context_missing"
        if context_status == LEGACY_CONTEXT_MISSING:
            return "sent_legacy"
        return "sent"
    if st == "whatsapp_failed":
        return "failed"
    if st.startswith("skipped"):
        return "skipped"
    if st == "queued":
        return "queued"
    return "other"


def derive_carts_page_status(
    *,
    phase_key: str,
    coarse: str,
    sent_ct: int,
    log_status: str = "",
    context_status: str = "",
) -> str:
    ls = _norm(log_status)
    if ls in _SENT_LOG_STATUSES or sent_ct > 0:
        if context_status == CONTEXT_MISSING:
            return "sent_context_missing"
        return "sent"
    pk = _norm(phase_key)
    if pk in ("first_message_sent", "reminder_sent"):
        return "sent"
    cr = _norm(coarse)
    if cr == "sent":
        return "sent"
    if cr == "converted":
        return "purchased"
    if cr in ("returned", "stopped"):
        return cr
    return "not_sent"


def detect_truth_mismatch(
    *,
    messages_page_status: str,
    carts_page_status: str,
    log_status: str = "",
    context_status: str = "",
) -> tuple[bool, str]:
    if context_status == CONTEXT_MISSING:
        return True, "message_missing_cart_context"
    mp = _norm(messages_page_status)
    cp = _norm(carts_page_status)
    sent_family = frozenset({"sent", "sent_legacy", "sent_context_missing"})
    if mp in sent_family and cp == "not_sent":
        return True, "messages_sent_carts_not_sent"
    if cp in sent_family and mp not in sent_family and _norm(log_status) in _SENT_LOG_STATUSES:
        return True, "carts_sent_messages_not_sent"
    if mp in sent_family and cp in sent_family and mp != cp:
        if mp != "sent_legacy" and cp != "sent_legacy":
            return True, f"status_label_mismatch:{mp}:{cp}"
    return False, ""


def enrich_cart_row_truth_fields(
    target: dict[str, Any],
    *,
    phase_key: str,
    coarse: str,
    sent_ct: int,
    latest_log: Any = None,
) -> None:
    ctx = context_from_log_row(latest_log)
    log_st = _norm(getattr(latest_log, "status", None) if latest_log else "")
    ctx_st = _norm(ctx.get("context_status"))
    mp = derive_messages_page_status(log_st, context_status=ctx_st)
    cp = derive_carts_page_status(
        phase_key=phase_key,
        coarse=coarse,
        sent_ct=sent_ct,
        log_status=log_st,
        context_status=ctx_st,
    )
    mismatch, mismatch_reason = detect_truth_mismatch(
        messages_page_status=mp,
        carts_page_status=cp,
        log_status=log_st,
        context_status=ctx_st,
    )
    preview = _norm(ctx.get("message_body"))
    if len(preview) > _MESSAGE_PREVIEW_MAX:
        preview = preview[: _MESSAGE_PREVIEW_MAX - 1] + "…"
    target["recovery_message_context"] = ctx
    target["recovery_context_status"] = ctx_st or LEGACY_CONTEXT_MISSING
    target["messages_page_status"] = mp
    target["carts_page_status"] = cp
    target["truth_mismatch_detected"] = mismatch
    target["truth_mismatch_reason"] = mismatch_reason or None
    if preview and not target.get("message_preview"):
        target["message_preview"] = preview
    if mp.startswith("sent") or cp == "sent":
        target["merchant_message_status_ar"] = "تم الإرسال"
    elif cp == "not_sent" and mp == "queued":
        target["merchant_message_status_ar"] = "قيد الإرسال"
    elif log_st == "whatsapp_failed":
        target["merchant_message_status_ar"] = "تعذّر الإرسال"
    else:
        target["merchant_message_status_ar"] = target.get("merchant_status_label_ar") or "—"


def log_row_matches_abandoned_cart(
    lg: Any,
    ac: Any,
    *,
    recovery_key: str = "",
) -> bool:
    sess = _norm(getattr(ac, "recovery_session_id", None))
    zid = _norm(getattr(ac, "zid_cart_id", None))
    ls = _norm(getattr(lg, "session_id", None))
    lc = _norm(getattr(lg, "cart_id", None))
    lrk = _norm(getattr(lg, "recovery_key", None))
    if lrk and recovery_key and lrk == _norm(recovery_key):
        return True
    if sess and ls == sess:
        return True
    if zid and lc == zid:
        return True
    if zid and ls == zid:
        return True
    return False


def _dt_iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    try:
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    except (TypeError, ValueError, AttributeError):
        return None


def build_recovery_message_truth_debug(
    recovery_key: str,
    *,
    dash_store: Optional[Any] = None,
) -> dict[str, Any]:
    from extensions import db
    from models import AbandonedCart, CartRecoveryLog, RecoverySchedule

    rk = _norm(recovery_key)
    out: dict[str, Any] = {
        "recovery_key": rk,
        "cart": None,
        "recovery_schedule": None,
        "cart_recovery_logs": [],
        "message_context": None,
        "derived_cart_status": None,
        "messages_page_status": None,
        "carts_page_status": None,
        "mismatch_detected": False,
        "mismatch_reason": None,
    }
    if not rk:
        out["mismatch_detected"] = True
        out["mismatch_reason"] = "empty_recovery_key"
        return out

    store_slug = ""
    if dash_store is not None:
        store_slug = _norm(getattr(dash_store, "zid_store_id", None))

    carts: list[Any] = []
    try:
        db.create_all()
        q = db.session.query(AbandonedCart)
        if ":" in rk:
            parts = rk.split(":", 2)
            if len(parts) >= 2:
                sess_guess = parts[1]
                q = q.filter(AbandonedCart.recovery_session_id == sess_guess)
        carts = q.limit(12).all()
    except Exception:  # noqa: BLE001
        db.session.rollback()

    ac_hit = None
    for ac in carts:
        if recovery_key_from_parts(
            store_slug=store_slug or _norm(getattr(ac, "zid_store_id", None)),
            session_id=_norm(getattr(ac, "recovery_session_id", None)),
            cart_id=_norm(getattr(ac, "zid_cart_id", None)),
        ) == rk:
            ac_hit = ac
            break
    if ac_hit is None and carts:
        ac_hit = carts[0]

    logs: list[Any] = []
    try:
        logs = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.recovery_key == rk)
            .order_by(CartRecoveryLog.id.desc())
            .limit(40)
            .all()
        )
    except Exception:  # noqa: BLE001
        db.session.rollback()
    if not logs and ac_hit is not None:
        try:
            from main import _cart_recovery_log_filters_for_abandoned_cart  # noqa: PLC0415

            conds = _cart_recovery_log_filters_for_abandoned_cart(ac_hit)
            if conds:
                from sqlalchemy import or_

                logs = (
                    db.session.query(CartRecoveryLog)
                    .filter(or_(*conds))
                    .order_by(CartRecoveryLog.id.desc())
                    .limit(40)
                    .all()
                )
        except Exception:  # noqa: BLE001
            db.session.rollback()

    sched = None
    try:
        sched = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.recovery_key == rk)
            .order_by(RecoverySchedule.id.desc())
            .first()
        )
    except Exception:  # noqa: BLE001
        db.session.rollback()

    log_dicts = []
    latest_sent = None
    for lg in logs:
        ctx = context_from_log_row(lg)
        entry = {
            "id": int(getattr(lg, "id", 0) or 0),
            "status": _norm(getattr(lg, "status", None)),
            "step": getattr(lg, "step", None),
            "sent_at": _dt_iso(getattr(lg, "sent_at", None)),
            "context_status": ctx.get("context_status"),
            "store_slug": _norm(getattr(lg, "store_slug", None)),
            "session_id": _norm(getattr(lg, "session_id", None)),
            "cart_id": _norm(getattr(lg, "cart_id", None)),
            "recovery_key": _norm(getattr(lg, "recovery_key", None)) or ctx.get("recovery_key"),
            "message_preview": (ctx.get("message_body") or "")[:120],
        }
        log_dicts.append(entry)
        if _norm(getattr(lg, "status", None)) in _SENT_LOG_STATUSES:
            if latest_sent is None or int(entry["id"]) > int(getattr(latest_sent, "id", 0) or 0):
                latest_sent = lg

    if ac_hit is not None:
        snap = extract_cart_snapshot(ac_hit)
        out["cart"] = {
            "id": int(getattr(ac_hit, "id", 0) or 0),
            "zid_cart_id": _norm(getattr(ac_hit, "zid_cart_id", None)),
            "recovery_session_id": _norm(getattr(ac_hit, "recovery_session_id", None)),
            "status": _norm(getattr(ac_hit, "status", None)),
            "cart_value": snap.get("cart_value"),
            "reason_tag": snap.get("reason_tag"),
            "items_count": snap.get("items_count"),
            "product_names": snap.get("product_names"),
        }
    if sched is not None:
        out["recovery_schedule"] = {
            "id": int(getattr(sched, "id", 0) or 0),
            "status": _norm(getattr(sched, "status", None)),
            "step": getattr(sched, "step", None),
            "store_slug": _norm(getattr(sched, "store_slug", None)),
            "session_id": _norm(getattr(sched, "session_id", None)),
            "cart_id": _norm(getattr(sched, "cart_id", None)),
        }

    out["cart_recovery_logs"] = log_dicts
    msg_ctx = context_from_log_row(latest_sent) if latest_sent is not None else {}
    if not msg_ctx and log_dicts:
        msg_ctx = context_from_log_row(logs[0])
    out["message_context"] = msg_ctx or None

    phase_key = "pending_send"
    coarse = "pending"
    sent_ct = sum(1 for e in log_dicts if e.get("status") in _SENT_LOG_STATUSES)
    if ac_hit is not None and latest_sent is not None:
        try:
            from main import (  # noqa: PLC0415
                _normal_recovery_coarse_status,
                _normal_recovery_dashboard_phase_key,
            )

            log_ss = frozenset(e["status"] for e in log_dicts if e.get("status"))
            phase_key = _normal_recovery_dashboard_phase_key(
                ac_hit,
                recovery_log_statuses=log_ss,
            )
            coarse = _normal_recovery_coarse_status(phase_key)
        except Exception:  # noqa: BLE001
            pass
    elif sent_ct > 0:
        phase_key = "first_message_sent"
        coarse = "sent"

    log_st = _norm(getattr(latest_sent, "status", None) if latest_sent else "")
    ctx_st = _norm(msg_ctx.get("context_status"))
    mp = derive_messages_page_status(log_st, context_status=ctx_st)
    cp = derive_carts_page_status(
        phase_key=phase_key,
        coarse=coarse,
        sent_ct=sent_ct,
        log_status=log_st,
        context_status=ctx_st,
    )
    out["derived_cart_status"] = coarse
    out["messages_page_status"] = mp
    out["carts_page_status"] = cp
    mismatch, reason = detect_truth_mismatch(
        messages_page_status=mp,
        carts_page_status=cp,
        log_status=log_st,
        context_status=ctx_st,
    )
    out["mismatch_detected"] = mismatch
    out["mismatch_reason"] = reason or None
    return out


__all__ = [
    "CONTEXT_MISSING",
    "CONTEXT_OK",
    "LEGACY_CONTEXT_MISSING",
    "RecoveryMessageContext",
    "build_recovery_message_context",
    "build_recovery_message_truth_debug",
    "classify_context_linkage",
    "context_from_log_row",
    "derive_carts_page_status",
    "derive_messages_page_status",
    "detect_truth_mismatch",
    "enrich_cart_row_truth_fields",
    "extract_cart_snapshot",
    "log_row_matches_abandoned_cart",
    "merge_persist_context",
    "recovery_key_from_parts",
    "resolve_message_body_for_send",
    "serialize_context_json",
]
