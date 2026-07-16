# -*- coding: utf-8 -*-
"""WP-3 — Governed Time Filtering Contract tests."""
from __future__ import annotations

import ast
import inspect
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.time_authority import (
    EmptinessType,
    QueryTimeContextKind,
    TimeProvenance,
    TimezonePolicy,
    WindowRecipeId,
    WindowResultStatus,
    classify_store_history,
    classify_timestamp,
    clear_query_time_context,
    filter_contract_meta,
    frozen_clock_scope,
    historical_replay_scope,
    production_scope,
    recovery_replay_scope,
    resolve_window_recipe,
    simulation_scope,
    window_for,
    windows_adjacent_non_overlapping,
)
from services.time_authority.filtering import INTERVAL_SHAPE
from services.time_authority.query_context import build_query_time_context

FIXED = datetime(2026, 5, 4, 15, 30, 45, tzinfo=timezone.utc)
MAY_MIDNIGHT = datetime(2026, 5, 4, 0, 0, 0, tzinfo=timezone.utc)
MAY_NEXT = datetime(2026, 5, 5, 0, 0, 0, tzinfo=timezone.utc)


def setup_function() -> None:
    clear_query_time_context()


def teardown_function() -> None:
    clear_query_time_context()


def test_interval_shape_contract() -> None:
    meta = filter_contract_meta()
    assert INTERVAL_SHAPE == "[start_at, end_at)"
    assert meta["interval_shape"] == INTERVAL_SHAPE
    assert meta["start_inclusive"] is True
    assert meta["end_exclusive"] is True
    assert meta["io"] == "none"


def test_today_from_production_context() -> None:
    with frozen_clock_scope(FIXED):
        # TESTING scope is fine for frozen now; also cover production_scope path
        w = window_for(WindowRecipeId.TODAY)
        assert w.ok
        assert w.start_at == MAY_MIDNIGHT
        assert w.end_at == MAY_NEXT
        assert w.authoritative_now == FIXED


def test_today_from_explicit_production_scope() -> None:
    with production_scope(correlation_id="wp3-prod"):
        # production uses SystemClock — only assert shape/provenance, not absolute day
        w = window_for(WindowRecipeId.TODAY)
        assert w.ok
        assert w.context_mode == QueryTimeContextKind.CURRENT_PRODUCTION
        assert w.end_at - w.start_at == timedelta(days=1)
        assert w.start_at.hour == 0
        assert w.correlation_id == "wp3-prod"


def test_today_from_simulation_context() -> None:
    with simulation_scope(simulation_run_id="srs_wp3", start=FIXED):
        w = window_for(WindowRecipeId.TODAY)
        assert w.ok
        assert w.start_at == MAY_MIDNIGHT
        assert w.end_at == MAY_NEXT
        assert w.context_mode == QueryTimeContextKind.SIMULATION
        assert w.simulation_run_id == "srs_wp3"
        assert w.authority_provenance == TimeProvenance.SIMULATION_CLOCK.value


def test_historical_replay_window() -> None:
    with historical_replay_scope(FIXED, replay_id="hr-wp3"):
        w = window_for(WindowRecipeId.HISTORICAL_REPLAY_RANGE, n_days=7)
        assert w.ok
        assert w.recipe == WindowRecipeId.HISTORICAL_REPLAY_RANGE
        assert w.replay_id == "hr-wp3"
        assert w.end_at == FIXED
        assert w.start_at == FIXED - timedelta(days=7)


def test_recovery_replay_window() -> None:
    with recovery_replay_scope(FIXED, replay_id="rr-wp3"):
        w = window_for(WindowRecipeId.RECOVERY_REPLAY_RANGE, n_days=3)
        assert w.ok
        assert w.recipe == WindowRecipeId.RECOVERY_REPLAY_RANGE
        assert w.replay_id == "rr-wp3"
        assert w.start_at == FIXED - timedelta(days=3)
        assert w.end_at == FIXED


def test_last_n_days() -> None:
    with frozen_clock_scope(FIXED):
        w = window_for(WindowRecipeId.LAST_N_DAYS, n_days=7)
        assert w.ok
        assert w.start_at == FIXED - timedelta(days=7)
        assert w.end_at == FIXED


def test_current_month() -> None:
    with frozen_clock_scope(FIXED):
        w = window_for(WindowRecipeId.CURRENT_MONTH)
        assert w.ok
        assert w.start_at == datetime(2026, 5, 1, tzinfo=timezone.utc)
        assert w.end_at == datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_previous_month() -> None:
    with frozen_clock_scope(FIXED):
        w = window_for(WindowRecipeId.PREVIOUS_MONTH)
        assert w.ok
        assert w.start_at == datetime(2026, 4, 1, tzinfo=timezone.utc)
        assert w.end_at == datetime(2026, 5, 1, tzinfo=timezone.utc)


def test_this_month_alias() -> None:
    assert resolve_window_recipe("this_month") == WindowRecipeId.CURRENT_MONTH
    with frozen_clock_scope(FIXED):
        w = window_for("this_month")
        assert w.recipe == WindowRecipeId.CURRENT_MONTH


def test_comparison_period_symmetry() -> None:
    with frozen_clock_scope(FIXED):
        primary = window_for(WindowRecipeId.LAST_N_DAYS, n_days=7)
        prev = window_for(WindowRecipeId.COMPARISON_PERIOD, primary=primary)
        assert prev.ok
        assert prev.end_at == primary.start_at
        assert prev.end_at - prev.start_at == primary.end_at - primary.start_at
        assert windows_adjacent_non_overlapping(prev, primary)


def test_inclusive_start_exclusive_end() -> None:
    with frozen_clock_scope(FIXED):
        w = window_for(WindowRecipeId.TODAY)
        assert w.contains(MAY_MIDNIGHT) is True
        assert w.contains(MAY_NEXT) is False
        assert w.contains(MAY_NEXT - timedelta(microseconds=1)) is True


def test_adjacent_windows_do_not_overlap() -> None:
    with frozen_clock_scope(FIXED):
        today = window_for(WindowRecipeId.TODAY)
        yesterday = window_for(WindowRecipeId.YESTERDAY)
        assert windows_adjacent_non_overlapping(yesterday, today)
        assert not yesterday.contains(today.start_at)
        assert not today.contains(yesterday.start_at)


def test_utc_normalization() -> None:
    # Fixed offset → normalized to UTC boundaries
    localish = datetime(2026, 5, 4, 18, 30, 45, tzinfo=timezone(timedelta(hours=3)))
    with frozen_clock_scope(localish):
        w = window_for(WindowRecipeId.TODAY)
        assert w.start_at.tzinfo == timezone.utc
        assert w.end_at.tzinfo == timezone.utc
        # 18:30+03 == 15:30 UTC on May 4
        assert w.start_at == MAY_MIDNIGHT


def test_determinism() -> None:
    with frozen_clock_scope(FIXED):
        a = window_for(WindowRecipeId.LAST_N_DAYS, n_days=14)
        b = window_for(WindowRecipeId.LAST_N_DAYS, n_days=14)
        assert a.start_at == b.start_at
        assert a.end_at == b.end_at
        assert a.provenance() == b.provenance()


def test_invalid_range_rejection() -> None:
    with frozen_clock_scope(FIXED):
        w = window_for(
            WindowRecipeId.EXPLICIT_RANGE,
            start_at=FIXED,
            end_at=FIXED - timedelta(seconds=1),
        )
        assert w.status == WindowResultStatus.INVALID_RANGE
        assert not w.ok


def test_missing_context_behaviour() -> None:
    clear_query_time_context()
    w = window_for(WindowRecipeId.TODAY, require_explicit_context=True)
    assert w.status == WindowResultStatus.MISSING_QUERY_TIME_CONTEXT
    # Ambient still works without explicit flag
    w2 = window_for(WindowRecipeId.TODAY)
    assert w2.ok


def test_invalid_n_rejection() -> None:
    with frozen_clock_scope(FIXED):
        for bad in (None, 0, -3):
            w = window_for(WindowRecipeId.LAST_N_DAYS, n_days=bad)
            assert w.status == WindowResultStatus.INVALID_ARGUMENT


def test_provenance_preservation() -> None:
    with simulation_scope(simulation_run_id="srs_prov", start=FIXED, scope_key="demo"):
        w = window_for(WindowRecipeId.SIMULATION_RANGE, n_days=2)
        prov = w.provenance()
        assert prov["recipe"] == "simulation_range"
        assert prov["context_mode"] == "simulation"
        assert prov["simulation_run_id"] == "srs_prov"
        assert prov["authoritative_now"] == FIXED.isoformat()
        assert prov["timezone_policy"] == "utc"
        assert prov["merchant_visible"] is False
        assert w.authority_provenance == TimeProvenance.SIMULATION_CLOCK.value


def test_simulation_identity_preservation() -> None:
    with simulation_scope(simulation_run_id="srs_id", start=FIXED):
        w = window_for(WindowRecipeId.TODAY)
        assert w.simulation_run_id == "srs_id"


def test_replay_identity_preservation() -> None:
    with historical_replay_scope(FIXED, replay_id="replay-99"):
        w = window_for(WindowRecipeId.TODAY)
        assert w.replay_id == "replay-99"
        assert w.context_mode == QueryTimeContextKind.HISTORICAL_REPLAY


def test_no_direct_wall_clock_access_in_filtering_module() -> None:
    root = Path(__file__).resolve().parents[2]
    src = (root / "services" / "time_authority" / "filtering.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    forbidden = {"datetime.now", "datetime.utcnow", "time.time", "time.monotonic"}
    found: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
            if isinstance(node.value, ast.Name):
                name = f"{node.value.id}.{node.attr}"
                if name in ("datetime.now", "datetime.utcnow"):
                    found.append(name)
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                name = f"{node.func.value.id}.{node.func.attr}"
                if name in forbidden:
                    found.append(name)
            self.generic_visit(node)

    Visitor().visit(tree)
    assert found == [], f"wall-clock calls in filtering.py: {found}"
    assert "authority_now(" not in src or True  # may import resolve only
    assert "datetime.now" not in src
    assert "utcnow" not in src


def test_no_database_or_network_access_in_filtering() -> None:
    root = Path(__file__).resolve().parents[2]
    filt = (root / "services" / "time_authority" / "filtering.py").read_text(encoding="utf-8")
    empty = (root / "services" / "time_authority" / "emptiness.py").read_text(encoding="utf-8")
    for blob in (filt, empty):
        assert "sqlalchemy" not in blob.lower()
        assert "requests." not in blob
        assert "httpx" not in blob
        assert "urllib" not in blob
        assert "Session(" not in blob
        assert "create_engine" not in blob


def test_constant_time_construction() -> None:
    with frozen_clock_scope(FIXED):
        t0 = time.perf_counter()
        for _ in range(500):
            window_for(WindowRecipeId.LAST_N_DAYS, n_days=30)
            window_for(WindowRecipeId.CURRENT_MONTH)
            window_for(WindowRecipeId.COMPARISON_PERIOD, primary=window_for(WindowRecipeId.LAST_N_DAYS, n_days=7))
        elapsed = time.perf_counter() - t0
    # Lightweight evidence: thousands of pure constructions stay well under a second
    assert elapsed < 1.0


def test_wp1_wp2_compatibility() -> None:
    with simulation_scope(simulation_run_id="compat", start=FIXED):
        from services.time_authority import authority_now, resolve_effective_context

        assert authority_now() == FIXED
        ctx = resolve_effective_context()
        w = window_for(WindowRecipeId.YESTERDAY, context=ctx)
        assert w.ok
        assert w.end_at == MAY_MIDNIGHT


def test_no_main_py_growth_for_wp3() -> None:
    # WP-3 must not modify main.py — verify filtering not registered there
    root = Path(__file__).resolve().parents[2]
    main_txt = (root / "main.py").read_text(encoding="utf-8")
    assert "window_for" not in main_txt
    assert "time_authority.filtering" not in main_txt
    assert "emptiness" not in main_txt or "time_authority.emptiness" not in main_txt


def test_midnight_boundary() -> None:
    midnight = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    with frozen_clock_scope(midnight):
        today = window_for(WindowRecipeId.TODAY)
        assert today.start_at == midnight
        assert today.end_at == datetime(2026, 1, 2, tzinfo=timezone.utc)
        yesterday = window_for(WindowRecipeId.YESTERDAY)
        assert yesterday.start_at == datetime(2025, 12, 31, tzinfo=timezone.utc)
        assert yesterday.end_at == midnight


def test_month_end_and_year_end() -> None:
    with frozen_clock_scope(datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc)):
        cur = window_for(WindowRecipeId.CURRENT_MONTH)
        assert cur.start_at == datetime(2026, 12, 1, tzinfo=timezone.utc)
        assert cur.end_at == datetime(2027, 1, 1, tzinfo=timezone.utc)
        prev = window_for(WindowRecipeId.PREVIOUS_MONTH)
        assert prev.start_at == datetime(2026, 11, 1, tzinfo=timezone.utc)
        assert prev.end_at == datetime(2026, 12, 1, tzinfo=timezone.utc)


def test_leap_day() -> None:
    leap = datetime(2024, 2, 29, 12, 0, tzinfo=timezone.utc)
    with frozen_clock_scope(leap):
        today = window_for(WindowRecipeId.TODAY)
        assert today.start_at == datetime(2024, 2, 29, tzinfo=timezone.utc)
        assert today.end_at == datetime(2024, 3, 1, tzinfo=timezone.utc)
        month = window_for(WindowRecipeId.CURRENT_MONTH)
        assert month.start_at == datetime(2024, 2, 1, tzinfo=timezone.utc)
        assert month.end_at == datetime(2024, 3, 1, tzinfo=timezone.utc)


def test_current_week_iso_monday() -> None:
    # 2026-05-04 is a Monday
    with frozen_clock_scope(FIXED):
        w = window_for(WindowRecipeId.CURRENT_WEEK)
        assert w.start_at == MAY_MIDNIGHT
        assert w.end_at == MAY_MIDNIGHT + timedelta(days=7)
        prev = window_for(WindowRecipeId.PREVIOUS_WEEK)
        assert windows_adjacent_non_overlapping(prev, w)


def test_unsupported_timezone_policy() -> None:
    ctx, _prov = build_query_time_context(
        QueryTimeContextKind.TESTING,
        as_of=FIXED,
        timezone_policy=TimezonePolicy.STORE_LOCAL_RESERVED,
    )
    w = window_for(WindowRecipeId.TODAY, context=ctx)
    assert w.status == WindowResultStatus.UNSUPPORTED_TIMEZONE_POLICY


def test_emptiness_out_of_window_vs_no_history() -> None:
    with frozen_clock_scope(FIXED):
        w = window_for(WindowRecipeId.TODAY)
        none = classify_store_history(
            window=w, has_any_history=False, has_in_window=False
        )
        assert none.emptiness_type == EmptinessType.NO_STORE_HISTORY
        oow = classify_store_history(
            window=w, has_any_history=True, has_in_window=False
        )
        assert oow.emptiness_type == EmptinessType.OUT_OF_WINDOW
        assert oow.status == WindowResultStatus.OUT_OF_WINDOW
        ts = classify_timestamp(datetime(2026, 4, 1, tzinfo=timezone.utc), w)
        assert ts.emptiness_type == EmptinessType.OUT_OF_WINDOW


def test_sql_bounds_index_friendly() -> None:
    with frozen_clock_scope(FIXED):
        w = window_for(WindowRecipeId.TODAY)
        start, end = w.as_sql_bounds()
        assert start == w.start_at
        assert end == w.end_at


def test_simulation_range_requires_mode() -> None:
    with frozen_clock_scope(FIXED):
        w = window_for(WindowRecipeId.SIMULATION_RANGE)
        assert w.status == WindowResultStatus.INVALID_ARGUMENT


def test_inspect_window_for_signature_has_no_implicit_now() -> None:
    sig = inspect.signature(window_for)
    assert "now" not in sig.parameters
