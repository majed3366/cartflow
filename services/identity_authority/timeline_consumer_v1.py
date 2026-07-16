# -*- coding: utf-8 -*-
"""
Timeline → Identity Authority consumer bridge (INV-002 WP-6).

Merchant Timeline must not resolve merchant/store identity independently.
All Timeline tenant keys come from sealed MQIC owned by Identity Authority.

HTTP session → MQIC uses Phase 3 ``resolve_mqic_from_session`` (same lookup
class as Knowledge/Brief/Home). Caller-supplied slug is sealed via Authority
with zero DB I/O.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Optional

from services.identity_authority.contracts import AUTHORITY_SOURCE_ID
from services.identity_authority.context import get_mqic, mqic_scope
from services.identity_authority.exceptions import (
    IdentityError,
    MissingMerchantQueryIdentityContext,
)
from services.identity_authority.knowledge_consumer_v1 import mqic_from_caller_store_slug
from services.identity_authority.mqic import MerchantQueryIdentityContext


def bind_mqic_for_timeline(
    *,
    cookies: Optional[Mapping[str, str]] = None,
    explicit_store_slug: str = "",
) -> Optional[MerchantQueryIdentityContext]:
    """
    Bind MQIC for Timeline from the merchant session.

    Delegates to Phase 3 session & membership binding — no Timeline-local
    identity authorship.
    """
    from services.identity_authority.session_membership_v1 import (  # noqa: PLC0415
        resolve_mqic_from_session,
    )

    return resolve_mqic_from_session(
        cookies=cookies,
        explicit_store_slug=explicit_store_slug,
        bind=True,
    )


def ensure_timeline_mqic(
    *,
    store_slug: str = "",
    mqic: Optional[MerchantQueryIdentityContext] = None,
) -> MerchantQueryIdentityContext:
    """
    Resolve the MQIC Timeline must consume.

    Prefer active / passed MQIC. Never let Timeline invent a store.
    """
    active = mqic if mqic is not None else get_mqic()
    slug_in = (store_slug or "").strip()[:255]
    if active is not None:
        active.assert_authority_owned()
        if slug_in and slug_in != active.store_slug:
            raise IdentityError(
                "store_slug_mismatch",
                f"timeline_slug_mismatch:{slug_in}!={active.store_slug}",
            )
        return active
    if not slug_in:
        raise MissingMerchantQueryIdentityContext("timeline_requires_mqic")
    return mqic_from_caller_store_slug(slug_in)


@contextmanager
def timeline_identity_scope(
    *,
    store_slug: str = "",
    mqic: Optional[MerchantQueryIdentityContext] = None,
) -> Iterator[MerchantQueryIdentityContext]:
    """
    Timeline build/read scope: exactly one MQIC for the block.

    If MQIC already bound (e.g. Home composition), validate and reuse.
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
                f"timeline_slug_mismatch:{slug_in}!={mqic.store_slug}",
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
                f"timeline_slug_mismatch:{mqic.store_slug}!={active.store_slug}",
            )
        yield active
        return

    if active is not None:
        active.assert_authority_owned()
        if slug_in and slug_in != active.store_slug:
            raise IdentityError(
                "store_slug_mismatch",
                f"timeline_slug_mismatch:{slug_in}!={active.store_slug}",
            )
        yield active
        return

    if not slug_in:
        raise MissingMerchantQueryIdentityContext("timeline_requires_mqic")
    created = mqic_from_caller_store_slug(slug_in)
    with mqic_scope(created) as bound:
        yield bound


def timeline_identity_diagnostics(
    mqic: Optional[MerchantQueryIdentityContext] = None,
) -> dict[str, Any]:
    """Ops diagnostics for Timeline — not merchant chrome."""
    from services.identity_authority.authority import identity_diagnostics

    active = mqic if mqic is not None else get_mqic()
    base = identity_diagnostics(active)
    return {
        "authority_owner": AUTHORITY_SOURCE_ID,
        "authority_consumer": "timeline",
        "timeline_authority_source": AUTHORITY_SOURCE_ID,
        "resolution_path": (
            active.resolution_path.value if active is not None else None
        ),
        "identity_diagnostics": base,
        "violation_detection": {
            "dual_resolve": "enforced",
            "immutability": "enforced",
            "store_slug_mismatch": "fail_closed",
        },
    }


def attach_timeline_identity_observability(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Attach internal identity observability to a Timeline payload.

    Merchant UI must ignore ``identity_authority_v1`` (not a speech surface).
    """
    if not isinstance(payload, dict):
        return payload
    payload["identity_authority_v1"] = timeline_identity_diagnostics()
    return payload


__all__ = [
    "attach_timeline_identity_observability",
    "bind_mqic_for_timeline",
    "ensure_timeline_mqic",
    "timeline_identity_diagnostics",
    "timeline_identity_scope",
]
