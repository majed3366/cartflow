# -*- coding: utf-8 -*-
"""
Customer Movement Visibility v1 — dashboard presentation only.

Read-model lines for merchant cart rows. Does not change lifecycle, recovery,
purchase truth, or counters.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from services.recovery_truth_timeline_v1 import STATUS_CUSTOMER_REPLY

HEADING_AR = "حركة العميل:"
LINE_PURCHASE_AR = "تم الشراء."
LINE_REPLY_AR = "رد العميل."
LINE_RETURN_AFTER_MESSAGE_AR = "عاد العميل للموقع بعد الرسالة."
LINE_RETURN_CART_AR = "عاد العميل للسلة."
LINE_RETURN_SITE_AR = "عاد العميل للموقع."

RETURN_LOG_STATUSES = frozenset({"returned_to_site", "user_returned"})
LIFECYCLE_RETURN_STATES = frozenset({"return_to_site", "waiting_purchase_window"})


def bulk_movement_snapshot_fields_by_recovery_keys(
    recovery_keys: list[str],
) -> dict[str, dict[str, Any]]:
    """Bounded bulk read from movement_snapshots when table exists (optional source)."""
    keys: list[str] = []
    seen: set[str] = set()
    for raw in recovery_keys:
        rk = _norm(raw)[:512]
        if not rk or rk in seen:
            continue
        seen.add(rk)
        keys.append(rk)
    if not keys:
        return {}
    try:
        from sqlalchemy.exc import SQLAlchemyError

        from extensions import db
        from models import MovementSnapshot
        from schema_movement_snapshot import ensure_movement_snapshot_schema
        from services.customer_movement_snapshot_v1 import (  # noqa: PLC0415
            _snapshot_row_to_dict,
        )

        ensure_movement_snapshot_schema(db)
        rows = (
            db.session.query(MovementSnapshot)
            .filter(MovementSnapshot.recovery_key.in_(keys))
            .limit(max(50, len(keys)))
            .all()
        )
        return {
            str(r.recovery_key): _snapshot_row_to_dict(r)
            for r in rows
            if r.recovery_key
        }
    except Exception:  # noqa: BLE001
        try:
            from extensions import db  # noqa: PLC0415

            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return {}


def _norm(value: Any) -> str:
    return (str(value) if value is not None else "").strip()


def _int_nonneg(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def resolve_customer_movement_line_ar(
    *,
    movement_snapshot: Optional[Mapping[str, Any]] = None,
    purchase_truth: bool = False,
    timeline_statuses: Optional[frozenset[str]] = None,
    log_statuses: Optional[frozenset[str]] = None,
    behavioral: Optional[Mapping[str, Any]] = None,
    sent_count: int = 0,
    lifecycle_state: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve a single movement line for display.

    Priority: purchase > reply > return (with sent-aware copy).
    Returns None when no movement should be shown (omit section).
    """
    snap = movement_snapshot if isinstance(movement_snapshot, Mapping) else {}
    bh = behavioral if isinstance(behavioral, Mapping) else {}
    tl = timeline_statuses or frozenset()
    logs = log_statuses or frozenset()

    purchased = bool(purchase_truth) or bool(snap.get("purchase_detected"))
    if purchased:
        return LINE_PURCHASE_AR

    if bool(snap.get("reply_received")) or STATUS_CUSTOMER_REPLY in tl:
        return LINE_REPLY_AR

    passive_count = _int_nonneg(snap.get("passive_return_visit_count"))
    if not passive_count:
        passive_count = _int_nonneg(bh.get("passive_return_visit_count"))

    has_return = False
    cart_context = False

    if bool(snap.get("returned_to_site")) or passive_count > 0:
        has_return = True
    if logs & RETURN_LOG_STATUSES:
        has_return = True
    if bh.get("user_returned_to_site") is True or bh.get("customer_returned_to_site") is True:
        has_return = True
    if passive_count > 0:
        has_return = True

    ctx = _norm(bh.get("last_passive_return_context")).lower()
    if ctx == "cart":
        cart_context = True
    if bh.get("returned_checkout_page") is not True and ctx == "cart":
        cart_context = True

    lc = _norm(lifecycle_state).lower()
    if lc in LIFECYCLE_RETURN_STATES:
        has_return = True

    if not has_return:
        return None

    sent_proven = int(sent_count or 0) >= 1 or bool(snap.get("provider_sent"))
    if sent_proven:
        return LINE_RETURN_AFTER_MESSAGE_AR

    if cart_context and (
        bh.get("user_returned_to_site") is True
        or bh.get("active_commercial_reengagement") is True
    ):
        return LINE_RETURN_CART_AR

    return LINE_RETURN_SITE_AR


def attach_customer_movement_visibility_v1(
    target: dict[str, Any],
    *,
    recovery_key: str = "",
    movement_snapshot: Optional[Mapping[str, Any]] = None,
    purchase_truth: bool = False,
    timeline_statuses: Optional[frozenset[str]] = None,
    log_statuses: Optional[frozenset[str]] = None,
    behavioral: Optional[Mapping[str, Any]] = None,
    sent_count: int = 0,
    lifecycle_state: Optional[str] = None,
) -> None:
    """Attach movement presentation fields to a dashboard row dict (in-place)."""
    if not isinstance(target, dict):
        return
    line = resolve_customer_movement_line_ar(
        movement_snapshot=movement_snapshot,
        purchase_truth=purchase_truth,
        timeline_statuses=timeline_statuses,
        log_statuses=log_statuses,
        behavioral=behavioral,
        sent_count=sent_count,
        lifecycle_state=lifecycle_state or target.get("customer_lifecycle_state"),
    )
    if not line:
        target.pop("customer_movement_visible", None)
        target.pop("customer_movement_heading_ar", None)
        target.pop("customer_movement_line_ar", None)
        return
    target["customer_movement_visible"] = True
    target["customer_movement_heading_ar"] = HEADING_AR
    target["customer_movement_line_ar"] = line


def _recovery_keys_from_dashboard_rows(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        rk = _norm(row.get("recovery_key"))[:512]
        if not rk or rk in seen:
            continue
        seen.add(rk)
        out.append(rk)
    return out


def _sent_count_hint_from_row(row: Mapping[str, Any]) -> int:
    for key in ("merchant_sent_count", "sent_count", "recovery_sent_count"):
        try:
            n = int(row.get(key) or 0)
            if n > 0:
                return n
        except (TypeError, ValueError):
            continue
    bucket = _norm(row.get("merchant_cart_bucket")).lower()
    primary = _norm(row.get("merchant_cart_primary_bucket")).lower()
    lc = _norm(row.get("customer_lifecycle_state")).lower()
    if lc in LIFECYCLE_RETURN_STATES or bucket == "sent" or primary in (
        "sent",
        "return_to_site",
        "waiting_purchase_window",
    ):
        return 1
    return 0


def enrich_normal_carts_payload_customer_movement_v1(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Post-process snapshot/hot-merge payloads — bounded bulk reads for page rows only.
    """
    if not isinstance(payload, dict):
        return payload
    active = list(payload.get("merchant_carts_page_rows") or [])
    archived = list(payload.get("merchant_archived_carts_page_rows") or [])
    all_rows = active + archived
    rk_keys = _recovery_keys_from_dashboard_rows(all_rows)
    if not rk_keys:
        return payload

    movement_by_rk: dict[str, dict[str, Any]] = {}
    purchase_by_rk: dict[str, bool] = {}
    timeline_by_rk: dict[str, frozenset[str]] = {}
    return_logs_by_rk: dict[str, frozenset[str]] = {}
    behavioral_by_rk: dict[str, dict[str, Any]] = {}

    movement_by_rk = bulk_movement_snapshot_fields_by_recovery_keys(rk_keys)

    try:
        from services.cartflow_purchase_truth import bulk_has_purchase  # noqa: PLC0415

        purchased = bulk_has_purchase(rk_keys)
        purchase_by_rk = {k: bool(purchased.get(k)) for k in rk_keys}
    except Exception:  # noqa: BLE001
        purchase_by_rk = {}

    try:
        from services.recovery_truth_timeline_v1 import bulk_timeline_status_sets  # noqa: PLC0415

        timeline_by_rk = bulk_timeline_status_sets(rk_keys)
    except Exception:  # noqa: BLE001
        timeline_by_rk = {}

    try:
        return_logs_by_rk = _bulk_return_log_statuses_by_recovery_keys(rk_keys)
    except Exception:  # noqa: BLE001
        return_logs_by_rk = {}

    try:
        behavioral_by_rk = _bulk_behavioral_movement_hints_for_rows(all_rows)
    except Exception:  # noqa: BLE001
        behavioral_by_rk = {}

    for row in all_rows:
        if not isinstance(row, dict):
            continue
        rk = _norm(row.get("recovery_key"))[:512]
        if not rk:
            continue
        attach_customer_movement_visibility_v1(
            row,
            recovery_key=rk,
            movement_snapshot=movement_by_rk.get(rk),
            purchase_truth=bool(purchase_by_rk.get(rk)),
            timeline_statuses=timeline_by_rk.get(rk, frozenset()),
            log_statuses=return_logs_by_rk.get(rk, frozenset()),
            behavioral=behavioral_by_rk.get(rk),
            sent_count=_sent_count_hint_from_row(row),
            lifecycle_state=row.get("customer_lifecycle_state"),
        )

    payload["merchant_carts_page_rows"] = active
    payload["merchant_archived_carts_page_rows"] = archived
    return payload


def _bulk_return_log_statuses_by_recovery_keys(
    recovery_keys: list[str],
) -> dict[str, frozenset[str]]:
    keys = [_norm(k)[:512] for k in recovery_keys if _norm(k)]
    if not keys:
        return {}
    try:
        from extensions import db  # noqa: PLC0415
        from models import CartRecoveryLog  # noqa: PLC0415

        rows = (
            db.session.query(CartRecoveryLog.recovery_key, CartRecoveryLog.status)
            .filter(CartRecoveryLog.recovery_key.in_(keys))
            .filter(CartRecoveryLog.status.in_(tuple(RETURN_LOG_STATUSES)))
            .limit(max(50, len(keys) * 4))
            .all()
        )
        out: dict[str, set[str]] = {}
        for rk, st in rows:
            key = _norm(rk)[:512]
            if not key:
                continue
            out.setdefault(key, set()).add(_norm(st).lower())
        return {k: frozenset(v) for k, v in out.items()}
    except Exception:  # noqa: BLE001
        try:
            from extensions import db  # noqa: PLC0415

            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return {}


def _bulk_behavioral_movement_hints_for_rows(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Minimal behavioral hints keyed by recovery_key — one bounded cart query."""
    cart_ids: set[str] = set()
    session_ids: set[str] = set()
    rk_by_cart: dict[str, str] = {}
    rk_by_session: dict[str, str] = {}

    for row in rows:
        if not isinstance(row, Mapping):
            continue
        rk = _norm(row.get("recovery_key"))[:512]
        cid = _norm(row.get("cart_id"))[:255]
        sid = _norm(row.get("session_id"))[:512]
        if rk and cid:
            cart_ids.add(cid)
            rk_by_cart[cid] = rk
        if rk and sid:
            session_ids.add(sid)
            rk_by_session[sid] = rk

    if not cart_ids and not session_ids:
        return {}

    try:
        from sqlalchemy import or_  # noqa: PLC0415

        from extensions import db  # noqa: PLC0415
        from models import AbandonedCart  # noqa: PLC0415
        from services.behavioral_recovery.state_store import (  # noqa: PLC0415
            behavioral_dict_for_abandoned_cart,
        )

        parts: list[Any] = []
        if cart_ids:
            parts.append(AbandonedCart.zid_cart_id.in_(list(cart_ids)))
        if session_ids:
            parts.append(AbandonedCart.recovery_session_id.in_(list(session_ids)))
        if not parts:
            return {}

        ac_rows = (
            db.session.query(AbandonedCart)
            .filter(or_(*parts))
            .limit(max(80, len(cart_ids) + len(session_ids)))
            .all()
        )
        out: dict[str, dict[str, Any]] = {}
        for ac in ac_rows:
            bh = behavioral_dict_for_abandoned_cart(ac)
            cid = _norm(getattr(ac, "zid_cart_id", None))[:255]
            sid = _norm(getattr(ac, "recovery_session_id", None))[:512]
            rk = rk_by_cart.get(cid) or rk_by_session.get(sid)
            if not rk:
                continue
            hint = {
                k: bh.get(k)
                for k in (
                    "user_returned_to_site",
                    "customer_returned_to_site",
                    "passive_return_visit_count",
                    "last_passive_return_context",
                    "returned_checkout_page",
                    "active_commercial_reengagement",
                )
                if k in bh
            }
            if hint:
                out[rk] = hint
        return out
    except Exception:  # noqa: BLE001
        try:
            from extensions import db  # noqa: PLC0415

            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return {}


__all__ = [
    "HEADING_AR",
    "LINE_PURCHASE_AR",
    "LINE_REPLY_AR",
    "LINE_RETURN_AFTER_MESSAGE_AR",
    "LINE_RETURN_CART_AR",
    "LINE_RETURN_SITE_AR",
    "attach_customer_movement_visibility_v1",
    "bulk_movement_snapshot_fields_by_recovery_keys",
    "enrich_normal_carts_payload_customer_movement_v1",
    "resolve_customer_movement_line_ar",
]
