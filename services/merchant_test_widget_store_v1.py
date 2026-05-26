# -*- coding: utf-8 -*-
"""
Merchant test-widget store scoping — never attach sandbox events to demo when authenticated.
"""
from __future__ import annotations

from typing import Any, Optional

from services.recovery_store_lookup import is_widget_recovery_zid

_PUBLIC_SANDBOX_SLUGS = frozenset({"demo", "demo2", "default"})


def is_public_widget_sandbox_slug(slug: str) -> bool:
    s = (slug or "").strip()
    if not s:
        return True
    if s.casefold() in _PUBLIC_SANDBOX_SLUGS:
        return True
    return is_widget_recovery_zid(s)


def merchant_authenticated_store_slug(
    *,
    cookies: Optional[dict[str, str]] = None,
) -> Optional[str]:
    """Primary store zid for logged-in merchant (onboarding resolver)."""
    if cookies is not None:
        from services.merchant_onboarding_store import (  # noqa: PLC0415
            resolve_merchant_onboarding_store,
        )

        store, _meta = resolve_merchant_onboarding_store(cookies=cookies)
        if store is None:
            return None
        zid = (getattr(store, "zid_store_id", None) or "").strip()[:255]
        if not zid or is_widget_recovery_zid(zid):
            return None
        return zid

    from services.merchant_auth_context import get_merchant_auth_store_slug  # noqa: PLC0415

    zid = (get_merchant_auth_store_slug() or "").strip()[:255]
    if not zid or is_widget_recovery_zid(zid):
        return None
    return zid


def coerce_cart_event_store_slug(slug_from_payload: str) -> str:
    """
    When a merchant session is active, never persist cart/recovery under demo/demo2/default.
  """
    raw = (slug_from_payload or "").strip()[:255]
    auth = merchant_authenticated_store_slug()
    if auth and is_public_widget_sandbox_slug(raw):
        return auth
    if raw:
        return raw
    return auth or "default"


def merchant_activation_requires_login(
    *,
    merchant_activation: bool,
    cookies: Optional[dict[str, str]],
) -> bool:
    if not merchant_activation:
        return False
    return merchant_authenticated_store_slug(cookies=cookies) is None
