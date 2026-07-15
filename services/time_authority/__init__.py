# -*- coding: utf-8 -*-
"""
Platform Time Authority — public façade (WP-1).

Stable imports for future consumers. Do not import private provider internals
from outside this package unless extending providers.

WP-1: foundation only — no Knowledge/Dashboard/Timeline migration.
Filtering / emptiness / presentation recipes: WP-3 / WP-11.
HTTP context attach: WP-2.
Simulation Reality Engine bind: WP-10.
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
from services.time_authority.contracts import (
    ClockProvider,
    ClockSourceKind,
    EmptinessType,
    QueryTimeContextKind,
    WindowRecipeId,
    ensure_utc,
    provenance_dict,
)
from services.time_authority.exceptions import (
    InvalidClockProvider,
    MissingQueryTimeContext,
    QueryTimeContextError,
    TimeAuthorityError,
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
    activate_query_time_context,
    clear_query_time_context,
    get_query_time_context,
    require_query_time_context,
)
from services.time_authority.validators import (
    assert_context_kind,
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
    "activate_query_time_context",
    "clear_query_time_context",
    "get_query_time_context",
    "require_query_time_context",
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
    "TimeAuthorityError",
    "MissingQueryTimeContext",
    "InvalidClockProvider",
    "QueryTimeContextError",
]

__version__ = "1"
