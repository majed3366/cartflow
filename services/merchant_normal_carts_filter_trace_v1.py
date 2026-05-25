# -*- coding: utf-8 -*-
"""Read-only step counts for merchant normal-carts filter pipeline."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional


def trace_merchant_normal_carts_filters(
    *,
    dash_store: Optional[Any] = None,
    target_cart_id: Optional[str] = None,
    lifecycle: str = "active",
    page_limit: int = 50,
    page_offset: int = 0,
) -> dict[str, Any]:
    """
    Mirror GET /api/dashboard/normal-carts SQL + grouping filters without mutating data.
    """
    from sqlalchemy import func

    from extensions import db
    from models import AbandonedCart
    from main import (  # noqa: PLC0415
        _normal_recovery_abandoned_scope_filter,
        _normal_recovery_behavioral_merge_from_cart_group,
        _normal_recovery_coarse_status,
        _normal_recovery_dashboard_phase_key_merchant_batch,
        _normal_recovery_group_is_archived_merchant_batch,
        _normal_recovery_recovery_log_statuses_union_merchant_batch,
        _merchant_normal_dashboard_batch_reads,
        _normal_recovery_cart_activity_rank_map,
        _vip_pick_priority_cart_groups,
        merchant_vip_threshold_int,
    )
    from services.normal_recovery_merchant_stale import merchant_group_stale_meta

    tid = (target_cart_id or "").strip()[:255]
    lc_raw = (lifecycle or "active").strip().lower()
    if lc_raw not in ("active", "archived", "all"):
        lc_raw = "active"

    def _has_target(rows: list[Any]) -> bool:
        if not tid:
            return False
        for ac in rows:
            if (getattr(ac, "zid_cart_id", None) or "").strip() == tid:
                return True
        return False

    def _has_target_in_groups(groups: list[list[Any]]) -> bool:
        if not tid:
            return False
        for grp in groups:
            for ac in grp:
                if (getattr(ac, "zid_cart_id", None) or "").strip() == tid:
                    return True
        return False

    before_filters = (
        db.session.query(AbandonedCart).count()
        if tid
        else None
    )

    q_status = db.session.query(AbandonedCart).filter(AbandonedCart.status == "abandoned")
    after_status_rows = list(q_status.limit(500).all())
    after_status = len(after_status_rows)

    q_store = db.session.query(AbandonedCart).filter(AbandonedCart.status == "abandoned")
    _nr_scope = _normal_recovery_abandoned_scope_filter(dash_store)
    if _nr_scope is not None:
        q_store = q_store.filter(_nr_scope)
    after_store_rows = list(q_store.order_by(AbandonedCart.last_seen_at.desc()).limit(500).all())
    after_store = len(after_store_rows)

    vip_th = merchant_vip_threshold_int(dash_store)
    q_vip = q_store
    if vip_th is not None:
        q_vip = q_vip.filter(func.coalesce(AbandonedCart.cart_value, 0) < float(vip_th))
    desired_end = max(0, int(page_offset or 0)) + max(1, int(page_limit or 50))
    row_cap = 500 if lc_raw == "all" else max(220, min(500, desired_end * 8))
    max_pick = 24 if lc_raw == "all" else max(96, min(160, desired_end * 3))
    after_vip_rows = list(
        q_vip.order_by(AbandonedCart.last_seen_at.desc()).limit(row_cap).all()
    )
    after_vip = len(after_vip_rows)

    slug_for_act = (
        (getattr(dash_store, "zid_store_id", None) or "").strip()
        if dash_store is not None
        else ""
    )
    activity_map = _normal_recovery_cart_activity_rank_map(after_vip_rows, slug_for_act)
    picked = _vip_pick_priority_cart_groups(
        after_vip_rows,
        cart_activity_utc=activity_map,
        max_pick_groups=max_pick,
    )
    after_grouping = len(picked)

    batch_reads = _merchant_normal_dashboard_batch_reads(after_vip_rows, dash_store)
    now_utc = datetime.now(timezone.utc)

    def _lifecycle_bucket_ok(*, archived: bool, coarse: str, stale_flag: bool) -> bool:
        if lc_raw == "all":
            return True
        in_history = archived or (stale_flag and coarse in ("pending", "sent"))
        operational_active = (not archived) and (not stale_flag)
        if lc_raw == "active":
            return operational_active
        if lc_raw == "archived":
            return in_history
        return True

    lifecycle_pass = 0
    drop_reasons: dict[str, int] = defaultdict(int)
    target_trace: dict[str, Any] = {"cart_id": tid or None}

    for grp_sorted in picked:
        arch = _normal_recovery_group_is_archived_merchant_batch(grp_sorted, batch_reads)
        bh = _normal_recovery_behavioral_merge_from_cart_group(grp_sorted)
        log_u = _normal_recovery_recovery_log_statuses_union_merchant_batch(
            grp_sorted, batch_reads
        )
        ac0 = grp_sorted[0]
        pk = _normal_recovery_dashboard_phase_key_merchant_batch(
            ac0,
            behavioral_override=bh,
            recovery_log_statuses=log_u,
            batch=batch_reads,
        )
        coarse = _normal_recovery_coarse_status(pk)
        stale_flag, _sm = merchant_group_stale_meta(
            grp_sorted,
            store_slug=slug_for_act,
            activity_map=activity_map,
            coarse=coarse,
            now_utc=now_utc,
        )
        if tid and any(
            (getattr(ac, "zid_cart_id", None) or "").strip() == tid for ac in grp_sorted
        ):
            target_trace = {
                "cart_id": tid,
                "phase_key": pk,
                "coarse": coarse,
                "archived_group": arch,
                "stale_flag": stale_flag,
                "lifecycle_bucket_ok": _lifecycle_bucket_ok(
                    archived=arch, coarse=coarse, stale_flag=stale_flag
                ),
                "in_after_vip_rows": True,
                "in_picked_groups": True,
            }
        if not _lifecycle_bucket_ok(
            archived=arch, coarse=coarse, stale_flag=stale_flag
        ):
            if arch:
                drop_reasons["archived_group"] += 1
            elif stale_flag:
                drop_reasons["stale_flag"] += 1
            else:
                drop_reasons["lifecycle_other"] += 1
            continue
        lifecycle_pass += 1

    after_lifecycle = lifecycle_pass
    final_rows = min(after_lifecycle, max(0, desired_end - max(0, int(page_offset or 0))))

    return {
        "target_cart_id": tid or None,
        "lifecycle_tab": lc_raw,
        "before_filters": before_filters,
        "after_status": after_status,
        "after_store": after_store,
        "after_vip": after_vip,
        "after_grouping": after_grouping,
        "after_lifecycle": after_lifecycle,
        "final_rows": final_rows,
        "includes_target_cart_id": {
            "after_store": _has_target(after_store_rows),
            "after_vip": _has_target(after_vip_rows),
            "after_grouping": _has_target_in_groups(picked),
            "after_lifecycle": bool(
                target_trace.get("lifecycle_bucket_ok")
            ),
        },
        "target_group_trace": target_trace,
        "lifecycle_drop_reasons": dict(drop_reasons),
        "row_cap": row_cap,
        "max_pick_groups": max_pick,
    }


__all__ = ["trace_merchant_normal_carts_filters"]
