# -*- coding: utf-8 -*-
"""WP-1 — Platform Time Authority foundation tests (no consumer migration)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.time_authority import (
    ClockSourceKind,
    FixedAsOfProvider,
    FrozenTestProvider,
    InvalidClockProvider,
    MissingQueryTimeContext,
    QueryTimeContextError,
    QueryTimeContextKind,
    SimulationClockProvider,
    SystemClockProvider,
    activate_query_time_context,
    assert_query_time_context_active,
    authority_now,
    authority_provenance,
    authority_source_id,
    bind_provider,
    clear_provider_override,
    clear_query_time_context,
    coerce_optional_now,
    get_provider,
    get_query_time_context,
    is_using_system_clock,
    legacy_utc_now,
    require_query_time_context,
    reset_provider,
    use_provider,
    validate_provider,
)


FIXED = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)


def setup_function() -> None:
    clear_provider_override()
    clear_query_time_context()


def teardown_function() -> None:
    clear_provider_override()
    clear_query_time_context()


# --- Platform construction / providers ---


def test_system_provider_returns_aware_utc() -> None:
    p = SystemClockProvider()
    n = p.now()
    assert n.tzinfo is not None
    assert p.source_id == ClockSourceKind.SYSTEM.value


def test_fixed_and_frozen_providers() -> None:
    assert FixedAsOfProvider(FIXED).now() == FIXED
    frozen = FrozenTestProvider(FIXED)
    assert frozen.now() == FIXED
    later = FIXED + timedelta(hours=1)
    frozen.set_now(later)
    assert frozen.now() == later


def test_simulation_provider_advance() -> None:
    sim = SimulationClockProvider(FIXED, run_id="srs_test")
    assert sim.source_id == ClockSourceKind.SIMULATION.value
    assert sim.run_id == "srs_test"
    sim.advance(seconds=60)
    assert sim.now() == FIXED + timedelta(seconds=60)


def test_validate_provider_rejects_bad() -> None:
    with pytest.raises(InvalidClockProvider):
        validate_provider(None)

    class Bad:
        source_id = "x"

        def now(self):
            return "nope"

    with pytest.raises(InvalidClockProvider):
        validate_provider(Bad())


# --- Authority / injection ---


def test_ambient_authority_uses_system() -> None:
    assert is_using_system_clock()
    assert authority_source_id() == ClockSourceKind.SYSTEM.value
    n = authority_now()
    assert n.tzinfo is not None


def test_bind_provider_and_reset() -> None:
    token = bind_provider(FrozenTestProvider(FIXED))
    try:
        assert authority_now() == FIXED
        assert authority_source_id() == ClockSourceKind.FROZEN_TEST.value
    finally:
        reset_provider(token)
    assert is_using_system_clock()


def test_use_provider_context_manager() -> None:
    with use_provider(FixedAsOfProvider(FIXED)):
        assert authority_now() == FIXED
    assert is_using_system_clock()


def test_provider_isolation_nested() -> None:
    a = FIXED
    b = FIXED + timedelta(days=1)
    with use_provider(FrozenTestProvider(a)):
        assert authority_now() == a
        with use_provider(FrozenTestProvider(b)):
            assert authority_now() == b
        assert authority_now() == a


# --- Query Time Context ---


def test_activate_testing_context() -> None:
    assert get_query_time_context() is None
    with activate_query_time_context(QueryTimeContextKind.TESTING, as_of=FIXED):
        ctx = get_query_time_context()
        assert ctx is not None
        assert ctx.kind == QueryTimeContextKind.TESTING
        assert authority_now() == FIXED
        assert_query_time_context_active()
        require_query_time_context()
    assert get_query_time_context() is None
    assert is_using_system_clock()


def test_historical_replay_requires_as_of() -> None:
    with pytest.raises(QueryTimeContextError):
        with activate_query_time_context(QueryTimeContextKind.HISTORICAL_REPLAY):
            pass


def test_historical_replay_fixed() -> None:
    with activate_query_time_context(
        QueryTimeContextKind.HISTORICAL_REPLAY, as_of=FIXED
    ):
        assert authority_now() == FIXED
        assert authority_source_id() == ClockSourceKind.FIXED_AS_OF.value


def test_simulation_context() -> None:
    with activate_query_time_context(
        QueryTimeContextKind.SIMULATION,
        simulation_start=FIXED,
        simulation_run_id="srs_wp1",
    ):
        ctx = require_query_time_context()
        assert ctx.kind == QueryTimeContextKind.SIMULATION
        assert ctx.simulation_run_id == "srs_wp1"
        assert authority_now() == FIXED


def test_current_production_context() -> None:
    with activate_query_time_context(QueryTimeContextKind.CURRENT_PRODUCTION):
        assert get_query_time_context().kind == QueryTimeContextKind.CURRENT_PRODUCTION
        assert authority_source_id() == ClockSourceKind.SYSTEM.value


def test_require_context_fails_when_absent() -> None:
    with pytest.raises(MissingQueryTimeContext):
        require_query_time_context()


def test_custom_provider_injection_on_context() -> None:
    custom = FrozenTestProvider(FIXED + timedelta(minutes=5))
    with activate_query_time_context(
        QueryTimeContextKind.TESTING,
        as_of=FIXED,
        provider=custom,
    ):
        assert authority_now() == FIXED + timedelta(minutes=5)


# --- Compatibility ---


def test_legacy_utc_now_follows_authority() -> None:
    with use_provider(FrozenTestProvider(FIXED)):
        assert legacy_utc_now() == FIXED
    # Ambient: close to wall (within a few seconds)
    delta = abs((legacy_utc_now() - datetime.now(timezone.utc)).total_seconds())
    assert delta < 5


def test_coerce_optional_now() -> None:
    with use_provider(FrozenTestProvider(FIXED)):
        assert coerce_optional_now(None) == FIXED
        other = FIXED + timedelta(days=2)
        assert coerce_optional_now(other) == other


# --- Provenance / interface ---


def test_authority_provenance() -> None:
    with activate_query_time_context(QueryTimeContextKind.TESTING, as_of=FIXED):
        prov = authority_provenance(context_kind=QueryTimeContextKind.TESTING)
        assert prov["time_authority_version"] == 1
        assert prov["clock_source_id"] == ClockSourceKind.FROZEN_TEST.value
        assert prov["query_time_context_kind"] == QueryTimeContextKind.TESTING.value
        assert "2026-05-04" in prov["authority_now"]


def test_get_provider_protocol_surface() -> None:
    p = get_provider()
    assert hasattr(p, "source_id")
    assert hasattr(p, "now")
    validate_provider(p)


def test_naive_datetime_normalized_on_fixed() -> None:
    naive = datetime(2026, 5, 1, 0, 0, 0)
    p = FixedAsOfProvider(naive)
    assert p.now().tzinfo is not None
