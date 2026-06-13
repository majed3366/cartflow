# -*- coding: utf-8 -*-
"""
Batch-loaded VIP dashboard API — eliminates N+1 on GET /api/dashboard/vip-carts.

Architecture: Batch Query → Batch Related Data → Pure Projection → JSON
"""
from __future__ import annotations

import contextvars
import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import quote

from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason

# Hard guardrail targets (audit v1).
VIP_DASHBOARD_MAX_BUSINESS_QUERIES_50_ROWS = 20
VIP_DASHBOARD_LOCAL_MS_TARGET_50_ROWS = 750.0

_vip_dash_business_query_count: contextvars.ContextVar[int] = contextvars.ContextVar(
    "vip_dash_business_query_count", default=0
)


def vip_dashboard_query_prof_reset() -> None:
    _vip_dash_business_query_count.set(0)


def vip_dashboard_query_prof_record(n: int = 1) -> None:
    _vip_dash_business_query_count.set(
        int(_vip_dash_business_query_count.get()) + max(0, int(n))
    )


def vip_dashboard_query_prof_snapshot() -> dict[str, int]:
    return {"business_query_count": int(_vip_dash_business_query_count.get())}


@dataclass
class VipDashboardBatchContext:
    """Preloaded maps for pure VIP dashboard projection — no per-row DB."""

    dash_store: Any
    store_slug: str
    vip_threshold: Optional[float]
    groups: list[list[AbandonedCart]]
    reason_store_by_session: dict[str, CartRecoveryReason]
    reason_any_by_session: dict[str, CartRecoveryReason]
    sent_phone_by_session: dict[str, str]
    sent_phone_by_cart_id: dict[str, str]
    mem_phone_by_recovery_key: dict[str, str]
    override_contact_message: str
    rows_fetched: int = 0
    reasons_fetched: int = 0
    logs_fetched: int = 0


@dataclass
class VipDashboardPerfMeta:
    endpoint_ms: float = 0.0
    projection_ms: float = 0.0
    query_count: int = 0
    rows_returned: int = 0
    degraded: bool = False


def _strip_phone(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    return s[:100] if s else ""


def _reason_tag_from_batch(ac: AbandonedCart, ctx: VipDashboardBatchContext) -> Optional[str]:
    from main import _vip_reason_tag_from_abandoned_cart  # noqa: PLC0415

    tag = _vip_reason_tag_from_abandoned_cart(ac)
    if tag:
        return tag
    sess = (getattr(ac, "recovery_session_id", None) or "").strip()
    if not sess:
        return None
    row = ctx.reason_store_by_session.get(sess) or ctx.reason_any_by_session.get(sess)
    if row is None:
        return None
    out = (getattr(row, "reason", None) or "").strip()
    return out if out else None


def _recovery_keys_for_ac(ac: AbandonedCart, store_slug: str) -> list[str]:
    from main import _recovery_key_from_store_and_session  # noqa: PLC0415

    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    zid = (getattr(ac, "zid_cart_id", None) or "").strip() or None
    if not sid or not store_slug:
        return []
    keys = [_recovery_key_from_store_and_session(store_slug, sid, zid)]
    rk_legacy = _recovery_key_from_store_and_session(store_slug, sid)
    if rk_legacy not in keys:
        keys.append(rk_legacy)
    return keys


def vip_phone_from_batch(
    ac: AbandonedCart,
    ctx: VipDashboardBatchContext,
) -> str:
    """VIP phone resolution using batch maps only — mirrors dashboard priority, no DB."""
    from main import (  # noqa: PLC0415
        _normalize_customer_phone_for_wa_me,
        _vip_phone_from_abandoned_cart_raw_payload,
    )

    col = _strip_phone(getattr(ac, "customer_phone", None))
    if col:
        return _normalize_customer_phone_for_wa_me(col)

    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    if sid:
        rr = ctx.reason_store_by_session.get(sid) or ctx.reason_any_by_session.get(sid)
        if rr is not None:
            got_crr = _strip_phone(getattr(rr, "customer_phone", None))
            if got_crr:
                return _normalize_customer_phone_for_wa_me(got_crr)

        for rk in _recovery_keys_for_ac(ac, ctx.store_slug):
            mem = _strip_phone(ctx.mem_phone_by_recovery_key.get(rk))
            if mem:
                return _normalize_customer_phone_for_wa_me(mem)

        sent_sess = _strip_phone(ctx.sent_phone_by_session.get(sid))
        if sent_sess:
            return _normalize_customer_phone_for_wa_me(sent_sess)

    zid = (getattr(ac, "zid_cart_id", None) or "").strip()
    if zid:
        sent_cart = _strip_phone(ctx.sent_phone_by_cart_id.get(zid))
        if sent_cart:
            return _normalize_customer_phone_for_wa_me(sent_cart)

    raw_payload_phone = _vip_phone_from_abandoned_cart_raw_payload(ac)
    if raw_payload_phone:
        return _normalize_customer_phone_for_wa_me(raw_payload_phone)

    return ""


def vip_dashboard_row_contract(
    ac: AbandonedCart,
    ctx: VipDashboardBatchContext,
    *,
    avatar_letter: str,
) -> dict[str, Any]:
    """
    Stable VIP dashboard row projection — pure, no DB.
    Includes contract fields + legacy dashboard UI fields for compatibility.
    """
    from datetime import datetime, timezone

    from main import (  # noqa: PLC0415
        _vip_customer_contact_whatsapp_message,
        _vip_lifecycle_effective,
    )
    from services.lifecycle_authority_recovery_v1 import (  # noqa: PLC0415
        attach_merchant_row_lifecycle_authority,
        log_statuses_from_logs,
        normalize_vip_lifecycle_evidence,
    )
    from services.merchant_dashboard_reference_ui import (
        merchant_reason_chip_class_and_label,
        merchant_relative_time_arabic,
    )
    from services.vip_cart import vip_operational_lane_diagnostics

    slug = ctx.store_slug
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    zid = (getattr(ac, "zid_cart_id", None) or "").strip()
    recovery_key = f"{slug}:{sid}" if slug and sid else ""

    phone_digits = vip_phone_from_batch(ac, ctx)
    reason_tag = (_reason_tag_from_batch(ac, ctx) or "other").strip().lower()
    _, reason_label_ar = merchant_reason_chip_class_and_label(reason_tag)

    now_utc = datetime.now(timezone.utc)
    rel = merchant_relative_time_arabic(getattr(ac, "last_seen_at", None), now_utc=now_utc)
    val = float(getattr(ac, "cart_value", None) or 0.0)
    vip_evidence = normalize_vip_lifecycle_evidence(_vip_lifecycle_effective(ac))
    rk_keys = _recovery_keys_for_ac(ac, slug)
    log_ss, sent_n, matched_logs = log_statuses_from_logs(
        getattr(ctx, "logs", None) or [],
        session_id=sid,
        recovery_keys=rk_keys,
    )

    if ctx.override_contact_message and phone_digits:
        contact_msg = ctx.override_contact_message
    else:
        contact_msg = _vip_customer_contact_whatsapp_message(ac)

    href = ""
    if phone_digits and contact_msg:
        href = f"https://wa.me/{phone_digits}?text={quote(contact_msg)}"
    elif phone_digits:
        href = f"https://wa.me/{phone_digits}"

    manual_unavailable_ar = (
        "لا يوجد رقم عميل متاح — تواصل يدوي غير ممكن حتى يتوفر رقم العميل"
    )
    lane = vip_operational_lane_diagnostics(ac.cart_value, ctx.dash_store)

    created_at = getattr(ac, "first_seen_at", None) or getattr(ac, "last_seen_at", None)
    last_activity_at = getattr(ac, "last_seen_at", None)

    row_out: dict[str, Any] = {
        "cart_id": zid or None,
        "recovery_key": recovery_key or None,
        "store_slug": slug or None,
        "customer_name": None,
        "customer_phone": phone_digits or None,
        "cart_total": val,
        "currency": "SAR",
        "is_vip": True,
        "vip_reason": reason_tag,
        "reason_tag": reason_tag,
        "reason_label_ar": reason_label_ar,
        "last_activity_at": (
            last_activity_at.isoformat() if last_activity_at is not None else None
        ),
        "created_at": created_at.isoformat() if created_at is not None else None,
        "alert_status": None,
        "alert_phone": phone_digits or None,
        "manual_contact_available": bool(phone_digits and href),
        "operational_lane": lane.get("vip_operational_lane"),
        "display_status_ar": None,
        "recommended_action_ar": (
            "تواصل يدوي (VIP)" if phone_digits else manual_unavailable_ar
        ),
        "id": getattr(ac, "id", None),
        "avatar_letter": avatar_letter,
        "amount_display": str(int(val)),
        "subtitle_ar": f"{rel} • {reason_label_ar}",
        "contact_href": href,
        "has_phone": bool(phone_digits),
        "manual_contact_unavailable_ar": (
            None if phone_digits and href else manual_unavailable_ar
        ),
        "vip_alert_actionable": True,
        "vip_lifecycle_label_ar": None,
    }

    attach_merchant_row_lifecycle_authority(
        row_out,
        recovery_key=recovery_key,
        sent_count=sent_n,
        attempt_cap=max(2, sent_n or 1),
        log_statuses=log_ss,
        coarse="sent" if sent_n else "pending",
        cart_status=str(getattr(ac, "status", None) or ""),
        is_vip_lane=True,
        has_phone=bool(phone_digits),
        abandoned_cart_id=int(getattr(ac, "id", 0) or 0) or None,
        matched_logs=matched_logs,
        vip_lifecycle_status_evidence=vip_evidence,
    )
    return row_out


def _build_sent_phone_indexes(
    logs: list[Any],
    sent_statuses: frozenset[str],
) -> tuple[dict[str, str], dict[str, str]]:
    from services.merchant_phone_resolution_prefetch_v1 import (  # noqa: PLC0415
        _build_sent_log_phone_index,
    )

    idx = _build_sent_log_phone_index(logs, sent_statuses)
    return idx.by_session, idx.by_cart


def load_vip_dashboard_batch_context(dash_store: Optional[Any]) -> VipDashboardBatchContext:
    """Single-pass batch load for VIP dashboard API."""
    from main import (  # noqa: PLC0415
        VIP_PRIORITY_LC_ACTIVE_SQL,
        _NORMAL_RECOVERY_SENT_LOG_STATUSES,
        _vip_pick_priority_cart_groups,
    )
    from services.merchant_reason_bulk_prefetch_v1 import bulk_load_reason_maps_by_session
    from services.recovery_session_phone import get_recovery_customer_phone
    from services.vip_cart import (
        merchant_vip_threshold_int,
        vip_offer_manual_contact_whatsapp_body,
    )

    slug = ""
    if dash_store is not None:
        z = getattr(dash_store, "zid_store_id", None)
        slug = (str(z).strip()[:255] if z and str(z).strip() else "") or ""

    vip_th = merchant_vip_threshold_int(dash_store)
    empty = VipDashboardBatchContext(
        dash_store=dash_store,
        store_slug=slug,
        vip_threshold=float(vip_th) if vip_th is not None else None,
        groups=[],
        reason_store_by_session={},
        reason_any_by_session={},
        sent_phone_by_session={},
        sent_phone_by_cart_id={},
        mem_phone_by_recovery_key={},
        override_contact_message=vip_offer_manual_contact_whatsapp_body(dash_store) or "",
    )
    if vip_th is None:
        return empty

    q = (
        db.session.query(AbandonedCart)
        .filter(func.coalesce(AbandonedCart.cart_value, 0) >= float(vip_th))
        .filter(AbandonedCart.status == "abandoned")
        .filter(VIP_PRIORITY_LC_ACTIVE_SQL)
    )
    dash_id_raw = getattr(dash_store, "id", None) if dash_store is not None else None
    if dash_id_raw is not None:
        try:
            vid = int(dash_id_raw)
            q = q.filter(
                (AbandonedCart.store_id == vid) | (AbandonedCart.store_id.is_(None))  # type: ignore[union-attr]
            )
        except (TypeError, ValueError):
            pass

    try:
        vip_dashboard_query_prof_record(1)
        full_rows = list(q.order_by(AbandonedCart.last_seen_at.desc()).all())
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        full_rows = []

    groups = _vip_pick_priority_cart_groups(full_rows, max_pick_groups=50)

    sess_keys: set[str] = set()
    cart_ids: set[str] = set()
    mem_keys: set[str] = set()
    for grp in groups:
        ac0 = grp[0]
        sid = (getattr(ac0, "recovery_session_id", None) or "").strip()
        if sid:
            sess_keys.add(sid)
        zid = (getattr(ac0, "zid_cart_id", None) or "").strip()
        if zid:
            cart_ids.add(zid)
        for rk in _recovery_keys_for_ac(ac0, slug):
            mem_keys.add(rk)

    reason_store: dict[str, CartRecoveryReason] = {}
    reason_any: dict[str, CartRecoveryReason] = {}
    reasons_fetched = 0
    if sess_keys:
        vip_dashboard_query_prof_record(1)
        reason_store, reason_any, reasons_fetched, _fb = bulk_load_reason_maps_by_session(
            store_slug=slug,
            session_keys=sess_keys,
        )

    logs: list[Any] = []
    if sess_keys or cart_ids:
        or_parts: list[Any] = []
        if sess_keys:
            or_parts.append(CartRecoveryLog.session_id.in_(list(sess_keys)))
        if cart_ids:
            or_parts.append(CartRecoveryLog.cart_id.in_(list(cart_ids)))
        try:
            vip_dashboard_query_prof_record(1)
            logs = (
                db.session.query(CartRecoveryLog)
                .filter(or_(*or_parts))
                .order_by(CartRecoveryLog.id.desc())
                .limit(500)
                .all()
            )
        except (SQLAlchemyError, OSError):
            db.session.rollback()
            logs = []

    sent_by_sess, sent_by_cart = _build_sent_phone_indexes(
        logs, _NORMAL_RECOVERY_SENT_LOG_STATUSES
    )

    mem_phone: dict[str, str] = {}
    for rk in mem_keys:
        mp = get_recovery_customer_phone(rk)
        if mp:
            mem_phone[rk] = _strip_phone(mp)

    return VipDashboardBatchContext(
        dash_store=dash_store,
        store_slug=slug,
        vip_threshold=float(vip_th),
        groups=groups,
        reason_store_by_session=reason_store,
        reason_any_by_session=reason_any,
        sent_phone_by_session=sent_by_sess,
        sent_phone_by_cart_id=sent_by_cart,
        mem_phone_by_recovery_key=mem_phone,
        override_contact_message=vip_offer_manual_contact_whatsapp_body(dash_store) or "",
        rows_fetched=len(full_rows),
        reasons_fetched=reasons_fetched,
        logs_fetched=len(logs),
    )


def build_vip_dashboard_api_payload(
    dash_store: Optional[Any],
    *,
    debug_perf: bool = False,
) -> tuple[dict[str, Any], VipDashboardPerfMeta]:
    """Batch VIP dashboard JSON body for GET /api/dashboard/vip-carts."""
    from services.merchant_dashboard_reference_ui import merchant_vip_avatar_letter
    from services.merchant_general_settings import merchant_automation_mode
    from services.vip_cart import merchant_vip_threshold_int

    t0 = time.perf_counter()
    vip_dashboard_query_prof_reset()
    ctx = load_vip_dashboard_batch_context(dash_store)
    load_ms = (time.perf_counter() - t0) * 1000

    t_proj = time.perf_counter()
    page_rows: list[dict[str, Any]] = []
    for i, grp in enumerate(ctx.groups[:20]):
        ac = grp[0]
        page_rows.append(
            vip_dashboard_row_contract(
                ac,
                ctx,
                avatar_letter=merchant_vip_avatar_letter(i),
            )
        )
    home_rows = page_rows[:3]
    projection_ms = (time.perf_counter() - t_proj) * 1000

    vip_banner: Optional[dict[str, Any]] = None
    if page_rows:
        v0 = page_rows[0]
        try:
            amt_int = int(float(v0.get("cart_total") or 0))
        except (TypeError, ValueError):
            amt_int = 0
        vip_banner = {
            "amount_line": f"سلة بقيمة {amt_int:,} ريال — {v0.get('subtitle_ar', '')}",
            "contact_href": v0.get("contact_href") or "",
        }

    vip_th = merchant_vip_threshold_int(dash_store)
    vip_threshold_configured = vip_th is not None
    nav_count = len(ctx.groups)

    body: dict[str, Any] = {
        "merchant_vip_banner": vip_banner,
        "merchant_vip_rows": home_rows,
        "merchant_vip_page_rows": page_rows,
        "merchant_nav_badge_vip": nav_count,
        "merchant_automation_mode": merchant_automation_mode(dash_store),
        "merchant_vip_threshold_configured": vip_threshold_configured,
        "merchant_vip_alert_state_ar": (
            f"سلال VIP نشطة: {nav_count}"
            if nav_count
            else (
                "لم يُضبط حد VIP للمتجر — فعّل الحد من الإعدادات"
                if not vip_threshold_configured
                else "لا سلال VIP نشطة تحتاج تدخلك الآن"
            )
        ),
    }

    perf = VipDashboardPerfMeta(
        endpoint_ms=round(load_ms + projection_ms, 2),
        projection_ms=round(projection_ms, 2),
        query_count=int(vip_dashboard_query_prof_snapshot()["business_query_count"]),
        rows_returned=len(page_rows),
        degraded=False,
    )

    if debug_perf:
        body["debug_perf"] = {
            "query_count": perf.query_count,
            "endpoint_ms": perf.endpoint_ms,
            "projection_ms": perf.projection_ms,
            "rows_returned": perf.rows_returned,
            "degraded": perf.degraded,
            "batch_rows_fetched": ctx.rows_fetched,
            "batch_reasons_fetched": ctx.reasons_fetched,
            "batch_logs_fetched": ctx.logs_fetched,
            "load_ms": round(load_ms, 2),
        }

    return body, perf
