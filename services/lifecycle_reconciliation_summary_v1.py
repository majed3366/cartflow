# -*- coding: utf-8 -*-
"""
Lifecycle reconciliation summary v1 — production-safe read-only disagreement scan.

Uses existing lifecycle_truth_consistency_for_row without changing lifecycle logic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryLog, Store
from services.customer_lifecycle_states_v1 import (
    attach_customer_lifecycle_state_v1,
    lifecycle_truth_consistency_for_row,
)
from services.merchant_dashboard_recovery_resolve_v1 import (
    canonical_recovery_keys_for_abandoned_cart,
)
from services.recovery_truth_timeline_v1 import timeline_status_set


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _store_slug_for_cart(ac: AbandonedCart) -> str:
    sid_raw = getattr(ac, "store_id", None)
    if sid_raw is not None:
        try:
            st = db.session.get(Store, int(sid_raw))
            if st is not None:
                slug = str(getattr(st, "zid_store_id", None) or "").strip()
                if slug:
                    return slug[:255]
        except Exception:  # noqa: BLE001
            db.session.rollback()
    return ""


def _build_row_for_cart(ac: AbandonedCart) -> dict[str, Any]:
    store_slug = _store_slug_for_cart(ac)
    keys = canonical_recovery_keys_for_abandoned_cart(ac, store_slug=store_slug)
    rk = keys[0] if keys else ""
    row: dict[str, Any] = {
        "recovery_key": rk[:120],
        "store_slug": store_slug[:64],
    }
    if not rk:
        return row
    log_statuses: set[str] = set()
    sent_count = 0
    try:
        logs = (
            db.session.query(CartRecoveryLog.status)
            .filter(CartRecoveryLog.recovery_key == rk)
            .order_by(CartRecoveryLog.id.desc())
            .limit(40)
            .all()
        )
        for (st,) in logs:
            s = str(st or "").strip().lower()
            if s:
                log_statuses.add(s)
            if s in ("mock_sent", "sent_real", "provider_sent", "provider_queued"):
                sent_count += 1
    except SQLAlchemyError:
        db.session.rollback()

    purchase_truth = False
    try:
        from services.cartflow_session_truth import has_conversion_truth

        purchase_truth = bool(has_conversion_truth(rk))
    except Exception:  # noqa: BLE001
        purchase_truth = False

    tl_statuses = timeline_status_set(rk)
    attach_customer_lifecycle_state_v1(
        row,
        recovery_key=rk,
        phase_key=str(getattr(ac, "phase_key", "") or ""),
        coarse=str(getattr(ac, "coarse", "") or ""),
        sent_count=sent_count,
        log_statuses=frozenset(log_statuses),
        purchase_truth=purchase_truth,
        cart_status=str(getattr(ac, "status", "") or ""),
        is_vip_lane=bool(getattr(ac, "vip_mode", False)),
        has_phone=bool(getattr(ac, "customer_phone", None)),
        abandoned_cart_id=int(ac.id) if ac.id else None,
        timeline_statuses=tl_statuses,
    )
    return row


def build_lifecycle_reconciliation_summary(
    *,
    sample_limit: int = 100,
    disagreement_sample_limit: int = 10,
) -> dict[str, Any]:
    """Scan recent carts for lifecycle/dashboard disagreements."""
    scan_limit = max(10, min(int(sample_limit or 100), 300))
    disagree_limit = max(1, min(int(disagreement_sample_limit or 10), 25))

    out: dict[str, Any] = {
        "generated_at": _utc_now_iso(),
        "disagreements_present": False,
        "disagreement_count": 0,
        "sampled_count": 0,
        "consistent_count": 0,
        "severity": "ok",
        "summary": "No lifecycle/dashboard disagreements in sampled carts.",
        "disagreement_reasons": {},
        "samples": [],
        "error": None,
    }

    try:
        db.create_all()
        carts = (
            db.session.query(AbandonedCart)
            .order_by(AbandonedCart.last_seen_at.desc())
            .limit(scan_limit)
            .all()
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        out["error"] = str(exc)[:200]
        out["severity"] = "critical"
        out["summary"] = "Lifecycle reconciliation unavailable due to database error."
        return out

    reason_counts: dict[str, int] = {}
    disagree_samples: list[dict[str, Any]] = []
    consistent = 0

    for ac in carts:
        if ac is None:
            continue
        row = _build_row_for_cart(ac)
        if not row.get("recovery_key"):
            consistent += 1
            continue
        ok, reason = lifecycle_truth_consistency_for_row(row)
        if ok:
            consistent += 1
            continue
        reason_key = str(reason or "unknown")[:120]
        reason_counts[reason_key] = reason_counts.get(reason_key, 0) + 1
        if len(disagree_samples) < disagree_limit:
            disagree_samples.append(
                {
                    "recovery_key": row.get("recovery_key"),
                    "store_slug": row.get("store_slug"),
                    "customer_lifecycle_state": row.get("customer_lifecycle_state"),
                    "merchant_cart_bucket": row.get("merchant_cart_bucket"),
                    "reason": reason_key,
                }
            )

    sampled = len(carts)
    disagree_n = sampled - consistent
    out["sampled_count"] = sampled
    out["consistent_count"] = consistent
    out["disagreement_count"] = disagree_n
    out["disagreements_present"] = disagree_n > 0
    out["disagreement_reasons"] = reason_counts
    out["samples"] = disagree_samples

    if disagree_n > 0:
        out["severity"] = "warning" if disagree_n < 5 else "critical"
        top_reason = max(reason_counts, key=reason_counts.get) if reason_counts else "unknown"
        out["summary"] = (
            f"Lifecycle/dashboard disagreements in {disagree_n}/{sampled} sampled cart(s); "
            f"top reason: {top_reason}."
        )

    return out


__all__ = ["build_lifecycle_reconciliation_summary"]
