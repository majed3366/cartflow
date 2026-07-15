# -*- coding: utf-8 -*-
"""
Query Time Context scopes — request / worker / test / replay helpers (WP-2).

All scopes use contextvars via activate_query_time_context. No process-global
mutable clock state.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Optional
from uuid import uuid4

from services.time_authority.contracts import QueryTimeContextKind
from services.time_authority.query_context import (
    QueryTimeContext,
    activate_query_time_context,
    build_default_production_context,
)


def _corr(explicit: str = "") -> str:
    return (explicit or "").strip() or uuid4().hex[:16]


@contextmanager
def production_scope(
    *,
    correlation_id: str = "",
    request_id: str = "",
    job_id: str = "",
    scope_key: str = "",
    label: str = "production_scope",
) -> Iterator[QueryTimeContext]:
    """Explicit production mode (SystemClock). Safe default for HTTP/workers."""
    with activate_query_time_context(
        QueryTimeContextKind.CURRENT_PRODUCTION,
        correlation_id=_corr(correlation_id),
        request_id=request_id,
        job_id=job_id,
        scope_key=scope_key,
        label=label,
    ) as ctx:
        yield ctx


@contextmanager
def request_scope(
    *,
    request_id: str = "",
    correlation_id: str = "",
    scope_key: str = "",
) -> Iterator[QueryTimeContext]:
    """HTTP request-scoped production context."""
    rid = (request_id or "").strip() or uuid4().hex[:16]
    with production_scope(
        correlation_id=correlation_id or rid,
        request_id=rid,
        scope_key=scope_key,
        label="http_request",
    ) as ctx:
        yield ctx


@contextmanager
def worker_scope(
    *,
    job_id: str = "",
    correlation_id: str = "",
    scope_key: str = "",
) -> Iterator[QueryTimeContext]:
    """Background worker / scheduler job-scoped production context."""
    jid = (job_id or "").strip() or uuid4().hex[:16]
    with production_scope(
        correlation_id=correlation_id or jid,
        job_id=jid,
        scope_key=scope_key,
        label="worker_job",
    ) as ctx:
        yield ctx


@contextmanager
def frozen_clock_scope(
    as_of: datetime,
    *,
    correlation_id: str = "",
    label: str = "testing",
) -> Iterator[QueryTimeContext]:
    """Frozen TESTING Query Time Context (name avoids pytest ``test*`` collection)."""
    with activate_query_time_context(
        QueryTimeContextKind.TESTING,
        as_of=as_of,
        correlation_id=_corr(correlation_id),
        label=label,
    ) as ctx:
        yield ctx


@contextmanager
def historical_replay_scope(
    as_of: datetime,
    *,
    replay_id: str = "",
    correlation_id: str = "",
    scope_key: str = "",
) -> Iterator[QueryTimeContext]:
    with activate_query_time_context(
        QueryTimeContextKind.HISTORICAL_REPLAY,
        as_of=as_of,
        replay_id=replay_id,
        correlation_id=_corr(correlation_id),
        scope_key=scope_key,
        label="historical_replay",
    ) as ctx:
        yield ctx


@contextmanager
def recovery_replay_scope(
    as_of: datetime,
    *,
    replay_id: str = "",
    correlation_id: str = "",
    scope_key: str = "",
) -> Iterator[QueryTimeContext]:
    with activate_query_time_context(
        QueryTimeContextKind.RECOVERY_REPLAY,
        as_of=as_of,
        replay_id=replay_id,
        correlation_id=_corr(correlation_id),
        scope_key=scope_key,
        label="recovery_replay",
    ) as ctx:
        yield ctx


@contextmanager
def simulation_scope(
    *,
    simulation_run_id: str,
    start: datetime,
    correlation_id: str = "",
    scope_key: str = "",
) -> Iterator[QueryTimeContext]:
    """
    Simulation Query Time Context (WP-2).

    Does not replace store_reality_simulator.simulation_scope — that bind is WP-10.
    This only activates Time Authority simulation mode for callers that opt in.
    """
    with activate_query_time_context(
        QueryTimeContextKind.SIMULATION,
        simulation_start=start,
        simulation_run_id=simulation_run_id,
        correlation_id=_corr(correlation_id),
        scope_key=scope_key,
        label="simulation",
    ) as ctx:
        yield ctx


def peek_default_production(
    *,
    correlation_id: str = "",
    scope_key: str = "",
) -> QueryTimeContext:
    """Build default production context without activating (inspection / tests)."""
    return build_default_production_context(
        correlation_id=correlation_id,
        scope_key=scope_key,
    )


__all__ = [
    "production_scope",
    "request_scope",
    "worker_scope",
    "frozen_clock_scope",
    "historical_replay_scope",
    "recovery_replay_scope",
    "simulation_scope",
    "peek_default_production",
]
