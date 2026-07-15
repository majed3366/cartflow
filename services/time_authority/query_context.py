# -*- coding: utf-8 -*-
"""
Query Time Context — governed time mode + propagation binding (WP-1 / WP-2).

Carries which clock/mode is active and how authoritative now is resolved.
HTTP/worker scope helpers live in context_scope.py / http_middleware.py.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterator, Mapping, Optional
from uuid import uuid4

from services.time_authority import authority as authority_mod
from services.time_authority.contracts import (
    ClockProvider,
    QueryTimeContextKind,
    TimeProvenance,
    TimezonePolicy,
    ensure_utc,
    provenance_dict,
    provenance_for_kind,
    resolve_context_kind,
)
from services.time_authority.exceptions import (
    MissingQueryTimeContext,
    QueryTimeContextError,
)
from services.time_authority.providers import (
    FixedAsOfProvider,
    FrozenTestProvider,
    SimulationClockProvider,
    SystemClockProvider,
)


@dataclass(frozen=True)
class QueryTimeContext:
    """
    Immutable Query Time Context after creation.

    ``mode`` is the architecture kind (QueryTimeContextKind).
    ``authoritative_now`` is resolved at activation from the bound provider.
    """

    mode: QueryTimeContextKind
    source_id: str
    time_provenance: TimeProvenance
    authoritative_now: datetime
    timezone_policy: TimezonePolicy = TimezonePolicy.UTC
    as_of: Optional[datetime] = None
    simulation_run_id: str = ""
    replay_id: str = ""
    correlation_id: str = ""
    job_id: str = ""
    request_id: str = ""
    # Opaque isolation key (e.g. store slug) — not identity resolution (INV-002).
    scope_key: str = ""
    label: str = ""

    @property
    def kind(self) -> QueryTimeContextKind:
        """Alias for WP-1 compatibility."""
        return self.mode

    def internal_provenance(self) -> dict:
        """Internal-only provenance (not for merchant UI)."""
        return provenance_dict(
            source_id=self.source_id,
            context_kind=self.mode,
            authority_now=self.authoritative_now,
            time_provenance=self.time_provenance,
            correlation_id=self.correlation_id or self.request_id or self.job_id,
            timezone_policy=self.timezone_policy,
        )


_active_qtc: ContextVar[Optional[QueryTimeContext]] = ContextVar(
    "cartflow_query_time_context", default=None
)


def get_query_time_context() -> Optional[QueryTimeContext]:
    """Return the active Query Time Context, or None if ambient (no explicit activation)."""
    return _active_qtc.get()


def require_query_time_context() -> QueryTimeContext:
    """Return active context or raise."""
    ctx = get_query_time_context()
    if ctx is None:
        raise MissingQueryTimeContext("query_time_context_required")
    return ctx


def resolve_effective_context() -> QueryTimeContext:
    """
    Effective context for the current execution.

    Explicit activation wins. Otherwise returns a default production snapshot
    (SystemClock) without inventing simulation/replay behaviour.
    """
    active = get_query_time_context()
    if active is not None:
        return active
    return build_default_production_context()


def build_default_production_context(
    *,
    correlation_id: str = "",
    request_id: str = "",
    job_id: str = "",
    scope_key: str = "",
) -> QueryTimeContext:
    """Safe default: production + SystemClock. Does not activate."""
    prov = SystemClockProvider()
    now = prov.now()
    return QueryTimeContext(
        mode=QueryTimeContextKind.CURRENT_PRODUCTION,
        source_id=str(prov.source_id),
        time_provenance=TimeProvenance.SYSTEM_CLOCK,
        authoritative_now=now,
        timezone_policy=TimezonePolicy.UTC,
        correlation_id=(correlation_id or request_id or job_id or "")[:128],
        request_id=(request_id or "")[:128],
        job_id=(job_id or "")[:128],
        scope_key=(scope_key or "")[:255],
        label="default_production",
    )


def _provider_for_kind(
    kind: QueryTimeContextKind,
    *,
    as_of: Optional[datetime],
    simulation_start: Optional[datetime],
    simulation_run_id: str,
    provider: Optional[ClockProvider],
) -> ClockProvider:
    if provider is not None:
        return provider
    if kind == QueryTimeContextKind.CURRENT_PRODUCTION:
        return SystemClockProvider()
    if kind in (
        QueryTimeContextKind.HISTORICAL_REPLAY,
        QueryTimeContextKind.FUTURE_REPLAY,
        QueryTimeContextKind.RECOVERY_REPLAY,
    ):
        if as_of is None:
            raise QueryTimeContextError(f"{kind.value}_requires_as_of")
        return FixedAsOfProvider(as_of)
    if kind == QueryTimeContextKind.TESTING:
        if as_of is None:
            raise QueryTimeContextError("testing_requires_as_of_or_frozen_provider")
        return FrozenTestProvider(as_of)
    if kind == QueryTimeContextKind.SIMULATION:
        start = simulation_start or as_of
        if start is None:
            raise QueryTimeContextError("simulation_requires_start_or_as_of")
        if not (simulation_run_id or "").strip():
            raise QueryTimeContextError("simulation_requires_simulation_run_id")
        return SimulationClockProvider(start, run_id=simulation_run_id)
    raise QueryTimeContextError(f"unsupported_context_kind:{kind}")


def validate_context_args(
    kind: QueryTimeContextKind,
    *,
    as_of: Optional[datetime],
    simulation_run_id: str,
    replay_id: str,
) -> None:
    """Validate mode-specific required fields before activation."""
    if kind == QueryTimeContextKind.SIMULATION and not (simulation_run_id or "").strip():
        raise QueryTimeContextError("simulation_requires_simulation_run_id")
    if kind in (
        QueryTimeContextKind.HISTORICAL_REPLAY,
        QueryTimeContextKind.RECOVERY_REPLAY,
        QueryTimeContextKind.FUTURE_REPLAY,
    ):
        if as_of is None:
            raise QueryTimeContextError(f"{kind.value}_requires_as_of")
        # replay_id recommended; if omitted, derived later
        _ = replay_id
    if kind == QueryTimeContextKind.TESTING and as_of is None:
        raise QueryTimeContextError("testing_requires_as_of_or_frozen_provider")


def build_query_time_context(
    kind: object,
    *,
    as_of: Optional[datetime] = None,
    simulation_start: Optional[datetime] = None,
    simulation_run_id: str = "",
    replay_id: str = "",
    correlation_id: str = "",
    request_id: str = "",
    job_id: str = "",
    scope_key: str = "",
    label: str = "",
    timezone_policy: TimezonePolicy = TimezonePolicy.UTC,
    provider: Optional[ClockProvider] = None,
) -> tuple[QueryTimeContext, ClockProvider]:
    """
    Validate and build an immutable context + provider without activating.

    Returns (context, provider). Caller may activate via activate_built_context.
    """
    try:
        resolved = resolve_context_kind(kind)
    except ValueError as exc:
        raise QueryTimeContextError(str(exc)) from exc

    as_of_norm = ensure_utc(as_of) if as_of is not None else None
    sim_start = ensure_utc(simulation_start) if simulation_start is not None else None
    sim_run = (simulation_run_id or "").strip()
    rid = (replay_id or "").strip()
    if (
        resolved
        in (
            QueryTimeContextKind.HISTORICAL_REPLAY,
            QueryTimeContextKind.RECOVERY_REPLAY,
            QueryTimeContextKind.FUTURE_REPLAY,
        )
        and not rid
        and as_of_norm is not None
    ):
        rid = f"replay:{resolved.value}:{as_of_norm.isoformat()}"

    validate_context_args(
        resolved,
        as_of=as_of_norm,
        simulation_run_id=sim_run,
        replay_id=rid,
    )
    prov = _provider_for_kind(
        resolved,
        as_of=as_of_norm,
        simulation_start=sim_start,
        simulation_run_id=sim_run,
        provider=provider,
    )
    now = prov.now()
    corr = (correlation_id or request_id or job_id or "").strip()[:128]
    if not corr:
        corr = uuid4().hex[:16]
    ctx = QueryTimeContext(
        mode=resolved,
        source_id=str(prov.source_id),
        time_provenance=provenance_for_kind(resolved),
        authoritative_now=now,
        timezone_policy=timezone_policy,
        as_of=as_of_norm,
        simulation_run_id=sim_run,
        replay_id=rid[:128],
        correlation_id=corr,
        request_id=(request_id or "").strip()[:128],
        job_id=(job_id or "").strip()[:128],
        scope_key=(scope_key or "").strip()[:255],
        label=(label or "").strip()[:128],
    )
    return ctx, prov


@contextmanager
def activate_built_context(
    ctx: QueryTimeContext, provider: ClockProvider
) -> Iterator[QueryTimeContext]:
    """Activate a previously built context + provider; restore on exit."""
    qtc_token: Token = _active_qtc.set(ctx)
    prov_token = authority_mod.bind_provider(provider)
    try:
        yield ctx
    finally:
        authority_mod.reset_provider(prov_token)
        _active_qtc.reset(qtc_token)


@contextmanager
def activate_query_time_context(
    kind: object,
    *,
    as_of: Optional[datetime] = None,
    simulation_start: Optional[datetime] = None,
    simulation_run_id: str = "",
    replay_id: str = "",
    correlation_id: str = "",
    request_id: str = "",
    job_id: str = "",
    scope_key: str = "",
    label: str = "",
    timezone_policy: TimezonePolicy = TimezonePolicy.UTC,
    provider: Optional[ClockProvider] = None,
) -> Iterator[QueryTimeContext]:
    """
    Activate a Query Time Context and bind the matching Time Authority provider.

    Restores prior context and provider on exit (nested-safe via contextvars).
    """
    ctx, prov = build_query_time_context(
        kind,
        as_of=as_of,
        simulation_start=simulation_start,
        simulation_run_id=simulation_run_id,
        replay_id=replay_id,
        correlation_id=correlation_id,
        request_id=request_id,
        job_id=job_id,
        scope_key=scope_key,
        label=label,
        timezone_policy=timezone_policy,
        provider=provider,
    )
    with activate_built_context(ctx, prov) as active:
        yield active


def clear_query_time_context() -> None:
    """Clear explicit Query Time Context (ambient production authority remains)."""
    _active_qtc.set(None)


def context_snapshot() -> Mapping[str, Any]:
    """Debug/ops snapshot of effective context (internal)."""
    ctx = resolve_effective_context()
    return {
        "mode": ctx.mode.value,
        "source_id": ctx.source_id,
        "time_provenance": ctx.time_provenance.value,
        "authoritative_now": ctx.authoritative_now.isoformat(),
        "timezone_policy": ctx.timezone_policy.value,
        "simulation_run_id": ctx.simulation_run_id or None,
        "replay_id": ctx.replay_id or None,
        "correlation_id": ctx.correlation_id or None,
        "request_id": ctx.request_id or None,
        "job_id": ctx.job_id or None,
        "scope_key": ctx.scope_key or None,
        "explicit": get_query_time_context() is not None,
    }
