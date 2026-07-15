# -*- coding: utf-8 -*-
"""
Platform Time Authority — public façade (WP-1 / WP-2).

Stable imports for future consumers.
Filtering / emptiness: WP-3. Consumer migration: later WPs. Simulation engine bind: WP-10.
"""
from __future__ import annotations

from services.time_authority.authority import (
    authority_now,
    authority_provenance,
    authority_source_id,
    bind_provider,
    clear_provider_override,
    get_provider,
    reset_provider,
    use_provider,
)
from services.time_authority.compat import (
    coerce_optional_now,
    is_using_system_clock,
    legacy_utc_now,
)
from services.time_authority.context_scope import (
    frozen_clock_scope,
    historical_replay_scope,
    peek_default_production,
    production_scope,
    recovery_replay_scope,
    request_scope,
    simulation_scope,
    worker_scope,
)
from services.time_authority.contracts import (
    ClockProvider,
    ClockSourceKind,
    EmptinessType,
    QueryTimeContextKind,
    TimeProvenance,
    TimezonePolicy,
    WindowRecipeId,
    ensure_utc,
    provenance_dict,
    provenance_for_kind,
    resolve_context_kind,
)
from services.time_authority.exceptions import (
    InvalidClockProvider,
    MissingQueryTimeContext,
    QueryTimeContextError,
    TimeAuthorityError,
)
from services.time_authority.http_middleware import (
    QueryTimeContextMiddleware,
    register_query_time_context_middleware,
)
from services.time_authority.providers import (
    FixedAsOfProvider,
    FrozenTestProvider,
    SimulationClockProvider,
    SystemClockProvider,
    default_system_provider,
    validate_provider,
)
from services.time_authority.query_context import (
    QueryTimeContext,
    activate_built_context,
    activate_query_time_context,
    build_default_production_context,
    build_query_time_context,
    clear_query_time_context,
    context_snapshot,
    get_query_time_context,
    require_query_time_context,
    resolve_effective_context,
)
from services.time_authority.validators import (
    assert_context_kind,
    assert_not_simulation_when_production_expected,
    assert_provider_valid,
    assert_query_time_context_active,
    assert_source_id,
)

__all__ = [
    # Authority
    "authority_now",
    "authority_provenance",
    "authority_source_id",
    "bind_provider",
    "clear_provider_override",
    "get_provider",
    "reset_provider",
    "use_provider",
    # Query context
    "QueryTimeContext",
    "QueryTimeContextKind",
    "TimeProvenance",
    "TimezonePolicy",
    "activate_query_time_context",
    "activate_built_context",
    "build_query_time_context",
    "build_default_production_context",
    "clear_query_time_context",
    "context_snapshot",
    "get_query_time_context",
    "require_query_time_context",
    "resolve_effective_context",
    "resolve_context_kind",
    "provenance_for_kind",
    # Scopes
    "production_scope",
    "request_scope",
    "worker_scope",
    "frozen_clock_scope",
    "historical_replay_scope",
    "recovery_replay_scope",
    "simulation_scope",
    "peek_default_production",
    # HTTP
    "QueryTimeContextMiddleware",
    "register_query_time_context_middleware",
    # Providers
    "ClockProvider",
    "ClockSourceKind",
    "SystemClockProvider",
    "FixedAsOfProvider",
    "FrozenTestProvider",
    "SimulationClockProvider",
    "default_system_provider",
    "validate_provider",
    # Compat
    "legacy_utc_now",
    "coerce_optional_now",
    "is_using_system_clock",
    # Contracts / validators / errors
    "WindowRecipeId",
    "EmptinessType",
    "ensure_utc",
    "provenance_dict",
    "assert_provider_valid",
    "assert_query_time_context_active",
    "assert_context_kind",
    "assert_source_id",
    "assert_not_simulation_when_production_expected",
    "TimeAuthorityError",
    "MissingQueryTimeContext",
    "InvalidClockProvider",
    "QueryTimeContextError",
]

__version__ = "2"
