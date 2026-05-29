# -*- coding: utf-8 -*-
"""
Trace inclusion stages for GET /api/dashboard/normal-carts (read-only).

Mirrors: candidate query → augment → group → pick → lifecycle/classify → page slice.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func

from extensions import db
from models import AbandonedCart, CartRecoveryLog

log = logging.getLogger("cartflow")


def _norm(s: Any) -> str:
    return str(s or "").strip()


def _target_ac_ids(
    ac: Optional[AbandonedCart],
    *,
    cart_id: str,
    session_id: str,
) -> set[int]:
    ids: set[int] = set()
    if ac is not None:
        aid = int(getattr(ac, "id", 0) or 0)
        if aid:
            ids.add(aid)
    cid = _norm(cart_id)
    sid = _norm(session_id)
    if cid or sid:
        try:
            q = db.session.query(AbandonedCart)
            if cid:
                for row in q.filter(AbandonedCart.zid_cart_id == cid).all():
                    rid = int(getattr(row, "id", 0) or 0)
                    if rid:
                        ids.add(rid)
            if sid:
                for row in q.filter(AbandonedCart.recovery_session_id == sid).all():
                    rid = int(getattr(row, "id", 0) or 0)
                    if rid:
                        ids.add(rid)
        except Exception:  # noqa: BLE001
            db.session.rollback()
    return ids


def _group_contains_target(grp: list[AbandonedCart], target_ids: set[int]) -> bool:
    for ac in grp:
        if int(getattr(ac, "id", 0) or 0) in target_ids:
            return True
    return False


def _api_row_matches(
    row: dict[str, Any],
    *,
    recovery_key: str,
    cart_id: str,
    session_id: str,
    target_ids: set[int],
) -> bool:
    rk = _norm(recovery_key)
    if rk and _norm(row.get("recovery_key")) == rk:
        return True
    cid = _norm(cart_id)
    if cid:
        for k in ("cart_id", "zid_cart_id", "merchant_cart_id"):
            if _norm(row.get(k)) == cid:
                return True
    sid = _norm(session_id)
    if sid:
        for k in ("session_id", "recovery_session_id"):
            if _norm(row.get(k)) == sid:
                return True
    rid = int(row.get("merchant_case_row_id") or row.get("id") or 0)
    if rid and rid in target_ids:
        return True
    return False


def _exclusion_stage(
    *,
    candidate: bool,
    augmented: bool,
    grouped: bool,
    picked: bool,
    classified: bool,
    returned_in_api: bool,
    in_full_rows: bool,
    lifecycle_excluded: bool,
    loop_cap_excluded: bool,
) -> str:
    if returned_in_api:
        return "included"
    if classified:
        return "page_slice"
    if picked:
        if lifecycle_excluded:
            return "lifecycle"
        if loop_cap_excluded:
            return "loop_cap"
        return "classify"
    if grouped:
        return "pick"
    if in_full_rows:
        return "grouping"
    if augmented or candidate:
        return "candidate_or_augment"
    return "candidate_and_augment"


def trace_merchant_cart_presence(
    recovery_key: str,
    *,
    dash_store: Any,
    page_limit: int = 50,
    page_offset: int = 0,
    lifecycle: str = "active",
) -> dict[str, Any]:
    from main import (  # noqa: PLC0415
        _augment_abandoned_candidates_for_recovery_dashboard,
        _ensure_recovery_visibility_groups_in_pick,
        _merchant_normal_dashboard_batch_reads,
        _merchant_normal_recovery_light_payload_merchant_batch,
        _normal_recovery_abandoned_scope_filter,
        _normal_recovery_cart_activity_rank_map,
        _normal_recovery_cart_group_key,
        _normal_recovery_coarse_status,
        _normal_recovery_dashboard_phase_key_merchant_batch,
        _normal_recovery_group_is_archived_merchant_batch,
        _normal_recovery_merchant_lifecycle_bucket_ok,
        _normal_recovery_behavioral_merge_from_cart_group,
        _normal_recovery_recovery_log_statuses_union_merchant_batch,
        _normal_recovery_merchant_lightweight_alert_list_for_api,
        _vip_pick_priority_cart_groups,
        merchant_group_stale_meta,
        merchant_vip_threshold_int,
    )
    from services.merchant_dashboard_recovery_resolve_v1 import (  # noqa: PLC0415
        find_sent_log_by_recovery_identity,
        sent_logs_for_store,
        store_slug_from_dash,
    )

    rk = _norm(recovery_key)
    lc_raw = (lifecycle or "active").strip().lower()
    if lc_raw not in ("active", "archived", "all"):
        lc_raw = "active"
    po = max(0, int(page_offset or 0))
    pl = max(1, min(250, int(page_limit or 50)))

    out: dict[str, Any] = {
        "recovery_key": rk or None,
        "cart_id": None,
        "session_id": None,
        "log_id": None,
        "candidate": False,
        "augmented": False,
        "grouped": False,
        "picked": False,
        "classified": False,
        "returned_in_api": False,
        "exclusion_stage": "recovery_key_missing",
        "lifecycle": lc_raw,
        "page_limit": pl,
        "page_offset": po,
    }
    if not rk:
        return out

    slug = store_slug_from_dash(dash_store)
    sent_log = find_sent_log_by_recovery_identity(store_slug=slug, recovery_key=rk)
    if sent_log is None:
        try:
            sent_log = (
                db.session.query(CartRecoveryLog)
                .filter(CartRecoveryLog.recovery_key == rk)
                .order_by(CartRecoveryLog.id.desc())
                .first()
            )
        except Exception:  # noqa: BLE001
            db.session.rollback()
    if sent_log is None:
        out["exclusion_stage"] = "no_sent_log"
        return out

    sid = _norm(getattr(sent_log, "session_id", None))
    cid = _norm(getattr(sent_log, "cart_id", None))
    log_id = int(getattr(sent_log, "id", 0) or 0)
    log_slug = _norm(getattr(sent_log, "store_slug", None))
    out["cart_id"] = cid or None
    out["session_id"] = sid or None
    out["log_id"] = log_id or None
    out["log_store_slug"] = log_slug or None
    out["dash_store_slug"] = slug or None

    ac_hit: Optional[AbandonedCart] = None
    if cid:
        ac_hit = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.zid_cart_id == cid)
            .order_by(AbandonedCart.id.desc())
            .first()
        )
    if ac_hit is None and sid:
        ac_hit = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == sid)
            .order_by(AbandonedCart.id.desc())
            .first()
        )
    target_ids = _target_ac_ids(ac_hit, cart_id=cid, session_id=sid)
    if not target_ids:
        out["exclusion_stage"] = "no_abandoned_cart"
        return out

    desired_end = po + pl
    row_cap = 500 if lc_raw == "all" else max(220, min(500, desired_end * 8))
    max_pick = 24 if lc_raw == "all" else max(96, min(160, desired_end * 3))

    if lc_raw == "archived":
        q = db.session.query(AbandonedCart).filter(
            AbandonedCart.status.in_(("abandoned", "recovered"))
        )
    else:
        q = db.session.query(AbandonedCart).filter(AbandonedCart.status == "abandoned")
    nr_scope = _normal_recovery_abandoned_scope_filter(dash_store)
    if nr_scope is not None:
        q = q.filter(nr_scope)
    vip_th = merchant_vip_threshold_int(dash_store)
    if vip_th is not None:
        q = q.filter(func.coalesce(AbandonedCart.cart_value, 0) < float(vip_th))

    candidate_rows = list(q.order_by(AbandonedCart.last_seen_at.desc()).limit(row_cap).all())
    candidate_ids = {int(getattr(r, "id", 0) or 0) for r in candidate_rows}
    in_candidate = bool(target_ids & candidate_ids)
    out["candidate"] = in_candidate

    full_rows = _augment_abandoned_candidates_for_recovery_dashboard(
        list(candidate_rows),
        dash_store=dash_store,
        scope_filter=nr_scope,
    )
    full_ids = {int(getattr(r, "id", 0) or 0) for r in full_rows}
    in_full = bool(target_ids & full_ids)
    out["augmented"] = bool(in_full and not in_candidate)

    groups_by_key: dict[str, list[AbandonedCart]] = defaultdict(list)
    for ac in full_rows:
        groups_by_key[_normal_recovery_cart_group_key(ac)].append(ac)
    target_group_keys: set[str] = set()
    for gk, grp in groups_by_key.items():
        if _group_contains_target(grp, target_ids):
            target_group_keys.add(gk)
    out["grouped"] = bool(target_group_keys)

    slug_for_act = slug
    activity_map = _normal_recovery_cart_activity_rank_map(full_rows, slug_for_act)
    picked_before = _vip_pick_priority_cart_groups(
        full_rows,
        cart_activity_utc=activity_map,
        max_pick_groups=max_pick,
    )
    picked = _ensure_recovery_visibility_groups_in_pick(
        picked_before,
        full_rows,
        store_slug=slug_for_act,
    )
    pick_index: Optional[int] = None
    for i, grp in enumerate(picked):
        if _group_contains_target(grp, target_ids):
            out["picked"] = True
            pick_index = i
            break

    augment_logs = sent_logs_for_store(slug_for_act, limit=100)
    ensure_logs = sent_logs_for_store(slug_for_act, limit=48)
    out["in_augment_sent_window"] = any(
        int(getattr(lg, "id", 0) or 0) == log_id for lg in augment_logs
    )
    out["in_ensure_sent_window"] = any(
        int(getattr(lg, "id", 0) or 0) == log_id for lg in ensure_logs
    )

    batch_reads = _merchant_normal_dashboard_batch_reads(full_rows, dash_store)
    now_utc = datetime.now(timezone.utc)
    classified_hit = False
    lifecycle_excluded = False
    loop_cap_excluded = False
    out_index: Optional[int] = None
    built_rows: list[dict[str, Any]] = []

    for pick_i, grp_sorted in enumerate(picked):
        if not _group_contains_target(grp_sorted, target_ids):
            continue
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
        stale_flag, stale_meta = merchant_group_stale_meta(
            grp_sorted,
            store_slug=slug_for_act,
            activity_map=activity_map,
            coarse=coarse,
            now_utc=now_utc,
            queued_followup_prefetch=batch_reads.queued_followup_prefetch,
            recovery_key=(
                batch_reads.recovery_key_by_ac.get(int(getattr(ac0, "id", 0) or 0)) or ""
            ).strip(),
        )
        if not _normal_recovery_merchant_lifecycle_bucket_ok(
            lc_raw=lc_raw,
            terminal_archived=arch,
            coarse=coarse,
            stale_flag=stale_flag,
            log_statuses=log_u,
        ):
            lifecycle_excluded = True
            continue
        payload = _merchant_normal_recovery_light_payload_merchant_batch(
            grp_sorted,
            dash_store,
            batch_reads,
            coarse=coarse,
            stale_meta=stale_meta,
            archived_group=arch,
            stale_flag=stale_flag,
            now_utc=now_utc,
        )
        classified_hit = True
        out_index = len(built_rows)
        built_rows.append(payload)
        if len(built_rows) >= desired_end:
            break

    if out["picked"] and not classified_hit and not lifecycle_excluded:
        loop_cap_excluded = True

    out["classified"] = classified_hit
    if classified_hit and out_index is not None:
        out["returned_in_api"] = po <= out_index < po + pl
    else:
        out["returned_in_api"] = False

    try:
        api_rows, _prof = _normal_recovery_merchant_lightweight_alert_list_for_api(
            pl,
            po,
            lifecycle=lc_raw,
            dash_store=dash_store,
        )
        for row in api_rows:
            if _api_row_matches(
                row,
                recovery_key=rk,
                cart_id=cid,
                session_id=sid,
                target_ids=target_ids,
            ):
                out["returned_in_api"] = True
                break
        out["api_row_count"] = len(api_rows)
    except Exception as exc:  # noqa: BLE001
        log.warning("cart_presence_trace api replay failed: %s", exc)
        db.session.rollback()

    out["exclusion_stage"] = _exclusion_stage(
        candidate=out["candidate"],
        augmented=out["augmented"],
        grouped=out["grouped"],
        picked=out["picked"],
        classified=out["classified"],
        returned_in_api=out["returned_in_api"],
        in_full_rows=in_full,
        lifecycle_excluded=lifecycle_excluded,
        loop_cap_excluded=loop_cap_excluded,
    )
    if pick_index is not None:
        out["pick_index"] = pick_index
    if out_index is not None:
        out["out_index_before_slice"] = out_index
    return out
