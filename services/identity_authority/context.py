# -*- coding: utf-8 -*-
"""
Request-scoped MQIC propagation via contextvars (INV-002 WP-1).

IA-2: bind exactly once per request scope.
IA-3: bound MQIC is immutable; replacement with different identity is a violation.
HTTP middleware registration is WP-2 — this module is the foundation only.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator, Optional

from services.identity_authority.exceptions import (
    DualResolveViolation,
    IdentityImmutabilityViolation,
    IdentityOwnershipViolation,
    MissingMerchantQueryIdentityContext,
)
from services.identity_authority.mqic import (
    MerchantQueryIdentityContext,
    assert_immutable_fields_unchanged,
)
from services.identity_authority.observability import record as _obs_record

_active_mqic: ContextVar[Optional[MerchantQueryIdentityContext]] = ContextVar(
    "cartflow_merchant_query_identity_context", default=None
)
_resolve_count: ContextVar[int] = ContextVar(
    "cartflow_identity_resolve_count", default=0
)


def get_mqic() -> Optional[MerchantQueryIdentityContext]:
    """Return the active MQIC, or None if unbound."""
    return _active_mqic.get()


def require_mqic() -> MerchantQueryIdentityContext:
    """Return active MQIC or raise."""
    ctx = get_mqic()
    if ctx is None:
        raise MissingMerchantQueryIdentityContext("mqic_required")
    ctx.assert_authority_owned()
    return ctx


def peek_resolve_count() -> int:
    """How many successful resolves have been recorded in this scope."""
    return int(_resolve_count.get() or 0)


def bind_mqic(mqic: MerchantQueryIdentityContext) -> Token:
    """
    Bind MQIC for the current request/scope.

    Dual bind with a different identity → DualResolveViolation (IA-2 / IA-3).
    Dual bind with identical identity → DualResolveViolation (exactly once).
    """
    try:
        mqic.assert_authority_owned()
    except IdentityOwnershipViolation:
        _obs_record("ownership_violation")
        raise

    current = get_mqic()
    count = peek_resolve_count()
    if current is not None or count > 0:
        _obs_record("dual_resolve_violation")
        if current is not None:
            try:
                assert_immutable_fields_unchanged(current, mqic)
            except IdentityImmutabilityViolation:
                _obs_record("immutability_violation")
                raise
        raise DualResolveViolation("identity_already_resolved_for_request")

    token = _active_mqic.set(mqic)
    _resolve_count.set(count + 1)
    _obs_record("bind_ok")
    return token


def reset_mqic(token: Token) -> None:
    """Restore prior MQIC binding from bind_mqic token."""
    _active_mqic.reset(token)


def clear_mqic() -> None:
    """Clear active MQIC and resolve count (test / scope exit helper)."""
    _active_mqic.set(None)
    _resolve_count.set(0)
    _obs_record("clear_ok")


@contextmanager
def mqic_scope(mqic: MerchantQueryIdentityContext) -> Iterator[MerchantQueryIdentityContext]:
    """Activate MQIC for a block; restore prior binding on exit."""
    prior = get_mqic()
    prior_count = peek_resolve_count()
    # Fresh nested scope: temporarily clear so bind enforces once within scope.
    _active_mqic.set(None)
    _resolve_count.set(0)
    try:
        bind_mqic(mqic)
        yield mqic
    finally:
        _active_mqic.set(prior)
        _resolve_count.set(prior_count)


def assert_mqic_active() -> None:
    require_mqic()
