# -*- coding: utf-8 -*-
"""INV-001 WP-5 — Dashboard/Home ↔ Knowledge Time Authority cross-surface tests."""
from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from extensions import db
from models import AbandonedCart, Store
from services.dashboard_kpi_time_v1 import (
    merchant_kpi_today_projection,
    merchant_month_window_projection,
    merchant_reason_counts_store_window,
    resolve_dashboard_rolling_windows,
    resolve_dashboard_today_window,
)
from services.knowledge_metrics_v1 import collect_knowledge_metrics
from services.knowledge_time_authority_v1 import resolve_knowledge_windows
from services.time_authority import (
    WindowRecipeId,
    clear_query_time_context,
    historical_replay_scope,
    simulation_scope,
    window_for,
)

FIXED = datetime(2026, 5, 4, 15, 30, 45, tzinfo=timezone.utc)
JULY = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
_STORE = "wp5-xsurf-store"


def setup_function() -> None:
    clear_query_time_context()


def teardown_function() -> None:
    clear_query_time_context()


def _reset() -> None:
    for model in (AbandonedCart, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()


@pytest.fixture()
def xdb():
    _reset()
    db.create_all()
    yield
    _reset()


def _seed_may(n: int = 4) -> Store:
    store = Store(zid_store_id=_STORE, access_token="t", is_active=True)
    db.session.add(store)
    db.session.commit()
    db.session.refresh(store)
    base = datetime(2026, 5, 2, 10, 0, 0)
    for i in range(n):
        db.session.add(
            AbandonedCart(
                store_id=store.id,
                zid_cart_id=f"wp5-x-{i}",
                status="abandoned",
                recovery_session_id=f"wp5-s-{i}",
                first_seen_at=base + timedelta(hours=i),
                last_seen_at=base + timedelta(hours=i),
                vip_mode=False,
                cart_value=50.0,
            )
        )
    db.session.commit()
    return store


@pytest.mark.parametrize("days", [1, 7, 14, 30])
def test_production_dashboard_equals_knowledge_windows(days: int) -> None:
    kl = resolve_knowledge_windows(window_days=days, now=FIXED)
    dash = resolve_dashboard_rolling_windows(window_days=days, now=FIXED)
    assert (dash.start, dash.end, dash.prev_start) == (
        kl.start,
        kl.end,
        kl.prev_start,
    )
    assert dash.primary.start_at == kl.primary.start_at
    assert dash.comparison.start_at == kl.comparison.start_at


def test_today_matches_wp3_today_recipe() -> None:
    start, end, ctx = resolve_dashboard_today_window(now=FIXED)
    tw = window_for(WindowRecipeId.TODAY, context=ctx)
    assert start == tw.start_at.replace(tzinfo=None)
    assert end == tw.end_at.replace(tzinfo=None)


def test_simulation_dashboard_equals_knowledge_windows() -> None:
    with simulation_scope(simulation_run_id="srs_wp5", start=FIXED):
        kl = resolve_knowledge_windows(window_days=7)
        dash = resolve_dashboard_rolling_windows(window_days=7)
    assert (dash.start, dash.end, dash.prev_start) == (
        kl.start,
        kl.end,
        kl.prev_start,
    )
    assert dash.context.simulation_run_id == "srs_wp5"


def test_historical_replay_dashboard_equals_knowledge() -> None:
    with historical_replay_scope(FIXED, replay_id="hr-wp5"):
        kl = resolve_knowledge_windows(window_days=7)
        dash = resolve_dashboard_rolling_windows(window_days=7)
    assert (dash.start, dash.end) == (kl.start, kl.end)
    assert dash.context.replay_id == "hr-wp5"


def test_comparison_period_symmetry_cross_surface() -> None:
    kl = resolve_knowledge_windows(window_days=7, now=FIXED)
    dash = resolve_dashboard_rolling_windows(window_days=7, now=FIXED)
    assert dash.prev_start == kl.prev_start
    assert dash.end - dash.start == dash.start - dash.prev_start


def test_half_open_boundary_rolling(xdb) -> None:
    store = _seed_may(0)
    tw = resolve_dashboard_rolling_windows(window_days=7, now=FIXED)
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id="at-start",
            status="abandoned",
            first_seen_at=tw.start,
            last_seen_at=tw.start,
            vip_mode=False,
        )
    )
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id="at-end",
            status="abandoned",
            first_seen_at=tw.end,
            last_seen_at=tw.end,
            vip_mode=False,
        )
    )
    db.session.commit()
    month = merchant_month_window_projection(store, days=7, now=FIXED)
    assert month["abandoned_total"] == 1


def test_sim_sees_may_production_july_zero(xdb) -> None:
    store = _seed_may(4)
    july_m = merchant_month_window_projection(store, days=7, now=JULY)
    july_k = collect_knowledge_metrics(db.session, _STORE, window_days=7, now=JULY)
    assert july_m["abandoned_total"] == 0
    assert july_k.cart_count == 0
    with simulation_scope(simulation_run_id="srs_gate", start=FIXED):
        may_m = merchant_month_window_projection(store, days=7)
        may_k = collect_knowledge_metrics(db.session, _STORE, window_days=7)
    assert may_m["abandoned_total"] == 4
    assert may_k.cart_count == 4
    dash_w = resolve_dashboard_rolling_windows(window_days=7, now=FIXED)
    kl_w = resolve_knowledge_windows(window_days=7, now=FIXED)
    assert dash_w.end == kl_w.end
    assert may_k.window_end == kl_w.end


def test_no_wall_clock_in_dashboard_kpi_module() -> None:
    src = Path("services/dashboard_kpi_time_v1.py").read_text(encoding="utf-8")
    assert "datetime.now" not in src
    assert "utcnow" not in src
    assert "legacy_today" not in src
    assert "legacy_rolling" not in src
    assert "LEGACY_KPI_TIME" not in src


def test_no_duplicate_filtering_system() -> None:
    src = Path("services/dashboard_kpi_time_v1.py").read_text(encoding="utf-8")
    assert "resolve_knowledge_windows" in src
    assert "window_for" in src
    assert "timedelta(days" not in src


def test_main_py_still_call_site_only_for_kpi() -> None:
    main_txt = Path("main.py").read_text(encoding="utf-8")
    assert "def _merchant_kpi_today_projection" not in main_txt
    assert "from services.dashboard_kpi_time_v1 import" in main_txt
    # No new temporal math added in WP-5
    assert "legacy_today_utc_bounds" not in main_txt


def test_index_friendly_predicates() -> None:
    src = Path("services/dashboard_kpi_time_v1.py").read_text(encoding="utf-8")
    assert "last_seen_at >= start" in src or ">= start" in src
    assert "last_seen_at < end" in src or "< end" in src or "< end_day" in src
    assert "func.date(" not in src
