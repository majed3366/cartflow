# -*- coding: utf-8 -*-
"""Read-only: why a recovery_key is included or excluded from merchant normal-carts."""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import or_

from extensions import db
from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason, RecoverySchedule


def _norm(s: Any) -> str:
    return str(s or "").strip()


def build_recovery_dashboard_inclusion_truth(
    *,
    recovery_key: str,
    dash_store: Any,
    lifecycle: str = "active",
) -> Dict[str, Any]:
    """
    Mirror GET /api/dashboard/normal-carts inclusion pipeline for one recovery_key.
    """
    from main import (  # noqa: PLC0415
        _normal_recovery_abandoned_scope_filter,
        _normal_recovery_merchant_lightweight_alert_list_for_api,
    )
    from services.cartflow_session_truth import parse_recovery_key
    from services.merchant_cart_presence_trace_v1 import trace_merchant_cart_presence

    rk = _norm(recovery_key)[:512]
    lc_raw = (_norm(lifecycle) or "active").lower()
    out: Dict[str, Any] = {
        "recovery_key": rk or None,
        "lifecycle_tab": lc_raw,
        "dashboard_visible": False,
        "dashboard_exclusion_reason": "recovery_key_missing",
        "abandoned_cart_id": None,
        "store_id": None,
        "row_scope_match": False,
        "excluded_by_filter": False,
        "excluded_by_archive": False,
        "excluded_by_tab": False,
        "excluded_by_group_merge": False,
        "selected_dashboard_row_id": None,
        "abandoned_cart_exists": False,
        "cart_recovery_reason_exists": False,
        "recovery_schedule_row_count": 0,
        "cart_recovery_log_sent_count": 0,
    }
    if not rk:
        return out

    store_slug, session_id = parse_recovery_key(rk)
    store_slug = _norm(store_slug)[:255]
    session_id = _norm(session_id)[:512]

    ac_row: Optional[AbandonedCart] = None
    if session_id:
        ac_row = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == session_id)
            .order_by(AbandonedCart.id.desc())
            .first()
        )
    out["abandoned_cart_exists"] = ac_row is not None
    if ac_row is not None:
        out["abandoned_cart_id"] = int(getattr(ac_row, "id", 0) or 0) or None
        out["store_id"] = getattr(ac_row, "store_id", None)

    if store_slug and session_id:
        rr = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == store_slug,
                CartRecoveryReason.session_id == session_id,
            )
            .first()
        )
        out["cart_recovery_reason_exists"] = rr is not None

    cart_id = _norm(getattr(ac_row, "zid_cart_id", None)) if ac_row else ""
    if store_slug and (session_id or cart_id):
        conds: list[Any] = [RecoverySchedule.store_slug == store_slug]
        if cart_id:
            conds.append(
                or_(
                    RecoverySchedule.session_id == session_id,
                    RecoverySchedule.cart_id == cart_id,
                )
            )
        else:
            conds.append(RecoverySchedule.session_id == session_id)
        try:
            out["recovery_schedule_row_count"] = int(
                db.session.query(RecoverySchedule).filter(*conds).count()
            )
        except Exception:  # noqa: BLE001
            db.session.rollback()

    from services.merchant_dashboard_recovery_resolve_v1 import (  # noqa: PLC0415
        SENT_LOG_STATUSES,
    )

    try:
        q_log = db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.recovery_key == rk,
            CartRecoveryLog.status.in_(tuple(SENT_LOG_STATUSES)),
        )
        out["cart_recovery_log_sent_count"] = int(q_log.count())
    except Exception:  # noqa: BLE001
        db.session.rollback()

    scope = _normal_recovery_abandoned_scope_filter(dash_store)
    if ac_row is not None and scope is not None:
        try:
            scoped = (
                db.session.query(AbandonedCart.id)
                .filter(AbandonedCart.id == int(ac_row.id), scope)
                .first()
            )
            out["row_scope_match"] = scoped is not None
        except Exception:  # noqa: BLE001
            db.session.rollback()
    elif ac_row is not None and scope is None:
        out["row_scope_match"] = True

    trace = trace_merchant_cart_presence(
        rk,
        dash_store=dash_store,
        lifecycle=lc_raw,
        page_limit=50,
        page_offset=0,
    )
    stage = _norm(trace.get("exclusion_stage"))
    out["presence_trace"] = trace

    api_rows: list[dict[str, Any]] = []
    try:
        api_rows, _prof = _normal_recovery_merchant_lightweight_alert_list_for_api(
            50,
            0,
            nr_session=session_id or None,
            nr_cart=cart_id or None,
            lifecycle=lc_raw,
            dash_store=dash_store,
        )
    except Exception:  # noqa: BLE001
        db.session.rollback()

    dash_row: Optional[dict[str, Any]] = None
    for row in api_rows:
        if _norm(row.get("recovery_key")) == rk:
            dash_row = row
            break

    out["dashboard_visible"] = dash_row is not None
    if dash_row is not None:
        out["selected_dashboard_row_id"] = int(
            dash_row.get("merchant_case_row_id") or dash_row.get("id") or 0
        ) or None
        out["dashboard_exclusion_reason"] = None
        return out

    out["excluded_by_tab"] = lc_raw == "active" and stage in (
        "lifecycle",
        "page_slice",
    )
    out["excluded_by_archive"] = stage == "lifecycle" or bool(
        trace.get("lifecycle_excluded")
    )
    out["excluded_by_filter"] = bool(trace.get("lifecycle_excluded"))
    out["excluded_by_group_merge"] = stage in (
        "candidate_and_augment",
        "candidate_or_augment",
        "grouping",
        "pick",
        "classify",
        "loop_cap",
    )

    reason = stage or "not_in_api_rows"
    if stage == "lifecycle":
        reason = "terminal_archived_or_lifecycle_tab"
    elif stage == "pick":
        reason = "group_not_picked"
    elif stage in ("candidate_and_augment", "candidate_or_augment"):
        reason = "not_in_candidate_query"
    elif stage == "no_abandoned_cart":
        reason = "no_abandoned_cart"
    elif stage == "no_sent_log":
        reason = "no_sent_log"
    out["dashboard_exclusion_reason"] = reason
    return out


__all__ = ["build_recovery_dashboard_inclusion_truth"]
