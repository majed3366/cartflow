# -*- coding: utf-8 -*-
"""
Batch-loaded normal-carts dashboard API — eliminates duplicate loads and N+1 on
GET /api/dashboard/normal-carts.

Architecture: Batch Query → Batch Related Data → Pure Projection → JSON
"""
from __future__ import annotations

import contextvars
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart

# Guardrail targets (aligned with operational contracts v1).
NORMAL_CARTS_MAX_BUSINESS_QUERIES_50_ROWS = 40
NORMAL_CARTS_LOCAL_MS_TARGET_50_ROWS = 3000.0

_nc_dash_business_query_count: contextvars.ContextVar[int] = contextvars.ContextVar(
    "nc_dash_business_query_count", default=0
)


def normal_carts_dashboard_query_prof_reset() -> None:
    _nc_dash_business_query_count.set(0)


def normal_carts_dashboard_query_prof_record(n: int = 1) -> None:
    _nc_dash_business_query_count.set(
        int(_nc_dash_business_query_count.get()) + max(0, int(n))
    )


def normal_carts_dashboard_query_prof_snapshot() -> dict[str, int]:
    return {"business_query_count": int(_nc_dash_business_query_count.get())}


def _peek_request_query_count() -> int:
    try:
        from services.db_request_audit import (  # noqa: PLC0415
            audit_enabled,
            peek_request_audit_bucket_for_profile,
        )

        if not audit_enabled():
            return int(normal_carts_dashboard_query_prof_snapshot()["business_query_count"])
        peek = peek_request_audit_bucket_for_profile()
        if peek is None:
            return int(normal_carts_dashboard_query_prof_snapshot()["business_query_count"])
        return int(peek.get("queries") or 0)
    except Exception:  # noqa: BLE001
        return int(normal_carts_dashboard_query_prof_snapshot()["business_query_count"])


@dataclass
class NormalCartsDashboardPerfMeta:
    endpoint_ms: float = 0.0
    projection_ms: float = 0.0
    load_ms: float = 0.0
    query_count: int = 0
    candidate_rows: int = 0
    visible_rows: int = 0
    rows_built: int = 0
    rows_returned: int = 0
    partial: bool = False
    degraded: bool = False
    timeout_stage: str = ""

    def to_api_perf(self) -> dict[str, Any]:
        return {
            "query_count": int(self.query_count),
            "duration_ms": round(float(self.endpoint_ms), 2),
            "candidate_rows": int(self.candidate_rows),
            "visible_rows": int(self.visible_rows),
            "rows_built": int(self.rows_built),
            "rows_returned": int(self.rows_returned),
            "partial": bool(self.partial),
            "degraded": bool(self.degraded),
            "timeout_stage": (self.timeout_stage or "")[:64] or None,
            "projection_ms": round(float(self.projection_ms), 2),
            "load_ms": round(float(self.load_ms), 2),
        }


def build_normal_carts_unified_rows(
    dash_store: Optional[Any],
    *,
    page_limit: int = 50,
    page_offset: int = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], NormalCartsDashboardPerfMeta]:
    """
  Single candidate load + single batch_reads → active and archived row lists.
  """
    from services.dashboard_snapshot_hot_path_guard_v1 import guard_dashboard_hot_path

    guard_dashboard_hot_path("normal_carts_unified_rows", endpoint="normal-carts")
    from main import (  # noqa: PLC0415
        _augment_abandoned_candidates_for_recovery_dashboard,
        _ensure_recovery_visibility_groups_in_pick,
        _merchant_batch_manual_archived,
        _merchant_normal_dashboard_batch_reads,
        _merchant_normal_recovery_light_payload_merchant_batch,
        _normal_recovery_abandoned_scope_filter,
        _normal_recovery_behavioral_merge_from_cart_group,
        _normal_recovery_cart_activity_rank_map,
        _normal_recovery_coarse_status,
        _normal_recovery_dashboard_phase_key_merchant_batch,
        _normal_recovery_group_is_archived_merchant_batch,
        _normal_recovery_merchant_lifecycle_bucket_ok,
        _normal_recovery_recovery_log_statuses_union_merchant_batch,
        _vip_pick_priority_cart_groups,
        abandoned_cart_in_vip_operational_lane,
        merchant_vip_threshold_int,
    )
    from services.dashboard_normal_carts_guard_v1 import (  # noqa: PLC0415
        dashboard_nc_deadline_exceeded,
        dashboard_nc_log_stage,
        dashboard_nc_mark_partial,
        dashboard_nc_partial_active,
    )
    from services.dashboard_normal_carts_perf_v1 import (  # noqa: PLC0415
        dashboard_normal_carts_perf_record_loads,
        dashboard_normal_carts_perf_stage,
    )
    from services.merchant_purchased_cart_dashboard_v1 import (  # noqa: PLC0415
        purchased_terminal_visible_on_active_lifecycle_tab,
    )
    from services.normal_recovery_merchant_stale import merchant_group_stale_meta
    from services.normal_carts_query_profiler import normal_carts_profile_span

    perf = NormalCartsDashboardPerfMeta()
    prof_empty: dict[str, Any] = {
        "carts_count": 0,
        "logs_loaded": 0,
        "reasons_loaded": 0,
        "phones_loaded": 0,
    }

    desired_end = max(0, int(page_offset or 0)) + max(1, int(page_limit or 50))
    po = max(0, int(page_offset or 0))
    pl = max(1, int(page_limit or 50))

    if dash_store is None:
        try:
            from main import _dashboard_recovery_store_row  # noqa: PLC0415

            dash_store = _dashboard_recovery_store_row()
        except Exception:  # noqa: BLE001
            dash_store = None

    t_load = time.perf_counter()
    try:
        q = db.session.query(AbandonedCart).filter(
            AbandonedCart.status.in_(("abandoned", "recovered"))
        )
        _nr_scope = _normal_recovery_abandoned_scope_filter(dash_store)
        if _nr_scope is not None:
            q = q.filter(_nr_scope)
        vip_th = merchant_vip_threshold_int(dash_store)
        if vip_th is not None:
            q = q.filter(func.coalesce(AbandonedCart.cart_value, 0) < float(vip_th))

        row_cap = max(220, min(500, desired_end * 8))
        max_pick = max(96, min(160, desired_end * 3))

        with dashboard_normal_carts_perf_stage("abandoned_candidates"):
            with normal_carts_profile_span("sql:abandoned_cart_candidates_unified"):
                normal_carts_dashboard_query_prof_record(1)
                full_rows = list(
                    q.order_by(AbandonedCart.last_seen_at.desc()).limit(row_cap).all()
                )
            full_rows = _augment_abandoned_candidates_for_recovery_dashboard(
                full_rows,
                dash_store=dash_store,
                scope_filter=_nr_scope,
            )
        perf.candidate_rows = len(full_rows)
        dashboard_normal_carts_perf_record_loads(abandoned_carts=len(full_rows))
        dashboard_nc_log_stage(
            "candidates_loaded",
            candidate_rows=len(full_rows),
            row_cap=int(row_cap),
            max_pick=int(max_pick),
        )

        if not full_rows:
            perf.load_ms = (time.perf_counter() - t_load) * 1000.0
            return [], [], dict(prof_empty), perf

        if dashboard_nc_deadline_exceeded():
            perf.partial = True
            perf.degraded = True
            perf.timeout_stage = "candidates_loaded"
            dashboard_nc_mark_partial("candidates_loaded")
            perf.load_ms = (time.perf_counter() - t_load) * 1000.0
            return [], [], dict(prof_empty), perf

        slug_for_act = (
            (getattr(dash_store, "zid_store_id", None) or "").strip()
            if dash_store is not None
            else ""
        )
        activity_map = _normal_recovery_cart_activity_rank_map(full_rows, slug_for_act)
        picked = _vip_pick_priority_cart_groups(
            full_rows,
            cart_activity_utc=activity_map,
            max_pick_groups=max_pick,
        )
        picked = _ensure_recovery_visibility_groups_in_pick(
            picked,
            full_rows,
            store_slug=slug_for_act,
        )

        if dashboard_nc_deadline_exceeded():
            perf.partial = True
            perf.degraded = True
            perf.timeout_stage = "before_batch_reads"
            dashboard_nc_mark_partial("before_batch_reads")
            perf.load_ms = (time.perf_counter() - t_load) * 1000.0
            return [], [], dict(prof_empty), perf

        with dashboard_normal_carts_perf_stage("batch_reads"):
            batch_reads = _merchant_normal_dashboard_batch_reads(full_rows, dash_store)
        dashboard_nc_log_stage(
            "batch_reads_done",
            logs_loaded=int(getattr(batch_reads, "logs_loaded", 0) or 0),
            picked_groups=len(picked),
        )
        perf.load_ms = (time.perf_counter() - t_load) * 1000.0

        active_out: list[dict[str, Any]] = []
        archived_out: list[dict[str, Any]] = []
        now_utc = datetime.now(timezone.utc)
        npick = len(picked)
        rows_built = 0

        t_proj = time.perf_counter()
        dashboard_nc_log_stage("payload_rows_start", picked_groups=npick)

        for pick_i, grp_sorted in enumerate(picked):
            if dashboard_nc_deadline_exceeded():
                perf.partial = True
                perf.degraded = True
                perf.timeout_stage = "payload_row"
                dashboard_nc_mark_partial("payload_row")
                break
            if len(active_out) >= desired_end and len(archived_out) >= desired_end:
                break

            with normal_carts_profile_span("loop:for_grp_sorted_in_picked"):
                arch = _normal_recovery_group_is_archived_merchant_batch(
                    grp_sorted, batch_reads
                )
                bh = _normal_recovery_behavioral_merge_from_cart_group(grp_sorted)
                log_u = _normal_recovery_recovery_log_statuses_union_merchant_batch(
                    grp_sorted,
                    batch_reads,
                )
                ac0 = grp_sorted[0]
                try:
                    _vip_skip_store = batch_reads.store_row_for_cart(ac0)
                except Exception:  # noqa: BLE001
                    _vip_skip_store = dash_store
                if abandoned_cart_in_vip_operational_lane(ac0, _vip_skip_store):
                    continue

                pk = _normal_recovery_dashboard_phase_key_merchant_batch(
                    ac0,
                    behavioral_override=bh,
                    recovery_log_statuses=log_u,
                    batch=batch_reads,
                )
                coarse = _normal_recovery_coarse_status(pk)
                _rk_stale = (
                    batch_reads.recovery_key_by_ac.get(int(getattr(ac0, "id", 0) or 0))
                    or ""
                ).strip()
                stale_flag, stale_meta = merchant_group_stale_meta(
                    grp_sorted,
                    store_slug=slug_for_act,
                    activity_map=activity_map,
                    coarse=coarse,
                    now_utc=now_utc,
                    queued_followup_prefetch=batch_reads.queued_followup_prefetch,
                    recovery_key=_rk_stale,
                )

                _rk_pt = (
                    batch_reads.recovery_key_by_ac.get(int(getattr(ac0, "id", 0) or 0))
                    or ""
                ).strip()
                _purch_pt = (
                    bool(batch_reads.purchase_truth_by_rk.get(_rk_pt))
                    if _rk_pt
                    else False
                )
                manual_arch = _merchant_batch_manual_archived(ac0, batch_reads)
                purchased_terminal = purchased_terminal_visible_on_active_lifecycle_tab(
                    terminal_archived=arch,
                    ac=ac0,
                    log_statuses=log_u,
                    purchase_truth=_purch_pt,
                    coarse=coarse,
                )

                active_ok = _normal_recovery_merchant_lifecycle_bucket_ok(
                    lc_raw="active",
                    terminal_archived=arch,
                    coarse=coarse,
                    stale_flag=stale_flag,
                    log_statuses=log_u,
                    merchant_manual_archived=manual_arch,
                    purchased_terminal=purchased_terminal,
                )
                archived_ok = _normal_recovery_merchant_lifecycle_bucket_ok(
                    lc_raw="archived",
                    terminal_archived=arch,
                    coarse=coarse,
                    stale_flag=stale_flag,
                    log_statuses=log_u,
                    merchant_manual_archived=manual_arch,
                    purchased_terminal=purchased_terminal,
                )
                if not active_ok and not archived_ok:
                    continue

                with dashboard_normal_carts_perf_stage("payload_row"):
                    row = _merchant_normal_recovery_light_payload_merchant_batch(
                        grp_sorted,
                        dash_store,
                        batch_reads,
                        coarse=coarse,
                        stale_meta=stale_meta,
                        archived_group=arch,
                        stale_flag=stale_flag,
                        now_utc=now_utc,
                        phase_key_pre=pk,
                        coarse_pre=coarse,
                        skip_legacy_lifecycle_truth=True,
                    )
                rows_built += 1
                if active_ok and len(active_out) < desired_end:
                    active_out.append(row)
                if archived_ok and len(archived_out) < desired_end:
                    archived_out.append(row)

        perf.rows_built = rows_built
        perf.visible_rows = len(active_out)
        perf.projection_ms = (time.perf_counter() - t_proj) * 1000.0
        dashboard_nc_log_stage(
            "payload_rows_done",
            rows_built=rows_built,
            loop_iterations=int(npick),
        )

        active_sliced = active_out[po : po + pl]
        archived_sliced = archived_out[po : po + pl]
        prof = {
            "carts_count": len(active_sliced),
            "logs_loaded": int(batch_reads.logs_loaded or 0),
            "reasons_loaded": int(batch_reads.reasons_rows_fetched or 0),
            "phones_loaded": int(batch_reads.phones_loaded or 0),
        }
        perf.rows_returned = len(active_sliced)
        if dashboard_nc_partial_active():
            perf.partial = True
            perf.degraded = True
            if not perf.timeout_stage:
                perf.timeout_stage = "payload_row"

        return active_sliced, archived_sliced, prof, perf

    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        perf.degraded = True
        perf.load_ms = (time.perf_counter() - t_load) * 1000.0
        return [], [], dict(prof_empty), perf


def build_normal_carts_dashboard_api_payload(
    dash_store: Optional[Any],
    *,
    page_limit: int = 50,
    page_offset: int = 0,
    debug_perf: bool = False,
) -> tuple[dict[str, Any], NormalCartsDashboardPerfMeta]:
    """Full JSON body for GET /api/dashboard/normal-carts (batch architecture)."""
    from main import _merchant_dashboard_refresh_state_payload  # noqa: PLC0415
    from services.customer_lifecycle_states_v1 import (  # noqa: PLC0415
        lifecycle_filter_counts_from_rows,
        lifecycle_nav_badge_waiting_count,
    )
    from services.dashboard_normal_carts_perf_v1 import (  # noqa: PLC0415
        dashboard_normal_carts_perf_add_render_payload_ms,
        dashboard_normal_carts_perf_stage,
    )

    t0 = time.perf_counter()
    normal_carts_dashboard_query_prof_reset()

    try:
        from main import _merchant_dashboard_db_ready  # noqa: PLC0415

        _merchant_dashboard_db_ready()
    except Exception:  # noqa: BLE001
        pass

    active_rows, archived_rows, build_prof, perf = build_normal_carts_unified_rows(
        dash_store,
        page_limit=page_limit,
        page_offset=page_offset,
    )

    _render0 = time.perf_counter()
    with dashboard_normal_carts_perf_stage("render_payload"):
        table_rows = list(active_rows[:8])
        cart_filter_counts = lifecycle_filter_counts_from_rows(active_rows)
        refresh_state = _merchant_dashboard_refresh_state_payload(dash_store)
        bucket_counts: dict[str, int] = {}
        for row in active_rows:
            b = str(row.get("customer_lifecycle_state") or "").strip().lower()
            if not b:
                continue
            bucket_counts[b] = int(bucket_counts.get(b) or 0) + 1

        body: dict[str, Any] = {
            "merchant_table_rows": table_rows,
            "merchant_carts_page_rows": active_rows,
            "merchant_archived_carts_page_rows": archived_rows,
            "merchant_archived_cart_count": len(archived_rows),
            "merchant_cart_filter_counts": cart_filter_counts,
            "merchant_nav_badge_abandoned": lifecycle_nav_badge_waiting_count(active_rows),
        }
        body.update(refresh_state)
    try:
        dashboard_normal_carts_perf_add_render_payload_ms(
            (time.perf_counter() - _render0) * 1000.0
        )
    except Exception:  # noqa: BLE001
        pass

    perf.endpoint_ms = (time.perf_counter() - t0) * 1000.0
    perf.query_count = _peek_request_query_count()
    body["_perf"] = perf.to_api_perf()
    if debug_perf:
        body["debug_perf"] = dict(body["_perf"])

    prof_nc = {
        "carts_count": len(active_rows),
        "logs_loaded": int(build_prof.get("logs_loaded") or 0),
        "reasons_loaded": int(build_prof.get("reasons_loaded") or 0),
        "phones_loaded": int(build_prof.get("phones_loaded") or 0),
    }
    return body, prof_nc, perf
