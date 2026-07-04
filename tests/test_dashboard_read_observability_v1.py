# -*- coding: utf-8 -*-
"""
Dashboard Read Model Observability V1 (I1/I2/I3/I5) — tests.

Proves: metrics populate from the real read path, read parity / behavior neutrality
is preserved (observability never mutates payloads), read-path distribution and
hot-slice degrade classification are correct, builder coverage/lag is exposed, and
the dashboard status classifier now reacts to real production latency.
"""
from __future__ import annotations

import time

import pytest

from extensions import db
from models import DashboardSnapshot, Store
from services.dashboard_read_observability_v1 import (
    BRANCH_DEGRADED,
    BRANCH_HIT,
    BRANCH_MISSING_STORE_SLUG,
    BRANCH_NO_SNAPSHOT,
    BRANCH_ROUTE_BUDGET_EXCEEDED,
    BRANCH_SNAPSHOT_READ_ERROR,
    BRANCH_STALE,
    READ_PATH_BOUNDED_LIVE,
    READ_PATH_SNAPSHOT,
    build_dashboard_read_observability_report,
    classify_read_branch,
    classify_read_path,
    record_dashboard_read_sample,
    reset_dashboard_read_observability_for_tests,
)


def _reset() -> None:
    reset_dashboard_read_observability_for_tests()


def _reset_db() -> None:
    db.session.query(DashboardSnapshot).delete()
    db.session.query(Store).delete()
    db.session.commit()
    _reset()


# --------------------------------------------------------------------------- #
# Unit — classification                                                       #
# --------------------------------------------------------------------------- #
def test_classify_read_path() -> None:
    assert classify_read_path("normal-carts") == READ_PATH_BOUNDED_LIVE
    for ep in ("summary", "widget-panel", "refresh-state", "store-connection"):
        assert classify_read_path(ep) == READ_PATH_SNAPSHOT


def test_classify_read_branch_mapping() -> None:
    assert classify_read_branch({"reason": None, "status": "active", "stale": False}) == BRANCH_HIT
    assert classify_read_branch({"reason": "stale_snapshot", "stale": True}) == BRANCH_STALE
    assert classify_read_branch({"reason": "no_snapshot", "status": "miss"}) == BRANCH_NO_SNAPSHOT
    assert classify_read_branch({"reason": "missing_store_slug"}) == BRANCH_MISSING_STORE_SLUG
    assert (
        classify_read_branch({"reason": "route_budget_exceeded", "budget_exceeded": True})
        == BRANCH_ROUTE_BUDGET_EXCEEDED
    )
    assert classify_read_branch({"degraded": True}) == BRANCH_DEGRADED


def test_empty_report_is_safe() -> None:
    _reset()
    rpt = build_dashboard_read_observability_report()
    assert rpt["total_requests"] == 0
    assert rpt["latency"]["route_ms"]["p50_ms"] is None
    assert rpt["latency"]["route_ms"]["p99_ms"] is None
    for bucket in rpt["read_path_distribution"]["by_read_path"].values():
        assert bucket["count"] == 0
        assert bucket["pct"] is None
    assert rpt["hot_slice"]["reads"] == 0
    assert rpt["hot_slice"]["degraded_rate_pct"] is None


def test_record_never_raises_on_bad_input() -> None:
    _reset()
    record_dashboard_read_sample(endpoint="", route_ms=None, branch="not_a_branch")
    record_dashboard_read_sample(endpoint="summary", route_ms=-5.0, read_path="bogus")
    rpt = build_dashboard_read_observability_report()
    assert rpt["total_requests"] == 2


# --------------------------------------------------------------------------- #
# Unit — percentiles + distribution + hot slice                               #
# --------------------------------------------------------------------------- #
def test_percentiles_and_read_path_distribution() -> None:
    _reset()
    for ms in (10.0, 20.0, 30.0, 40.0, 100.0):
        record_dashboard_read_sample(endpoint="summary", route_ms=ms, snapshot_read_ms=2.0)
    record_dashboard_read_sample(
        endpoint="normal-carts",
        route_ms=55.0,
        snapshot_read_ms=3.0,
        read_path=READ_PATH_BOUNDED_LIVE,
        hot_slice_ms=40.0,
        hot_slice_queries=8,
        data_freshness="hot_merged",
    )
    rpt = build_dashboard_read_observability_report()
    route = rpt["latency"]["route_ms"]
    assert route["sample_count"] == 6
    assert route["p50_ms"] is not None and route["p99_ms"] is not None
    assert route["p99_ms"] >= route["p90_ms"] >= route["p50_ms"]
    dist = rpt["read_path_distribution"]["by_read_path"]
    assert dist[READ_PATH_SNAPSHOT]["count"] == 5
    assert dist[READ_PATH_BOUNDED_LIVE]["count"] == 1
    assert "summary" in rpt["latency"]["route_ms_by_endpoint"]


def test_hot_slice_degrade_classification() -> None:
    _reset()
    # healthy
    record_dashboard_read_sample(
        endpoint="normal-carts", route_ms=50.0, hot_slice_ms=30.0,
        hot_slice_queries=6, data_freshness="hot_merged",
    )
    # query-budget limit hit
    record_dashboard_read_sample(
        endpoint="normal-carts", route_ms=80.0, hot_slice_ms=45.0, hot_slice_queries=18,
        hot_slice_degraded=True, hot_slice_reason="query_budget_exceeded_18",
        data_freshness="snapshot_only",
    )
    # slow → timeout class
    record_dashboard_read_sample(
        endpoint="normal-carts", route_ms=650.0, hot_slice_ms=620.0, hot_slice_queries=10,
        hot_slice_degraded=True, hot_slice_reason="slow_620ms", data_freshness="snapshot_only",
    )
    hot = build_dashboard_read_observability_report()["hot_slice"]
    assert hot["reads"] == 3
    assert hot["degraded_count"] == 2
    assert hot["limit_hit_count"] == 1
    assert hot["timeout_count"] == 1
    assert hot["degraded_rate_pct"] == pytest.approx(66.7, abs=0.2)
    assert hot["queries_max"] == 18


# --------------------------------------------------------------------------- #
# Integration — production wiring via enforce_route_budget                    #
# --------------------------------------------------------------------------- #
def test_enforce_route_budget_records_and_preserves_payload() -> None:
    _reset()
    from services.dashboard_snapshot_read_v1 import enforce_route_budget

    body = {
        "snapshot_mode": True,
        "kpis": {"abandoned_today": 3},
        "_snapshot": {"read_ms": 2.5, "reason": None, "status": "active", "stale": False},
    }
    keys_before = set(body.keys())
    out = enforce_route_budget(body, wall0=time.perf_counter() - 0.05, endpoint="summary")

    # Behavior neutrality: only pre-existing enforce behavior touched the payload
    # (route_ms inside _snapshot). No observability keys leaked into the response.
    assert out is body
    assert set(out.keys()) == keys_before
    assert "route_ms" in out["_snapshot"]
    assert "read_observability" not in out
    assert out["kpis"] == {"abandoned_today": 3}

    rpt = build_dashboard_read_observability_report()
    assert rpt["total_requests"] == 1
    assert rpt["read_path_distribution"]["by_branch"][BRANCH_HIT]["count"] == 1
    assert rpt["latency"]["route_ms"]["sample_count"] == 1
    assert rpt["latency"]["route_ms"]["last_ms"] >= 40.0  # ~50ms wall


def test_enforce_route_budget_over_budget_marks_branch() -> None:
    _reset()
    import os

    from services.dashboard_snapshot_read_v1 import enforce_route_budget

    os.environ["CARTFLOW_DASHBOARD_ROUTE_MAX_MS"] = "50"
    try:
        body = {"_snapshot": {"read_ms": 1.0}}
        enforce_route_budget(body, wall0=time.perf_counter() - 0.2, endpoint="normal-carts")
    finally:
        os.environ.pop("CARTFLOW_DASHBOARD_ROUTE_MAX_MS", None)
    rpt = build_dashboard_read_observability_report()
    assert rpt["read_path_distribution"]["by_branch"][BRANCH_ROUTE_BUDGET_EXCEEDED]["count"] == 1


def test_enforcement_guard_error_branch_recorded() -> None:
    _reset()
    from services.dashboard_snapshot_enforcement_guard_v1 import (
        _record_snapshot_read_error_observability,
    )

    _record_snapshot_read_error_observability("/api/dashboard/normal-carts")
    rpt = build_dashboard_read_observability_report()
    assert rpt["read_path_distribution"]["by_branch"][BRANCH_SNAPSHOT_READ_ERROR]["count"] == 1
    assert "normal-carts" in rpt["read_path_distribution"]["by_endpoint"]


# --------------------------------------------------------------------------- #
# Integration — real read path (DB) proves hit branch + parity                #
# --------------------------------------------------------------------------- #
def test_real_read_path_records_hit_and_preserves_read_parity() -> None:
    _reset_db()
    from services.dashboard_snapshot_read_v1 import build_summary_from_snapshot
    from services.dashboard_snapshot_v1 import (
        SNAPSHOT_TYPE_SUMMARY,
        upsert_dashboard_snapshot,
    )

    slug = "778811"
    payload = {"snapshot_mode": True, "kpis": {"abandoned_today": 7}}
    upsert_dashboard_snapshot(
        store_id=1, store_slug=slug, snapshot_type=SNAPSHOT_TYPE_SUMMARY, payload=payload
    )
    db.session.commit()

    # Same call twice — with observability enabled — must return equal payloads.
    out1 = build_summary_from_snapshot(store_slug=slug)
    out2 = build_summary_from_snapshot(store_slug=slug)
    assert out1.get("kpis") == {"abandoned_today": 7}
    assert out1.get("kpis") == out2.get("kpis")
    assert "read_observability" not in out1  # response never carries observability data

    rpt = build_dashboard_read_observability_report()
    assert rpt["read_path_distribution"]["by_branch"][BRANCH_HIT]["count"] >= 2
    assert rpt["latency"]["route_ms"]["sample_count"] >= 2


def test_real_read_path_missing_snapshot_records_no_snapshot_branch() -> None:
    _reset_db()
    from services.dashboard_snapshot_read_v1 import build_widget_panel_from_snapshot

    out = build_widget_panel_from_snapshot(store_slug="999002")
    assert out.get("snapshot_degraded") is True
    rpt = build_dashboard_read_observability_report()
    assert rpt["read_path_distribution"]["by_branch"][BRANCH_NO_SNAPSHOT]["count"] >= 1


# --------------------------------------------------------------------------- #
# Integration — builder coverage / lag (I3)                                   #
# --------------------------------------------------------------------------- #
def test_assess_builder_coverage_exposes_lag_and_cycle() -> None:
    _reset_db()
    from services.dashboard_snapshot_v1 import (
        SNAPSHOT_TYPE_NORMAL_CARTS,
        upsert_dashboard_snapshot,
    )
    from services.operational_metrics_v1 import assess_builder_coverage

    # Two eligible merchant stores; one has a normal_carts snapshot, one does not.
    db.session.add(Store(zid_store_id="770001", merchant_user_id=1, is_active=True))
    db.session.add(Store(zid_store_id="770002", merchant_user_id=2, is_active=True))
    db.session.commit()
    upsert_dashboard_snapshot(
        store_id=1, store_slug="770001", snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        payload={"merchant_carts_page_rows": []},
    )
    db.session.commit()

    cov = assess_builder_coverage(db.session)
    assert cov.get("error") is None
    assert cov["eligible_store_count"] >= 2
    assert cov["built_store_count"] >= 1
    assert cov["stores_never_built"] >= 1
    assert cov["stores_waiting_for_refresh"] >= 1
    assert cov["builder_cycle_seconds"] is not None
    assert cov["builder_lag_seconds"] is not None
    assert cov["stores_per_tick_limit"] >= 1


# --------------------------------------------------------------------------- #
# Integration — dashboard status reacts to REAL production latency            #
# --------------------------------------------------------------------------- #
def test_status_reacts_to_real_production_latency() -> None:
    _reset()
    from services.operational_metrics_v1 import (
        classify_dashboard_status,
        clear_dashboard_timing_samples_for_tests,
        collect_dashboard_timing_metrics,
    )

    clear_dashboard_timing_samples_for_tests()
    # Simulate two slow production requests recorded via the real read hook.
    record_dashboard_read_sample(endpoint="summary", route_ms=260.0, snapshot_read_ms=4.0)
    record_dashboard_read_sample(endpoint="summary", route_ms=320.0, snapshot_read_ms=4.0)

    timing = collect_dashboard_timing_metrics()
    # Real per-request latency now feeds the timing block (not test-only).
    assert timing["route_ms"]["sample_count"] >= 2
    assert timing["route_ms"]["source"] == "production_read_path"
    assert "read_observability" in timing

    status = classify_dashboard_status(snapshot={"normal_carts_stale_pct": 0.0}, timing=timing)
    assert status in ("warning", "critical")
