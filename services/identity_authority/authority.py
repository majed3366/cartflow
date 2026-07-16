# -*- coding: utf-8 -*-
"""
Platform Identity Authority — public resolve / bind façade (INV-002 WP-1).

Sole author of sealed MQIC for product use (IA-4).
No database queries. No merchant surface migration.
"""
from __future__ import annotations

from typing import Any, Optional

from services.identity_authority.contracts import AUTHORITY_SOURCE_ID
from services.identity_authority.context import (
    assert_mqic_active,
    bind_mqic,
    clear_mqic,
    get_mqic,
    mqic_scope,
    peek_resolve_count,
    require_mqic,
    reset_mqic,
)
from services.identity_authority.exceptions import IdentityError
from services.identity_authority.mqic import (
    MerchantQueryIdentityContext,
    reject_field_mutation,
)
from services.identity_authority.observability import (
    identity_context_metadata,
    record,
    resolution_provenance,
    reset_counters,
    snapshot_counters,
    violation_detection_snapshot,
)
from services.identity_authority.resolve import ResolveIdentityInput, resolve_mqic


def authority_source_id() -> str:
    """Stable Authority identity for provenance."""
    return AUTHORITY_SOURCE_ID


def resolve_and_bind(inp: ResolveIdentityInput) -> MerchantQueryIdentityContext:
    """
    Resolve MQIC once and bind into the current request scope (IA-2).

    Fail closed on IdentityError. Dual resolve raises DualResolveViolation.
    """
    try:
        mqic = resolve_mqic(inp)
        record("resolve_ok")
    except IdentityError:
        record("resolve_fail")
        raise
    bind_mqic(mqic)
    return mqic


def resolve_only(inp: ResolveIdentityInput) -> MerchantQueryIdentityContext:
    """
    Resolve without binding (tests / composition helpers).

    Prefer resolve_and_bind at request roots so IA-2 is enforced.
    """
    try:
        mqic = resolve_mqic(inp)
        record("resolve_ok")
        return mqic
    except IdentityError:
        record("resolve_fail")
        raise


def identity_diagnostics(
    mqic: Optional[MerchantQueryIdentityContext] = None,
) -> dict[str, Any]:
    """
    Ops diagnostics bundle — resolution provenance, authority source,
    context metadata, violation counters. Not merchant chrome.
    """
    active = mqic if mqic is not None else get_mqic()
    out: dict[str, Any] = {
        "authority_source": AUTHORITY_SOURCE_ID,
        "resolve_count": peek_resolve_count(),
        "context": identity_context_metadata(active),
        "violations": violation_detection_snapshot(),
        "counters": snapshot_counters(),
    }
    if active is not None:
        out["resolution_provenance"] = resolution_provenance(active)
    return out


__all__ = [
    "AUTHORITY_SOURCE_ID",
    "MerchantQueryIdentityContext",
    "ResolveIdentityInput",
    "assert_mqic_active",
    "authority_source_id",
    "bind_mqic",
    "clear_mqic",
    "get_mqic",
    "identity_diagnostics",
    "mqic_scope",
    "peek_resolve_count",
    "reject_field_mutation",
    "require_mqic",
    "reset_counters",
    "reset_mqic",
    "resolve_and_bind",
    "resolve_mqic",
    "resolve_only",
]
