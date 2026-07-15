# -*- coding: utf-8 -*-
"""
Platform Time Authority — sole acquisition of merchant-relevant 'now' (WP-1).

Binding uses contextvars so request/job/test scopes do not leak.
Default ambient provider is SystemClockProvider (production wall UTC).
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime
from typing import Iterator, Optional

from services.time_authority.contracts import ClockProvider, provenance_dict
from services.time_authority.exceptions import InvalidClockProvider
from services.time_authority.providers import default_system_provider, validate_provider

_active_provider: ContextVar[Optional[ClockProvider]] = ContextVar(
    "cartflow_time_authority_provider", default=None
)


def get_provider() -> ClockProvider:
    """Return the active clock provider (ambient default = system)."""
    bound = _active_provider.get()
    if bound is not None:
        return bound
    return default_system_provider()


def bind_provider(provider: ClockProvider) -> Token:
    """
    Bind a clock provider for the current context.

    Returns a token for reset_provider(token).
    """
    validate_provider(provider)
    return _active_provider.set(provider)


def reset_provider(token: Token) -> None:
    """Restore provider binding from bind_provider token."""
    _active_provider.reset(token)


def clear_provider_override() -> None:
    """Clear any override so ambient system provider is used."""
    _active_provider.set(None)


@contextmanager
def use_provider(provider: ClockProvider) -> Iterator[ClockProvider]:
    """Context manager: bind provider for the block, then restore."""
    token = bind_provider(provider)
    try:
        yield provider
    finally:
        reset_provider(token)


def authority_now() -> datetime:
    """
    Authoritative UTC 'now' for the active Time Authority source.

    Merchant-relevant stamp/filter decisions must use this (or windows built
    from it in WP-3+), not raw datetime.now().
    """
    provider = get_provider()
    try:
        return provider.now()
    except Exception as exc:  # noqa: BLE001
        raise InvalidClockProvider(f"authority_now_failed:{exc}") from exc


def authority_source_id() -> str:
    """Active clock source id for provenance."""
    return str(get_provider().source_id)


def authority_provenance(*, context_kind: Optional[object] = None) -> dict:
    """Provenance bundle (presentation consume later — WP-11)."""
    kind = None
    if context_kind is not None and hasattr(context_kind, "value"):
        kind = context_kind
    elif context_kind is not None:
        from services.time_authority.contracts import QueryTimeContextKind

        kind = QueryTimeContextKind(str(context_kind))
    return provenance_dict(
        source_id=authority_source_id(),
        context_kind=kind,
        authority_now=authority_now(),
    )
