# -*- coding: utf-8 -*-
"""
Knowledge → Identity Authority consumer bridge (INV-002 WP-2).

Knowledge must not resolve merchant/store identity independently.
All Knowledge tenant keys come from sealed MQIC owned by Identity Authority.

HTTP session → MQIC uses the same onboarding store lookup as the prior
Knowledge route auth path (no *additional* identity queries).
Caller-supplied slug (Home/Brief not yet migrated) is sealed via Authority
with zero DB I/O.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Optional

from services.identity_authority.contracts import (
    AUTHORITY_SOURCE_ID,
    CanonicalStoreIdentity,
)
from services.identity_authority.context import get_mqic, mqic_scope
from services.identity_authority.exceptions import (
    IdentityError,
    MissingMerchantQueryIdentityContext,
)
from services.identity_authority.mqic import MerchantQueryIdentityContext
from services.identity_authority.authority import resolve_only
from services.identity_authority.resolve import ResolveIdentityInput


def _canonical_from_slug(store_slug: str) -> CanonicalStoreIdentity:
    slug = (store_slug or "").strip()[:255]
    if not slug:
        raise IdentityError("store_slug_required", "store_slug_required")
    # Synthetic CartFlow-native id when caller already supplies the tenant slug
    # (no Store-row lookup — WP-2 forbids new identity DB queries).
    return CanonicalStoreIdentity(
        canonical_store_id=f"canonical:{slug}",
        store_slug=slug,
    )


def mqic_from_caller_store_slug(
    store_slug: str,
    *,
    merchant_id: str = "caller_supplied",
    correlation_id: str = "",
) -> MerchantQueryIdentityContext:
    """Seal caller-provided tenant slug through Authority (no DB)."""
    store = _canonical_from_slug(store_slug)
    return resolve_only(
        ResolveIdentityInput(
            merchant_id=(merchant_id or "caller_supplied").strip() or "caller_supplied",
            stores_by_id={store.canonical_store_id: store},
            membership_store_ids=frozenset({store.canonical_store_id}),
            primary_store_id=store.canonical_store_id,
            correlation_id=correlation_id,
        )
    )


def bind_mqic_from_merchant_session(
    *,
    cookies: Optional[Mapping[str, str]] = None,
    explicit_store_slug: str = "",
) -> Optional[MerchantQueryIdentityContext]:
    """
    Bind MQIC for a Knowledge HTTP request from the merchant session.

    INV-002 WP-3: delegates to Phase 3 session & membership binding
    (``resolve_mqic_from_session``). No Knowledge-local identity authorship.
    """
    from services.identity_authority.session_membership_v1 import (  # noqa: PLC0415
        resolve_mqic_from_session,
    )

    return resolve_mqic_from_session(
        cookies=cookies,
        explicit_store_slug=explicit_store_slug,
        bind=True,
    )


def ensure_knowledge_mqic(
    *,
    store_slug: str = "",
    mqic: Optional[MerchantQueryIdentityContext] = None,
) -> MerchantQueryIdentityContext:
    """
    Resolve the MQIC Knowledge must consume.

    Prefer active / passed MQIC. Never let Knowledge invent a store.
    """
    active = mqic if mqic is not None else get_mqic()
    slug_in = (store_slug or "").strip()[:255]
    if active is not None:
        active.assert_authority_owned()
        if slug_in and slug_in != active.store_slug:
            raise IdentityError(
                "store_slug_mismatch",
                f"knowledge_slug_mismatch:{slug_in}!={active.store_slug}",
            )
        return active
    if not slug_in:
        raise MissingMerchantQueryIdentityContext("knowledge_requires_mqic")
    return mqic_from_caller_store_slug(slug_in)


@contextmanager
def knowledge_identity_scope(
    *,
    store_slug: str = "",
    mqic: Optional[MerchantQueryIdentityContext] = None,
) -> Iterator[MerchantQueryIdentityContext]:
    """
    Knowledge request/report scope: exactly one MQIC for the block.

    If MQIC already bound (e.g. Knowledge route), validate and reuse.
    If an unbound MQIC is passed, bind it once for the block.
    Otherwise seal caller slug via Authority for the block only.
    """
    slug_in = (store_slug or "").strip()[:255]
    active = get_mqic()

    if mqic is not None:
        mqic.assert_authority_owned()
        if slug_in and slug_in != mqic.store_slug:
            raise IdentityError(
                "store_slug_mismatch",
                f"knowledge_slug_mismatch:{slug_in}!={mqic.store_slug}",
            )
        if active is None:
            with mqic_scope(mqic) as bound:
                yield bound
            return
        if (
            active.store_slug != mqic.store_slug
            or active.canonical_store_id != mqic.canonical_store_id
        ):
            raise IdentityError(
                "store_slug_mismatch",
                f"knowledge_slug_mismatch:{mqic.store_slug}!={active.store_slug}",
            )
        yield active
        return

    if active is not None:
        active.assert_authority_owned()
        if slug_in and slug_in != active.store_slug:
            raise IdentityError(
                "store_slug_mismatch",
                f"knowledge_slug_mismatch:{slug_in}!={active.store_slug}",
            )
        yield active
        return

    if not slug_in:
        raise MissingMerchantQueryIdentityContext("knowledge_requires_mqic")
    created = mqic_from_caller_store_slug(slug_in)
    with mqic_scope(created) as bound:
        yield bound


def knowledge_identity_diagnostics(
    mqic: Optional[MerchantQueryIdentityContext] = None,
) -> dict[str, Any]:
    """Ops diagnostics for Knowledge — not merchant chrome."""
    from services.identity_authority.authority import identity_diagnostics

    active = mqic if mqic is not None else get_mqic()
    base = identity_diagnostics(active)
    return {
        "authority_owner": AUTHORITY_SOURCE_ID,
        "authority_consumer": "knowledge",
        "knowledge_authority_source": AUTHORITY_SOURCE_ID,
        "resolution_path": (
            active.resolution_path.value if active is not None else None
        ),
        "identity_diagnostics": base,
    }


def attach_knowledge_identity_observability(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Attach internal identity observability to a Knowledge API payload.

    Merchant UI must ignore ``identity_authority_v1`` (not a speech surface).
    """
    if not isinstance(payload, dict):
        return payload
    payload["identity_authority_v1"] = knowledge_identity_diagnostics()
    return payload


__all__ = [
    "attach_knowledge_identity_observability",
    "bind_mqic_from_merchant_session",
    "ensure_knowledge_mqic",
    "knowledge_identity_diagnostics",
    "knowledge_identity_scope",
    "mqic_from_caller_store_slug",
]
