# -*- coding: utf-8 -*-
"""
Canonical merchant dashboard cart counter totals (store-level).

One Source Of Truth Per Question — counters answer store-wide merchant questions,
not page-window slices. Uses existing row projection + lifecycle attach (read-only).

Counter definitions (merchant meaning):
- active_total: non-VIP carts on the active dashboard (not lifecycle-archived/completed).
- waiting_total: active carts whose lifecycle bucket is waiting (active / waiting_first_send).
- sent_total: active carts in the sent lifecycle bucket.
- engaged_total: active carts in the attention bucket (reply / engaged / intervention).
- completed_total: carts on the completed page (same rule as completed tab JS).
- archived_total: carts in the archived dashboard bucket (terminal / manual archive).
- no_phone_total: active carts without verified phone before first send (pre-send only).
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart
from services.customer_lifecycle_states_v1 import (
    LIFECYCLE_TRUTH_UNAVAILABLE_STATE,
    STATE_ARCHIVED,
    STATE_COMPLETED,
    UI_FILTER_ATTENTION,
    UI_FILTER_SENT,
    UI_FILTER_WAITING,
    lifecycle_state_to_filter_bucket,
)
from services.dashboard_completed_row_semantics_v1 import is_completed_dashboard_row
from services.merchant_dashboard_recovery_resolve_v1 import SENT_LOG_STATUSES

log = logging.getLogger(__name__)

COUNTER_PARITY_VERSION = "v1"
COUNTER_QUERY_SCOPE = "store_total"
COUNTER_SOURCE_CANONICAL = "canonical"

_DEFAULT_ROW_CAP = 2500
_DEFAULT_MAX_PICK = 2500


def _store_counter_row_cap() -> int:
    raw = (os.environ.get("CARTFLOW_STORE_COUNTER_ROW_CAP") or "").strip()
    if raw:
        try:
            return max(500, min(10000, int(raw)))
        except (TypeError, ValueError):
            pass
    return _DEFAULT_ROW_CAP


def _store_counter_max_pick() -> int:
    raw = (os.environ.get("CARTFLOW_STORE_COUNTER_MAX_PICK") or "").strip()
    if raw:
        try:
            return max(200, min(10000, int(raw)))
        except (TypeError, ValueError):
            pass
    return _DEFAULT_MAX_PICK


@dataclass
class MerchantCartCounterTotals:
    active_total: int = 0
    waiting_total: int = 0
    sent_total: int = 0
    engaged_total: int = 0
    completed_total: int = 0
    archived_total: int = 0
    no_phone_total: int = 0
    partial: bool = False
    candidate_rows: int = 0
    groups_scanned: int = 0
    groups_skipped_vip: int = 0
    row_cap: int = 0
    max_pick: int = 0

    def to_counts_dict(self) -> dict[str, int]:
        return {
            "active_total": int(self.active_total),
            "waiting_total": int(self.waiting_total),
            "sent_total": int(self.sent_total),
            "engaged_total": int(self.engaged_total),
            "completed_total": int(self.completed_total),
            "archived_total": int(self.archived_total),
            "no_phone_total": int(self.no_phone_total),
        }

    def to_legacy_filter_counts(self) -> dict[str, int]:
        """Filter-bar compatible keys backed by store totals."""
        return {
            "all": int(self.active_total),
            "waiting": int(self.waiting_total),
            "sent": int(self.sent_total),
            "attention": int(self.engaged_total),
            "recovered": int(self.completed_total),
            "nophone": int(self.no_phone_total),
        }


@dataclass
class MerchantCartCounterPayload:
    counts: MerchantCartCounterTotals = field(default_factory=MerchantCartCounterTotals)
    source: str = COUNTER_SOURCE_CANONICAL
    generated_at: str = ""
    counter_source: str = COUNTER_SOURCE_CANONICAL
    counter_generated_at: str = ""
    counter_snapshot_age_seconds: Optional[float] = None
    counter_snapshot_stale: bool = False
    counter_query_scope: str = COUNTER_QUERY_SCOPE
    counter_parity_version: str = COUNTER_PARITY_VERSION
    store_slug: str = ""

    def to_api_payload(self) -> dict[str, Any]:
        gen = self.generated_at or datetime.now(timezone.utc).isoformat()
        health: dict[str, Any] = {
            "counter_source": self.counter_source,
            "counter_generated_at": self.counter_generated_at or gen,
            "counter_snapshot_stale": bool(self.counter_snapshot_stale),
            "counter_query_scope": self.counter_query_scope,
            "counter_parity_version": self.counter_parity_version,
            "partial": bool(self.counts.partial),
            "candidate_rows": int(self.counts.candidate_rows),
            "groups_scanned": int(self.counts.groups_scanned),
            "row_cap": int(self.counts.row_cap),
            "max_pick": int(self.counts.max_pick),
        }
        if self.counter_snapshot_age_seconds is not None:
            health["counter_snapshot_age_seconds"] = round(
                float(self.counter_snapshot_age_seconds), 1
            )
        return {
            "merchant_store_cart_counts": self.counts.to_counts_dict(),
            "merchant_cart_filter_counts": self.counts.to_legacy_filter_counts(),
            "merchant_nav_badge_abandoned": int(self.counts.waiting_total),
            "merchant_archived_cart_count": int(self.counts.archived_total),
            "merchant_counter_health": health,
            "merchant_counter_generated_at": gen,
            "merchant_counter_source": self.source,
        }


def _is_no_phone_pre_send_row(row: Mapping[str, Any], *, log_has_sent: bool) -> bool:
    if log_has_sent:
        return False
    if row.get("merchant_has_customer_phone") is True:
        return False
    if row.get("merchant_has_customer_phone") is False:
        return True
    return False


def _row_identity_key(row: Mapping[str, Any]) -> str:
    rk = str(row.get("recovery_key") or "").strip()
    if rk:
        return rk
    rid = row.get("merchant_case_row_id")
    if rid is not None:
        return f"row:{rid}"
    sid = str(row.get("session_id") or "").strip()
    if sid:
        return f"session:{sid}"
    return ""


def build_merchant_cart_counter_totals(
    dash_store: Optional[Any],
    *,
    source: str = COUNTER_SOURCE_CANONICAL,
    snapshot_generated_at: Optional[datetime] = None,
    snapshot_stale: bool = False,
) -> MerchantCartCounterPayload:
    """
    Store-level cart counter totals using the same inclusion + lifecycle rules as
    the normal-carts dashboard row builder (higher scan caps, no page slice).
    """
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
    from services.merchant_purchased_cart_dashboard_v1 import (  # noqa: PLC0415
        purchased_terminal_visible_on_active_lifecycle_tab,
    )
    from services.normal_recovery_merchant_stale import merchant_group_stale_meta

    t0 = time.perf_counter()
    totals = MerchantCartCounterTotals()
    row_cap = _store_counter_row_cap()
    max_pick = _store_counter_max_pick()
    totals.row_cap = row_cap
    totals.max_pick = max_pick

    store_slug = ""
    if dash_store is not None:
        store_slug = str(getattr(dash_store, "zid_store_id", None) or "").strip()

    if dash_store is None:
        try:
            from main import _dashboard_recovery_store_row  # noqa: PLC0415

            dash_store = _dashboard_recovery_store_row()
            store_slug = str(getattr(dash_store, "zid_store_id", None) or "").strip()
        except Exception:  # noqa: BLE001
            dash_store = None

    generated_at = datetime.now(timezone.utc).isoformat()
    out = MerchantCartCounterPayload(
        counts=totals,
        source=source,
        generated_at=generated_at,
        counter_source=source,
        counter_generated_at=generated_at,
        counter_snapshot_stale=bool(snapshot_stale),
        store_slug=store_slug,
    )

    if dash_store is None:
        emit_counter_totals_audit_logs(out, merchant=store_slug or "-")
        return out

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

        full_rows = list(
            q.order_by(AbandonedCart.last_seen_at.desc()).limit(row_cap).all()
        )
        full_rows = _augment_abandoned_candidates_for_recovery_dashboard(
            full_rows,
            dash_store=dash_store,
            scope_filter=_nr_scope,
        )
        totals.candidate_rows = len(full_rows)
        if len(full_rows) >= row_cap:
            totals.partial = True

        if not full_rows:
            emit_counter_totals_audit_logs(out, merchant=store_slug or "-")
            return out

        slug_for_act = store_slug
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
        if len(picked) >= max_pick:
            totals.partial = True

        batch_reads = _merchant_normal_dashboard_batch_reads(full_rows, dash_store)
        now_utc = datetime.now(timezone.utc)
        completed_seen: set[str] = set()

        for grp_sorted in picked:
            totals.groups_scanned += 1
            arch = _normal_recovery_group_is_archived_merchant_batch(grp_sorted, batch_reads)
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
                totals.groups_skipped_vip += 1
                continue

            pk = _normal_recovery_dashboard_phase_key_merchant_batch(
                ac0,
                behavioral_override=bh,
                recovery_log_statuses=log_u,
                batch=batch_reads,
            )
            coarse = _normal_recovery_coarse_status(pk)
            _rk_stale = (
                batch_reads.recovery_key_by_ac.get(int(getattr(ac0, "id", 0) or 0)) or ""
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
                batch_reads.recovery_key_by_ac.get(int(getattr(ac0, "id", 0) or 0)) or ""
            ).strip()
            _purch_pt = (
                bool(batch_reads.purchase_truth_by_rk.get(_rk_pt)) if _rk_pt else False
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
                if bool(log_u & SENT_LOG_STATUSES) and not manual_arch:
                    active_ok = True
                else:
                    continue

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
            log_has_sent = bool(log_u & SENT_LOG_STATUSES)

            if archived_ok:
                totals.archived_total += 1

            if active_ok:
                sk = str(row.get("customer_lifecycle_state") or "").strip().lower()
                if sk and sk != LIFECYCLE_TRUTH_UNAVAILABLE_STATE:
                    if sk not in (STATE_ARCHIVED, STATE_COMPLETED):
                        totals.active_total += 1
                        bucket = lifecycle_state_to_filter_bucket(sk)
                        if bucket == UI_FILTER_WAITING:
                            totals.waiting_total += 1
                        elif bucket == UI_FILTER_SENT:
                            totals.sent_total += 1
                        elif bucket == UI_FILTER_ATTENTION:
                            totals.engaged_total += 1
                if _is_no_phone_pre_send_row(row, log_has_sent=log_has_sent):
                    totals.no_phone_total += 1

            ident = _row_identity_key(row)
            if is_completed_dashboard_row(row):
                if not ident or ident not in completed_seen:
                    if ident:
                        completed_seen.add(ident)
                    totals.completed_total += 1

        if snapshot_generated_at is not None:
            age = (datetime.now(timezone.utc) - snapshot_generated_at).total_seconds()
            out.counter_snapshot_age_seconds = max(0.0, float(age))

    except (SQLAlchemyError, OSError, TypeError, ValueError) as exc:
        db.session.rollback()
        totals.partial = True
        log.warning("build_merchant_cart_counter_totals failed: %s", exc)

    emit_counter_totals_audit_logs(out, merchant=store_slug or "-")
    _ = t0  # reserved for future perf metrics
    return out


def apply_counter_health_from_snapshot_meta(
    payload: dict[str, Any],
    *,
    snapshot_meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Annotate counter health when serving persisted snapshot payloads."""
    if not isinstance(payload, dict):
        return payload
    health = dict(payload.get("merchant_counter_health") or {})
    snap = snapshot_meta or payload.get("_snapshot") or {}
    stale = bool(snap.get("stale"))
    health["counter_snapshot_stale"] = stale
    health["counter_source"] = "snapshot"
    gen_raw = health.get("counter_generated_at") or payload.get(
        "merchant_counter_generated_at"
    )
    if gen_raw and stale:
        try:
            gen_dt = datetime.fromisoformat(str(gen_raw).replace("Z", "+00:00"))
            if gen_dt.tzinfo is None:
                gen_dt = gen_dt.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - gen_dt).total_seconds()
            health["counter_snapshot_age_seconds"] = round(max(0.0, age), 1)
        except (TypeError, ValueError):
            pass
    payload["merchant_counter_health"] = health
    payload["merchant_counter_source"] = "snapshot"
    return payload


def visible_page_counts_from_rows(
    active_rows: list[dict[str, Any]],
    *,
    archived_rows: Optional[list[dict[str, Any]]] = None,
) -> dict[str, int]:
    """Page-window counts for audit only — not merchant-facing store totals."""
    from services.customer_lifecycle_states_v1 import (  # noqa: PLC0415
        lifecycle_filter_counts_from_rows,
        lifecycle_nav_badge_waiting_count,
    )
    from services.dashboard_completed_row_semantics_v1 import (  # noqa: PLC0415
        is_completed_dashboard_row,
    )

    fc = lifecycle_filter_counts_from_rows(active_rows)
    completed_seen: set[str] = set()
    completed_n = 0
    for pool in (archived_rows or [], active_rows):
        for row in pool or []:
            if not is_completed_dashboard_row(row):
                continue
            ident = _row_identity_key(row)
            if ident and ident in completed_seen:
                continue
            if ident:
                completed_seen.add(ident)
            completed_n += 1
    return {
        "all": int(fc.get("all") or 0),
        "waiting": int(lifecycle_nav_badge_waiting_count(active_rows)),
        "sent": int(fc.get("sent") or 0),
        "attention": int(fc.get("attention") or 0),
        "recovered": completed_n,
        "nophone": int(fc.get("nophone") or 0),
        "archived": len(archived_rows or []),
    }


def emit_counter_totals_audit_logs(
    counter_payload: MerchantCartCounterPayload,
    *,
    merchant: str,
) -> None:
    c = counter_payload.counts
    try:
        log.info(
            "[COUNTER TOTALS AUDIT] merchant=%s source=%s scope=%s "
            "active_total=%s waiting_total=%s sent_total=%s engaged_total=%s "
            "completed_total=%s archived_total=%s no_phone_total=%s "
            "snapshot_stale=%s partial=%s parity_version=%s",
            merchant[:64] or "-",
            counter_payload.counter_source,
            COUNTER_QUERY_SCOPE,
            c.active_total,
            c.waiting_total,
            c.sent_total,
            c.engaged_total,
            c.completed_total,
            c.archived_total,
            c.no_phone_total,
            counter_payload.counter_snapshot_stale,
            c.partial,
            COUNTER_PARITY_VERSION,
        )
    except Exception:  # noqa: BLE001
        pass


def emit_counter_page_audit_logs(
    *,
    merchant: str,
    visible_page_counts: dict[str, int],
    visible_page_rows: int,
) -> None:
    try:
        log.info(
            "[COUNTER PAGE AUDIT] merchant=%s visible_page_rows=%s "
            "page_waiting=%s page_sent=%s page_engaged=%s page_completed=%s "
            "page_archived=%s page_all=%s",
            merchant[:64] or "-",
            int(visible_page_rows),
            int(visible_page_counts.get("waiting") or 0),
            int(visible_page_counts.get("sent") or 0),
            int(visible_page_counts.get("attention") or 0),
            int(visible_page_counts.get("recovered") or 0),
            int(visible_page_counts.get("archived") or 0),
            int(visible_page_counts.get("all") or 0),
        )
    except Exception:  # noqa: BLE001
        pass


__all__ = [
    "COUNTER_PARITY_VERSION",
    "COUNTER_QUERY_SCOPE",
    "COUNTER_SOURCE_CANONICAL",
    "MerchantCartCounterPayload",
    "MerchantCartCounterTotals",
    "apply_counter_health_from_snapshot_meta",
    "build_merchant_cart_counter_totals",
    "emit_counter_page_audit_logs",
    "emit_counter_totals_audit_logs",
    "visible_page_counts_from_rows",
]
