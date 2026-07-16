# -*- coding: utf-8 -*-
"""
Dashboard/Home → Identity Authority consumer bridge (INV-002 WP-5).

Phase 4 surface: Dashboard/Home must not resolve merchant/store identity
independently. Tenant keys come from sealed MQIC owned by Identity Authority.

HTTP session → MQIC uses Phase 3 ``resolve_mqic_from_session`` (same lookup
class as Knowledge/Brief). Caller-supplied slug (snapshot activation attach)
is sealed via Authority with zero DB I/O.
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


def bind_mqic_for_dashboard_home(
    *,
    cookies: Optional[Mapping[str, str]] = None,
    explicit_store_slug: str = "",
) -> Optional[MerchantQueryIdentityContext]:
    """
    Bind MQIC for Dashboard/Home composition from the merchant session.

    Delegates to Phase 3 session & membership binding — no Home-local
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


def ensure_dashboard_home_mqic(
    *,
    store_slug: str = "",
    mqic: Optional[MerchantQueryIdentityContext] = None,
) -> MerchantQueryIdentityContext:
    """
    Resolve the MQIC Dashboard/Home must consume.

    Prefer active / passed MQIC. Never let Home invent a store.
    """
    active = mqic if mqic is not None else get_mqic()
    slug_in = (store_slug or "").strip()[:255]
    if active is not None:
        active.assert_authority_owned()
        if slug_in and slug_in != active.store_slug:
            raise IdentityError(
                "store_slug_mismatch",
                f"dashboard_home_slug_mismatch:{slug_in}!={active.store_slug}",
            )
        return active
    if not slug_in:
        raise MissingMerchantQueryIdentityContext("dashboard_home_requires_mqic")
    return mqic_from_caller_store_slug(slug_in)


@contextmanager
def dashboard_home_identity_scope(
    *,
    store_slug: str = "",
    mqic: Optional[MerchantQueryIdentityContext] = None,
) -> Iterator[MerchantQueryIdentityContext]:
    """
    Dashboard/Home composition scope: exactly one MQIC for the block.

    If MQIC already bound, validate and reuse (single resolve with Brief/Knowledge).
    If an unbound MQIC is passed, bind it once for the block.
    Otherwise seal caller slug via Authority for the block only
    (snapshot activation attach without a fresh session bind).
    """
    slug_in = (store_slug or "").strip()[:255]
    active = get_mqic()

    if mqic is not None:
        mqic.assert_authority_owned()
        if slug_in and slug_in != mqic.store_slug:
            raise IdentityError(
                "store_slug_mismatch",
                f"dashboard_home_slug_mismatch:{slug_in}!={mqic.store_slug}",
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
                f"dashboard_home_slug_mismatch:{mqic.store_slug}!={active.store_slug}",
            )
        yield active
        return

    if active is not None:
        active.assert_authority_owned()
        if slug_in and slug_in != active.store_slug:
            raise IdentityError(
                "store_slug_mismatch",
                f"dashboard_home_slug_mismatch:{slug_in}!={active.store_slug}",
            )
        yield active
        return

    if not slug_in:
        raise MissingMerchantQueryIdentityContext("dashboard_home_requires_mqic")
    created = mqic_from_caller_store_slug(slug_in)
    with mqic_scope(created) as bound:
        yield bound


def dashboard_home_identity_diagnostics(
    mqic: Optional[MerchantQueryIdentityContext] = None,
) -> dict[str, Any]:
    """Ops diagnostics for Dashboard/Home — not merchant chrome."""
    from services.identity_authority.authority import identity_diagnostics

    active = mqic if mqic is not None else get_mqic()
    base = identity_diagnostics(active)
    return {
        "authority_owner": AUTHORITY_SOURCE_ID,
        "authority_consumer": "dashboard_home",
        "dashboard_home_authority_source": AUTHORITY_SOURCE_ID,
        "resolution_path": (
            active.resolution_path.value if active is not None else None
        ),
        "identity_diagnostics": base,
    }


def attach_dashboard_home_identity_observability(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Attach internal identity observability to a Home API payload.

    Merchant UI must ignore ``identity_authority_v1`` (not a speech surface).
    """
    if not isinstance(payload, dict):
        return payload
    payload["identity_authority_v1"] = dashboard_home_identity_diagnostics()
    return payload


__all__ = [
    "attach_dashboard_home_identity_observability",
    "bind_mqic_for_dashboard_home",
    "dashboard_home_identity_diagnostics",
    "dashboard_home_identity_scope",
    "ensure_dashboard_home_mqic",
]
