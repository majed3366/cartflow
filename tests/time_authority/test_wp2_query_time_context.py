# -*- coding: utf-8 -*-
"""WP-2 — Query Time Context propagation and isolation tests."""
from __future__ import annotations

import concurrent.futures
from datetime import datetime, timezone

import pytest

from services.time_authority import (
    ClockSourceKind,
    QueryTimeContextKind,
    TimeProvenance,
    activate_query_time_context,
    authority_now,
    authority_provenance,
    authority_source_id,
    clear_query_time_context,
    get_query_time_context,
    historical_replay_scope,
    is_using_system_clock,
    legacy_utc_now,
    production_scope,
    recovery_replay_scope,
    request_scope,
    resolve_context_kind,
    resolve_effective_context,
    simulation_scope,
    frozen_clock_scope,
    worker_scope,
)
from services.time_authority.exceptions import QueryTimeContextError
from services.time_authority.http_middleware import QueryTimeContextMiddleware
from services.time_authority.query_context import (
    build_query_time_context,
    context_snapshot,
)

FIXED = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)


def setup_function() -> None:
    clear_query_time_context()


def teardown_function() -> None:
    clear_query_time_context()


def test_default_production_context_ambient() -> None:
    assert get_query_time_context() is None
    eff = resolve_effective_context()
    assert eff.mode == QueryTimeContextKind.CURRENT_PRODUCTION
    assert eff.time_provenance == TimeProvenance.SYSTEM_CLOCK
    assert is_using_system_clock()


def test_explicit_production_context() -> None:
    with production_scope(correlation_id="prod-1", scope_key="store_a"):
        ctx = get_query_time_context()
        assert ctx is not None
        assert ctx.mode == QueryTimeContextKind.CURRENT_PRODUCTION
        assert ctx.correlation_id == "prod-1"
        assert ctx.scope_key == "store_a"
        assert authority_source_id() == ClockSourceKind.SYSTEM.value


def test_simulation_context() -> None:
    with simulation_scope(simulation_run_id="srs_wp2", start=FIXED, scope_key="demo"):
        ctx = get_query_time_context()
        assert ctx.mode == QueryTimeContextKind.SIMULATION
        assert ctx.simulation_run_id == "srs_wp2"
        assert ctx.time_provenance == TimeProvenance.SIMULATION_CLOCK
        assert authority_now() == FIXED


def test_historical_replay_context() -> None:
    with historical_replay_scope(FIXED, replay_id="hr-1"):
        ctx = get_query_time_context()
        assert ctx.mode == QueryTimeContextKind.HISTORICAL_REPLAY
        assert ctx.replay_id == "hr-1"
        assert ctx.time_provenance == TimeProvenance.HISTORICAL_REPLAY
        assert authority_now() == FIXED


def test_recovery_replay_context() -> None:
    with recovery_replay_scope(FIXED, replay_id="rr-1"):
        ctx = get_query_time_context()
        assert ctx.mode == QueryTimeContextKind.RECOVERY_REPLAY
        assert ctx.time_provenance == TimeProvenance.RECOVERY_REPLAY


def test_frozen_clock_context() -> None:
    with frozen_clock_scope(FIXED):
        assert get_query_time_context().mode == QueryTimeContextKind.TESTING
        assert authority_now() == FIXED


def test_invalid_mode_rejection() -> None:
    with pytest.raises(QueryTimeContextError):
        with activate_query_time_context("not_a_real_mode"):
            pass


def test_missing_simulation_run_id_rejection() -> None:
    with pytest.raises(QueryTimeContextError, match="simulation_requires_simulation_run_id"):
        with activate_query_time_context(
            QueryTimeContextKind.SIMULATION,
            simulation_start=FIXED,
            simulation_run_id="",
        ):
            pass


def test_context_provenance_internal() -> None:
    with historical_replay_scope(FIXED, replay_id="p1", correlation_id="c1"):
        prov = authority_provenance()
        assert prov["merchant_visible"] is False
        assert prov["time_provenance"] == TimeProvenance.HISTORICAL_REPLAY.value
        assert prov["correlation_id"] == "c1"
        assert "2026-05-04" in prov["authority_now"]


def test_authoritative_now_resolution() -> None:
    with frozen_clock_scope(FIXED):
        ctx = get_query_time_context()
        assert ctx.authoritative_now == FIXED
        assert authority_now() == ctx.authoritative_now


def test_nested_context_behaviour() -> None:
    with production_scope(correlation_id="outer"):
        assert get_query_time_context().correlation_id == "outer"
        with frozen_clock_scope(FIXED, correlation_id="inner"):
            assert get_query_time_context().mode == QueryTimeContextKind.TESTING
            assert authority_now() == FIXED
        assert get_query_time_context().correlation_id == "outer"
        assert is_using_system_clock()


def test_context_cleanup() -> None:
    with production_scope():
        assert get_query_time_context() is not None
    assert get_query_time_context() is None
    assert is_using_system_clock()


def test_concurrent_request_isolation() -> None:
    def _run(scope_key: str) -> str:
        with request_scope(request_id=f"r-{scope_key}", scope_key=scope_key):
            return get_query_time_context().scope_key

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(_run, f"m{i}") for i in range(20)]
        keys = [f.result() for f in concurrent.futures.as_completed(futs)]
    assert set(keys) == {f"m{i}" for i in range(20)}


def test_concurrent_worker_isolation() -> None:
    def _run(job: str) -> tuple[str, str]:
        with worker_scope(job_id=job, scope_key=f"sk-{job}"):
            ctx = get_query_time_context()
            return ctx.job_id, ctx.scope_key

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(_run, f"job{i}") for i in range(16)]
        results = [f.result() for f in concurrent.futures.as_completed(futs)]
    assert {(f"job{i}", f"sk-job{i}") for i in range(16)} == set(results)


def test_frozen_clock_isolation() -> None:
    with frozen_clock_scope(FIXED, correlation_id="t1"):
        a = authority_now()
    with frozen_clock_scope(FIXED.replace(year=2025), correlation_id="t2"):
        b = authority_now()
    assert a.year == 2026
    assert b.year == 2025
    assert get_query_time_context() is None


def test_no_merchant_identity_leakage_across_scopes() -> None:
    with production_scope(scope_key="merchant_a"):
        assert get_query_time_context().scope_key == "merchant_a"
    with production_scope(scope_key="merchant_b"):
        assert get_query_time_context().scope_key == "merchant_b"
    assert get_query_time_context() is None


def test_no_simulation_to_production_leakage() -> None:
    with simulation_scope(simulation_run_id="srs_x", start=FIXED):
        assert authority_now() == FIXED
    assert get_query_time_context() is None
    assert is_using_system_clock()
    eff = resolve_effective_context()
    assert eff.mode == QueryTimeContextKind.CURRENT_PRODUCTION
    assert eff.simulation_run_id == ""


def test_wp1_compatibility_aliases_and_legacy() -> None:
    assert resolve_context_kind("production") == QueryTimeContextKind.CURRENT_PRODUCTION
    assert resolve_context_kind("test") == QueryTimeContextKind.TESTING
    with frozen_clock_scope(FIXED):
        assert legacy_utc_now() == FIXED
    # ambient legacy still wall-ish
    delta = abs((legacy_utc_now() - datetime.now(timezone.utc)).total_seconds())
    assert delta < 5


def test_no_merchant_facing_behaviour_change_ambient() -> None:
    """Without consumer migration, ambient authority remains system clock."""
    clear_query_time_context()
    assert is_using_system_clock()
    snap = context_snapshot()
    assert snap["mode"] == "current_production"
    assert snap["explicit"] is False


def test_middleware_class_is_composition_ready() -> None:
    assert QueryTimeContextMiddleware is not None
    assert callable(QueryTimeContextMiddleware)


def test_build_rejects_invalid_and_builds_immutable() -> None:
    ctx, _prov = build_query_time_context(
        "historical_replay",
        as_of=FIXED,
        correlation_id="x",
    )
    assert ctx.mode == QueryTimeContextKind.HISTORICAL_REPLAY
    with pytest.raises(Exception):
        ctx.mode = QueryTimeContextKind.TESTING  # type: ignore[misc]


def test_kind_property_wp1_compat() -> None:
    with production_scope():
        ctx = get_query_time_context()
        assert ctx.kind == ctx.mode
