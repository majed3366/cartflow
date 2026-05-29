# -*- coding: utf-8 -*-
"""
Deep performance audit for simulation dashboard_check_ms and purchase_check_ms.

Logging/metrics only — no recovery or dashboard behavior changes.
"""
from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Optional
from unittest.mock import patch

from services.db_request_audit import audit_profile_span


def _norm_fn(name: str) -> str:
    return (name or "").strip().lower()


def _categorize_dashboard_span(fn: str) -> str:
    f = _norm_fn(fn)
    if "lifecycle" in f:
        return "lifecycle"
    if any(
        tok in f
        for tok in (
            "pick",
            "activity_rank",
            "group",
            "picked",
            "ensure_",
            "stale",
        )
    ):
        return "grouping"
    if any(
        tok in f
        for tok in (
            "augment",
            "batch_build",
            "batch_index",
            "batch_scan",
            "batch_reads",
            "merge",
            "projection",
            "batch_resolve",
        )
    ):
        return "merge"
    if f.startswith("sql:") or "sql" in f:
        return "db"
    return "other"


def _sum_stage_ms(stage_ms: dict[str, float], *needles: str) -> float:
    total = 0.0
    for key, ms in (stage_ms or {}).items():
        lk = _norm_fn(key)
        if any(n in lk for n in needles):
            total += float(ms or 0.0)
    return total


@dataclass
class _SpanAgg:
    calls: int = 0
    wall_ms: float = 0.0
    queries: int = 0

    def add(self, *, wall_ms: float, queries: int) -> None:
        self.calls += 1
        self.wall_ms += max(0.0, float(wall_ms))
        self.queries += max(0, int(queries))


@dataclass
class _PurchasePhaseSample:
    record_truth_ms: float = 0.0
    lifecycle_ms: float = 0.0
    reconcile_ms: float = 0.0
    record_truth_queries: int = 0
    lifecycle_queries: int = 0
    reconcile_queries: int = 0


@contextmanager
def _purchase_ingest_phase_timer() -> Iterator[_PurchasePhaseSample]:
    """Time purchase sub-phases by wrapping callees — delegates unchanged."""
    sample = _PurchasePhaseSample()
    timers: dict[str, tuple[float, int]] = {}

    def _wrap(label: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        def _inner(*args: Any, **kwargs: Any) -> Any:
            with audit_profile_span(f"sim:purchase:{label}") as bucket:
                t0 = time.perf_counter()
                out = fn(*args, **kwargs)
            ms = (time.perf_counter() - t0) * 1000.0
            timers[label] = (ms, int(bucket.get("queries") or 0))
            return out

        return _inner

    started: list[Any] = []
    try:
        import services.cartflow_purchase_truth as cpt
        import services.lifecycle_closure_records_v1 as lcr
        import services.purchase_truth as pt

        real_record = cpt.record_purchase
        real_closure = lcr.record_lifecycle_closure
        real_apply_lc = pt.apply_purchase_truth_lifecycle_closure
        real_reconcile = pt._reconcile_active_recovery_carts

        p1 = patch.object(cpt, "record_purchase", _wrap("record_truth", real_record))
        p1b = patch.object(pt, "record_purchase", _wrap("record_truth", real_record))
        p2 = patch.object(
            lcr, "record_lifecycle_closure", _wrap("lifecycle_closure", real_closure)
        )
        p3 = patch.object(
            pt,
            "apply_purchase_truth_lifecycle_closure",
            _wrap("apply_lifecycle", real_apply_lc),
        )
        p4 = patch.object(
            pt, "_reconcile_active_recovery_carts", _wrap("reconcile", real_reconcile)
        )
        for p in (p1, p1b, p2, p3, p4):
            p.start()
            started.append(p)
        yield sample
    finally:
        for p in reversed(started):
            p.stop()
        rt = timers.get("record_truth", (0.0, 0))
        lc = timers.get("lifecycle_closure", (0.0, 0))
        lc_apply = timers.get("apply_lifecycle", (0.0, 0))
        lc = (lc[0] + lc_apply[0], lc[1] + lc_apply[1])
        rc = timers.get("reconcile", (0.0, 0))
        sample.record_truth_ms = float(rt[0])
        sample.lifecycle_ms = float(lc[0])
        sample.reconcile_ms = float(rc[0])
        sample.record_truth_queries = int(rt[1])
        sample.lifecycle_queries = int(lc[1])
        sample.reconcile_queries = int(rc[1])


@dataclass
class DeepProfileAccumulator:
    """Aggregates deep-profile samples across a simulation run."""

    dashboard_calls: int = 0
    purchase_calls: int = 0
    dashboard_wall_ms: float = 0.0
    purchase_wall_ms: float = 0.0
    dashboard_queries: int = 0
    purchase_queries: int = 0
    dashboard_db_ms: float = 0.0
    dashboard_lifecycle_ms: float = 0.0
    dashboard_grouping_ms: float = 0.0
    dashboard_merge_ms: float = 0.0
    dashboard_other_ms: float = 0.0
    purchase_ingest_ms: float = 0.0
    purchase_reconcile_ms: float = 0.0
    purchase_lifecycle_ms: float = 0.0
    purchase_dashboard_ms: float = 0.0
    purchase_record_truth_ms: float = 0.0
    purchase_ingest_queries: int = 0
    purchase_reconcile_queries: int = 0
    purchase_dashboard_queries: int = 0
    fn_wall: dict[str, _SpanAgg] = field(default_factory=lambda: defaultdict(_SpanAgg))

    def record_dashboard(
        self,
        *,
        wall_ms: float,
        queries: int,
        perf_snap: dict[str, Any],
        span_snap: list[dict[str, Any]],
    ) -> None:
        self.dashboard_calls += 1
        self.dashboard_wall_ms += max(0.0, float(wall_ms))
        self.dashboard_queries += max(0, int(queries))

        stage_ms = perf_snap.get("stage_ms") if isinstance(perf_snap, dict) else {}
        if not isinstance(stage_ms, dict):
            stage_ms = {}

        lifecycle_ms = float(perf_snap.get("lifecycle_attach_ms") or 0.0)
        lifecycle_ms += float(perf_snap.get("row_lifecycle_ms_sum") or 0.0)
        lifecycle_ms += float(perf_snap.get("row_lifecycle_truth_ms_sum") or 0.0)
        lifecycle_ms += float(perf_snap.get("followup_clarity_ms") or 0.0)

        db_ms = _sum_stage_ms(stage_ms, "abandoned_candidates", "batch_reads", "sql")
        grouping_ms = _sum_stage_ms(
            stage_ms, "pick", "activity", "group", "stale", "payload_rows"
        )
        merge_ms = _sum_stage_ms(stage_ms, "batch", "augment", "merge")

        for row in span_snap or ():
            fn = str(row.get("fn") or "")
            exc = float(row.get("wall_ms_exclusive") or 0.0)
            cat = _categorize_dashboard_span(fn)
            if cat == "db":
                db_ms += exc
            elif cat == "grouping":
                grouping_ms += exc
            elif cat == "merge":
                merge_ms += exc
            elif cat == "lifecycle":
                lifecycle_ms += exc
            self.fn_wall[fn].add(
                wall_ms=exc,
                queries=int(row.get("queries_exclusive") or 0),
            )

        accounted = db_ms + grouping_ms + merge_ms + lifecycle_ms
        other_ms = max(0.0, float(wall_ms) - accounted)
        self.dashboard_db_ms += db_ms
        self.dashboard_grouping_ms += grouping_ms
        self.dashboard_merge_ms += merge_ms
        self.dashboard_lifecycle_ms += lifecycle_ms
        self.dashboard_other_ms += other_ms

    def record_purchase(
        self,
        *,
        total_ms: float,
        ingest_ms: float,
        record_truth_ms: float,
        lifecycle_ms: float,
        reconcile_ms: float,
        dashboard_ms: float,
        ingest_queries: int,
        reconcile_queries: int,
        dashboard_queries: int,
        span_snap: list[dict[str, Any]],
    ) -> None:
        self.purchase_calls += 1
        self.purchase_wall_ms += max(0.0, float(total_ms))
        self.purchase_ingest_ms += max(0.0, float(ingest_ms))
        self.purchase_record_truth_ms += max(0.0, float(record_truth_ms))
        self.purchase_lifecycle_ms += max(0.0, float(lifecycle_ms))
        self.purchase_reconcile_ms += max(0.0, float(reconcile_ms))
        self.purchase_dashboard_ms += max(0.0, float(dashboard_ms))
        self.purchase_ingest_queries += max(0, int(ingest_queries))
        self.purchase_reconcile_queries += max(0, int(reconcile_queries))
        self.purchase_dashboard_queries += max(0, int(dashboard_queries))
        self.purchase_queries += (
            max(0, int(ingest_queries))
            + max(0, int(reconcile_queries))
            + max(0, int(dashboard_queries))
        )
        for label, ms in (
            ("purchase:record_truth", record_truth_ms),
            ("purchase:lifecycle_closure", lifecycle_ms),
            ("purchase:reconcile", reconcile_ms),
        ):
            if ms > 0:
                self.fn_wall[label].add(wall_ms=ms, queries=0)
        for row in span_snap or ():
            fn = str(row.get("fn") or "")
            self.fn_wall[f"purchase_dashboard:{fn}"].add(
                wall_ms=float(row.get("wall_ms_exclusive") or 0.0),
                queries=int(row.get("queries_exclusive") or 0),
            )

    def _avg(self, total: float, n: int) -> float:
        if n < 1:
            return 0.0
        return round(total / n, 2)

    def _top_functions(self, limit: int = 5) -> list[dict[str, Any]]:
        ranked = sorted(
            self.fn_wall.items(),
            key=lambda kv: (-kv[1].wall_ms, kv[0]),
        )
        out: list[dict[str, Any]] = []
        for fn, agg in ranked[: max(1, int(limit))]:
            if agg.wall_ms <= 0 and agg.queries <= 0:
                continue
            out.append(
                {
                    "function": fn,
                    "calls": int(agg.calls),
                    "total_wall_ms": round(agg.wall_ms, 2),
                    "avg_wall_ms": self._avg(agg.wall_ms, agg.calls),
                    "total_queries": int(agg.queries),
                }
            )
        return out

    def build_report(self) -> dict[str, Any]:
        dc = max(1, self.dashboard_calls) if self.dashboard_calls else 0
        pc = max(1, self.purchase_calls) if self.purchase_calls else 0
        profiled_total = self.dashboard_wall_ms + self.purchase_wall_ms
        dash_pct = (
            round(100.0 * self.dashboard_wall_ms / profiled_total, 1)
            if profiled_total > 0
            else 0.0
        )
        return {
            "dashboard_check_ms": {
                "calls": self.dashboard_calls,
                "total_wall_ms": round(self.dashboard_wall_ms, 2),
                "avg_wall_ms_per_call": self._avg(self.dashboard_wall_ms, self.dashboard_calls),
                "total_queries": self.dashboard_queries,
                "avg_queries_per_call": self._avg(float(self.dashboard_queries), self.dashboard_calls),
                "breakdown_ms": {
                    "db_ms": round(self.dashboard_db_ms, 2),
                    "lifecycle_ms": round(self.dashboard_lifecycle_ms, 2),
                    "grouping_ms": round(self.dashboard_grouping_ms, 2),
                    "merge_ms": round(self.dashboard_merge_ms, 2),
                    "other_ms": round(self.dashboard_other_ms, 2),
                },
                "breakdown_avg_ms_per_call": {
                    "db_ms": self._avg(self.dashboard_db_ms, dc),
                    "lifecycle_ms": self._avg(self.dashboard_lifecycle_ms, dc),
                    "grouping_ms": self._avg(self.dashboard_grouping_ms, dc),
                    "merge_ms": self._avg(self.dashboard_merge_ms, dc),
                    "other_ms": self._avg(self.dashboard_other_ms, dc),
                },
            },
            "purchase_check_ms": {
                "calls": self.purchase_calls,
                "total_wall_ms": round(self.purchase_wall_ms, 2),
                "avg_wall_ms_per_call": self._avg(self.purchase_wall_ms, self.purchase_calls),
                "total_queries": self.purchase_queries,
                "avg_queries_per_call": self._avg(float(self.purchase_queries), self.purchase_calls),
                "breakdown_ms": {
                    "record_truth_ms": round(self.purchase_record_truth_ms, 2),
                    "lifecycle_closure_ms": round(self.purchase_lifecycle_ms, 2),
                    "reconcile_active_carts_ms": round(self.purchase_reconcile_ms, 2),
                    "dashboard_after_purchase_ms": round(self.purchase_dashboard_ms, 2),
                    "ingest_total_ms": round(self.purchase_ingest_ms, 2),
                },
                "breakdown_avg_ms_per_call": {
                    "record_truth_ms": self._avg(self.purchase_record_truth_ms, pc),
                    "lifecycle_closure_ms": self._avg(self.purchase_lifecycle_ms, pc),
                    "reconcile_active_carts_ms": self._avg(self.purchase_reconcile_ms, pc),
                    "dashboard_after_purchase_ms": self._avg(self.purchase_dashboard_ms, pc),
                    "ingest_total_ms": self._avg(self.purchase_ingest_ms, pc),
                },
                "breakdown_queries": {
                    "ingest_queries": self.purchase_ingest_queries,
                    "reconcile_queries": self.purchase_reconcile_queries,
                    "dashboard_queries": self.purchase_dashboard_queries,
                },
            },
            "top_slowest_functions": self._top_functions(5),
            "share_of_profiled_wall_ms": {
                "dashboard_check_pct": dash_pct,
                "purchase_check_pct": round(100.0 - dash_pct, 1) if dash_pct else 0.0,
            },
            "notes": [
                "dashboard_check_ms includes all _measure_dashboard calls (before/after send, reply, return, purchase).",
                "purchase_check_ms wall time spans ingest_purchase_truth plus final dashboard read.",
                "breakdown_ms uses dashboard perf stages + normal-carts subprofiler exclusive wall.",
                "purchase sub-phases are timed via delegate wrappers — same call order and outcomes.",
                "No recovery, scheduling, or WhatsApp behavior is changed by this audit.",
            ],
        }


def profile_dashboard_check(
    run_dashboard: Callable[[], Optional[dict[str, Any]]],
) -> tuple[Optional[dict[str, Any]], float, dict[str, Any]]:
    """Wrap one dashboard truth check; returns (row, wall_ms, profile_sample)."""
    from services.dashboard_normal_carts_perf_v1 import (  # noqa: PLC0415
        dashboard_normal_carts_perf_begin,
        dashboard_normal_carts_perf_emit,
        dashboard_normal_carts_perf_snapshot,
    )
    from services.normal_carts_query_profiler import (  # noqa: PLC0415
        normal_carts_profile_begin_for_simulation,
        normal_carts_profile_end,
        normal_carts_profile_snapshot,
    )

    with audit_profile_span("sim:dashboard_check") as bucket:
        wall0 = time.perf_counter()
        normal_carts_profile_begin_for_simulation()
        dashboard_normal_carts_perf_begin()
        row = run_dashboard()
        perf_snap = dashboard_normal_carts_perf_snapshot()
        span_snap = normal_carts_profile_snapshot()
        dashboard_normal_carts_perf_emit(wall_perf_start=wall0)
        normal_carts_profile_end()
        wall_ms = (time.perf_counter() - wall0) * 1000.0
        sample = {
            "queries": int(bucket.get("queries") or 0),
            "wall_ms": round(wall_ms, 2),
            "perf": perf_snap,
            "spans": span_snap,
        }
    return row, wall_ms, sample


def profile_purchase_check(
    *,
    ingest_fn: Callable[[], None],
    dashboard_fn: Callable[[], Optional[dict[str, Any]]],
) -> tuple[Optional[dict[str, Any]], float, dict[str, Any]]:
    """Profile purchase ingest (single canonical path) + post-purchase dashboard read."""
    total0 = time.perf_counter()
    phase = _PurchasePhaseSample()

    with audit_profile_span("sim:purchase_ingest_total") as ingest_bucket:
        t0 = time.perf_counter()
        with _purchase_ingest_phase_timer() as phase:
            ingest_fn()
        ingest_ms = (time.perf_counter() - t0) * 1000.0
        ingest_queries = int(ingest_bucket.get("queries") or 0)

    row, dash_ms, dash_sample = profile_dashboard_check(dashboard_fn)
    total_ms = (time.perf_counter() - total0) * 1000.0

    sample = {
        "total_ms": round(total_ms, 2),
        "ingest_ms": round(ingest_ms, 2),
        "record_truth_ms": round(phase.record_truth_ms, 2),
        "lifecycle_ms": round(phase.lifecycle_ms, 2),
        "reconcile_ms": round(phase.reconcile_ms, 2),
        "dashboard_ms": round(dash_ms, 2),
        "ingest_queries": ingest_queries,
        "reconcile_queries": phase.reconcile_queries,
        "dashboard_queries": int((dash_sample or {}).get("queries") or 0),
        "dashboard_spans": (dash_sample or {}).get("spans") or [],
    }
    return row, total_ms, sample


__all__ = [
    "DeepProfileAccumulator",
    "profile_dashboard_check",
    "profile_purchase_check",
]
