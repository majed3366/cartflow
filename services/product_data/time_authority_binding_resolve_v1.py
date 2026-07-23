# -*- coding: utf-8 -*-
"""
TABF V1 — thin resolve helpers (no Product Performance imports).

Keeps generate_* binding free of circular imports with the audit foundation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from services.product_data.time_authority_binding_flag_v1 import (
    time_authority_binding_v1_enabled,
)
from services.product_data.time_authority_binding_types_v1 import (
    CLOCK_DISPLAY,
    CLOCK_EVENT,
    CLOCK_OBSERVATION,
    CLOCK_PROCESSING,
    CLOCK_REPLAY,
)

log = logging.getLogger("cartflow")


def _floor_second(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0)


def resolve_bound_as_of_v1(as_of: Optional[datetime] = None) -> datetime:
    """
    Canonical observation/replay anchor for Product Performance generate_* calls.

    Precedence:
    1. Explicit as_of (caller/replay)
    2. Active Query Time Context authoritative_now
    3. Time Authority authority_now() (system or bound provider)
    """
    if as_of is not None:
        return _floor_second(as_of)

    if not time_authority_binding_v1_enabled():
        return _floor_second(datetime.now(timezone.utc).replace(tzinfo=None))

    try:
        from services.time_authority.query_context import get_query_time_context
        from services.time_authority.authority import authority_now

        ctx = get_query_time_context()
        if ctx is not None and ctx.authoritative_now is not None:
            return _floor_second(ctx.authoritative_now)
        return _floor_second(authority_now())
    except Exception as exc:  # noqa: BLE001
        log.warning("tabf resolve_bound_as_of fallback wall: %s", exc)
        return _floor_second(datetime.now(timezone.utc).replace(tzinfo=None))


def describe_time_binding_v1(as_of: Optional[datetime] = None) -> dict[str, Any]:
    """Provenance for probes / chronology cues."""
    from services.time_authority.authority import authority_source_id, get_provider
    from services.time_authority.query_context import get_query_time_context

    explicit = as_of is not None
    resolved = resolve_bound_as_of_v1(as_of)
    ctx = get_query_time_context()
    mode = str(ctx.mode.value) if ctx is not None else "ambient_or_default_production"
    source = "explicit_as_of" if explicit else (
        "query_time_context" if ctx is not None else "authority_now"
    )
    return {
        "resolved_as_of": resolved.isoformat(sep=" "),
        "source": source,
        "qtc_mode": mode,
        "authority_source_id": authority_source_id(),
        "provider": type(get_provider()).__name__,
        "binding_enabled": time_authority_binding_v1_enabled(),
        "clocks": {
            CLOCK_EVENT: "preserved_on_facts",
            CLOCK_PROCESSING: "authority_now_in_workers",
            CLOCK_OBSERVATION: "resolve_bound_as_of_v1",
            CLOCK_DISPLAY: "bound_as_of_via_scf_meif",
            CLOCK_REPLAY: "qtc_historical_or_simulation",
        },
    }


__all__ = ["resolve_bound_as_of_v1", "describe_time_binding_v1"]
