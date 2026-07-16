# -*- coding: utf-8 -*-
"""INV-001 WP-6 — Daily Brief ↔ Knowledge ↔ Dashboard Time Authority cross-surface."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.dashboard_kpi_time_v1 import resolve_dashboard_rolling_windows
from services.knowledge_time_authority_v1 import (
    knowledge_stamp_now,
    resolve_knowledge_windows,
)
from services.merchant_daily_brief_composer_v2 import compose_merchant_daily_brief_v2
from services.merchant_daily_brief_time_v1 import (
    assert_brief_dashboard_knowledge_windows_equal,
    brief_date_iso,
    brief_stamp_now,
    resolve_brief_windows,
)
from services.merchant_daily_brief_v1 import compose_merchant_daily_brief_v1
from services.time_authority import (
    clear_query_time_context,
    historical_replay_scope,
    simulation_scope,
)

FIXED = datetime(2026, 5, 4, 15, 30, 45, tzinfo=timezone.utc)
JULY = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)

_BRIEF_MODULES = (
    Path("services/merchant_daily_brief_time_v1.py"),
    Path("services/merchant_daily_brief_v1.py"),
    Path("services/merchant_daily_brief_composer_v2.py"),
)


def setup_function() -> None:
    clear_query_time_context()


def teardown_function() -> None:
    clear_query_time_context()


@pytest.mark.parametrize("days", [1, 7, 14, 30])
def test_production_brief_equals_knowledge_windows(days: int) -> None:
    kl = resolve_knowledge_windows(window_days=days, now=FIXED)
    brief = resolve_brief_windows(window_days=days, now=FIXED)
    assert (brief.start, brief.end, brief.prev_start) == (
        kl.start,
        kl.end,
        kl.prev_start,
    )
    assert brief.primary.start_at == kl.primary.start_at
    assert brief.comparison.start_at == kl.comparison.start_at


@pytest.mark.parametrize("days", [1, 7, 14, 30])
def test_production_brief_equals_dashboard_windows(days: int) -> None:
    dash = resolve_dashboard_rolling_windows(window_days=days, now=FIXED)
    brief = resolve_brief_windows(window_days=days, now=FIXED)
    assert (brief.start, brief.end, brief.prev_start) == (
        dash.start,
        dash.end,
        dash.prev_start,
    )


def test_cross_surface_equality_helper() -> None:
    result = assert_brief_dashboard_knowledge_windows_equal(
        window_days=7, now=FIXED
    )
    assert result["equal"] is True


def test_simulation_brief_equals_knowledge() -> None:
    with simulation_scope(simulation_run_id="srs_wp6", start=FIXED):
        kl = resolve_knowledge_windows(window_days=7)
        brief = resolve_brief_windows(window_days=7)
        day = brief_date_iso()
    assert (brief.start, brief.end, brief.prev_start) == (
        kl.start,
        kl.end,
        kl.prev_start,
    )
    assert brief.context.simulation_run_id == "srs_wp6"
    assert day == FIXED.date().isoformat()


def test_replay_brief_equals_dashboard() -> None:
    with historical_replay_scope(FIXED, replay_id="hr-wp6"):
        dash = resolve_dashboard_rolling_windows(window_days=7)
        brief = resolve_brief_windows(window_days=7)
        stamp = brief_stamp_now()
    assert (brief.start, brief.end) == (dash.start, dash.end)
    assert brief.context.replay_id == "hr-wp6"
    assert stamp == FIXED


def test_comparison_period_symmetry() -> None:
    brief = resolve_brief_windows(window_days=7, now=FIXED)
    kl = resolve_knowledge_windows(window_days=7, now=FIXED)
    assert brief.prev_start == kl.prev_start
    assert brief.end - brief.start == brief.start - brief.prev_start


def test_boundary_timestamps_half_open() -> None:
    brief = resolve_brief_windows(window_days=7, now=FIXED)
    kl = resolve_knowledge_windows(window_days=7, now=FIXED)
    assert brief.start == kl.start
    assert brief.end == kl.end
    # WP-3 half-open projection: naive UTC bounds match recipe WindowResult
    assert brief.primary.start_at.replace(tzinfo=None) == brief.start
    assert brief.primary.end_at.replace(tzinfo=None) == brief.end
    assert brief.start < brief.end


def test_report_generation_timestamps_from_authority() -> None:
    stamp = brief_stamp_now(now=FIXED)
    assert stamp == knowledge_stamp_now(now=FIXED)
    assert brief_date_iso(now=FIXED) == "2026-05-04"
    brief_v1 = compose_merchant_daily_brief_v1(
        decision_bundles=[], brief_date=brief_date_iso(now=FIXED)
    )
    brief_v2 = compose_merchant_daily_brief_v2(
        decision_bundles=[], brief_date=brief_date_iso(now=FIXED)
    )
    assert brief_v1["brief_date"] == "2026-05-04"
    assert brief_v2["brief_date"] == "2026-05-04"


def test_no_wall_clock_in_brief_modules() -> None:
    for path in _BRIEF_MODULES:
        src = path.read_text(encoding="utf-8")
        assert "datetime.now" not in src, path
        assert "date.today" not in src, path
        assert "utcnow" not in src, path


def test_no_wall_clock_in_routing_stamp() -> None:
    src = Path("services/knowledge_routing_v1.py").read_text(encoding="utf-8")
    assert "datetime.now" not in src
    assert "utcnow" not in src
    assert "knowledge_stamp_now" in src


def test_no_duplicate_filtering_or_window_recipes() -> None:
    src = Path("services/merchant_daily_brief_time_v1.py").read_text(encoding="utf-8")
    assert "resolve_knowledge_windows" in src
    assert "timedelta(days" not in src
    assert "WindowRecipeId" not in src  # recipes owned by WP-3 / Knowledge bridge


def test_no_additional_sql_in_brief_time_bridge() -> None:
    src = Path("services/merchant_daily_brief_time_v1.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    banned = {"execute", "query", "session", "select", "filter"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in banned
        if isinstance(node, ast.Name) and node.id in ("db", "Session"):
            pytest.fail("brief time bridge must not touch DB")


def test_main_py_unchanged_for_wp6() -> None:
    main_txt = Path("main.py").read_text(encoding="utf-8")
    assert "merchant_daily_brief_time_v1" not in main_txt
    assert "resolve_brief_windows" not in main_txt


def test_window_generation_o1_no_recompute_divergence() -> None:
    a = resolve_brief_windows(window_days=7, now=JULY)
    b = resolve_brief_windows(window_days=7, now=JULY)
    c = resolve_knowledge_windows(window_days=7, now=JULY)
    d = resolve_dashboard_rolling_windows(window_days=7, now=JULY)
    assert (a.start, a.end, a.prev_start) == (b.start, b.end, b.prev_start)
    assert (a.start, a.end, a.prev_start) == (c.start, c.end, c.prev_start)
    assert (a.start, a.end, a.prev_start) == (d.start, d.end, d.prev_start)
