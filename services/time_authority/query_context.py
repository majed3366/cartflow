# -*- coding: utf-8 -*-
"""
Query Time Context — binds kind + optional clock source for one execution (WP-1).

HTTP middleware attach is WP-2. This module provides the abstraction and
contextvars activation only.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Optional

from services.time_authority import authority as authority_mod
from services.time_authority.contracts import (
    ClockProvider,
    QueryTimeContextKind,
    ensure_utc,
)
from services.time_authority.exceptions import QueryTimeContextError
from services.time_authority.providers import (
    FixedAsOfProvider,
    FrozenTestProvider,
    SimulationClockProvider,
    SystemClockProvider,
)


@dataclass(frozen=True)
class QueryTimeContext:
    """Immutable description of the active query time binding."""

    kind: QueryTimeContextKind
    source_id: str
    as_of: Optional[datetime] = None
    simulation_run_id: str = ""
    label: str = ""


_active_qtc: ContextVar[Optional[QueryTimeContext]] = ContextVar(
    "cartflow_query_time_context", default=None
)


def get_query_time_context() -> Optional[QueryTimeContext]:
    """Return the active Query Time Context, or None if ambient (no explicit activation)."""
    return _active_qtc.get()


def require_query_time_context() -> QueryTimeContext:
    """Return active context or raise (validators / future merchant gates)."""
    from services.time_authority.exceptions import MissingQueryTimeContext

    ctx = get_query_time_context()
    if ctx is None:
        raise MissingQueryTimeContext("query_time_context_required")
    return ctx


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
        return SimulationClockProvider(start, run_id=simulation_run_id)
    raise QueryTimeContextError(f"unsupported_context_kind:{kind}")


@contextmanager
def activate_query_time_context(
    kind: QueryTimeContextKind,
    *,
    as_of: Optional[datetime] = None,
    simulation_start: Optional[datetime] = None,
    simulation_run_id: str = "",
    provider: Optional[ClockProvider] = None,
    label: str = "",
) -> Iterator[QueryTimeContext]:
    """
    Activate a Query Time Context and bind the matching Time Authority provider.

    Restores prior context and provider on exit.
    """
    if not isinstance(kind, QueryTimeContextKind):
        try:
            kind = QueryTimeContextKind(str(kind))
        except ValueError as exc:
            raise QueryTimeContextError(f"invalid_context_kind:{kind}") from exc

    as_of_norm = ensure_utc(as_of) if as_of is not None else None
    sim_start = ensure_utc(simulation_start) if simulation_start is not None else None
    prov = _provider_for_kind(
        kind,
        as_of=as_of_norm,
        simulation_start=sim_start,
        simulation_run_id=simulation_run_id,
        provider=provider,
    )
    ctx = QueryTimeContext(
        kind=kind,
        source_id=str(prov.source_id),
        as_of=as_of_norm,
        simulation_run_id=(simulation_run_id or "").strip(),
        label=(label or "").strip(),
    )
    qtc_token: Token = _active_qtc.set(ctx)
    prov_token = authority_mod.bind_provider(prov)
    try:
        yield ctx
    finally:
        authority_mod.reset_provider(prov_token)
        _active_qtc.reset(qtc_token)


def clear_query_time_context() -> None:
    """Clear explicit Query Time Context (ambient production authority remains)."""
    _active_qtc.set(None)
