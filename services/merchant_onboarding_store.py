# -*- coding: utf-8 -*-
"""Resolve Store for merchant onboarding only — authenticated ownership, no fallbacks."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional

from extensions import db
from models import Store
from services.recovery_store_lookup import is_widget_recovery_zid

log = logging.getLogger("cartflow")


@dataclass
class MerchantOnboardingStoreResolution:
    merchant_id: Optional[int] = None
    user_email: str = ""
    store_id: Optional[int] = None
    store_slug: str = ""
    store_name: str = ""
    source: str = "unauthenticated"
    ready: bool = False
    completed_steps: int = 0

    def to_log_dict(self) -> dict[str, Any]:
        return asdict(self)


def merchant_store_display_name(
    store: Optional[Any],
    *,
    merchant_user: Optional[Any] = None,
) -> str:
    """Merchant-facing store label — never a demo slug as the name."""
    if store is not None:
        wn = (getattr(store, "widget_display_name", None) or "").strip()
        if wn:
            return wn[:255]
    if merchant_user is not None:
        mn = (getattr(merchant_user, "merchant_name", None) or "").strip()
        if mn:
            return mn[:255]
    return "متجرك"


def resolve_merchant_onboarding_store(
    *,
    cookies: Optional[dict[str, str]] = None,
) -> tuple[Optional[Store], MerchantOnboardingStoreResolution]:
    """
    Store row for onboarding/readiness UI only.

    - Requires valid merchant session cookie.
    - Uses ``primary_store_id`` / ``merchant_user_id`` on Store.
    - Rejects demo/default recovery slugs.
    - Never queries latest Store or anonymous fallbacks.
    """
    from services.merchant_auth_v1 import (
        get_merchant_user_by_id,
        get_primary_store_for_merchant,
        merchant_id_from_request_cookies,
    )

    meta = MerchantOnboardingStoreResolution()
    ck = cookies if cookies is not None else {}
    mid = merchant_id_from_request_cookies(ck)
    if not mid:
        meta.source = "unauthenticated"
        _log_resolution(meta)
        return None, meta

    meta.merchant_id = int(mid)
    user = get_merchant_user_by_id(int(mid))
    if user is None:
        meta.source = "merchant_user_not_found"
        _log_resolution(meta)
        return None, meta

    meta.user_email = (getattr(user, "email", None) or "").strip()

    store = get_primary_store_for_merchant(user)
    if store is None:
        meta.source = "no_store_for_merchant"
        meta.store_name = merchant_store_display_name(None, merchant_user=user)
        _log_resolution(meta)
        return None, meta

    zid = (getattr(store, "zid_store_id", None) or "").strip()
    meta.store_id = int(getattr(store, "id", 0) or 0) or None
    meta.store_slug = zid
    meta.store_name = merchant_store_display_name(store, merchant_user=user)

    owner_id = getattr(store, "merchant_user_id", None)
    if owner_id is not None and int(owner_id) != int(mid):
        meta.source = "ownership_mismatch"
        _log_resolution(meta)
        return None, meta

    if zid and is_widget_recovery_zid(zid):
        meta.source = "rejected_system_slug"
        _log_resolution(meta)
        return None, meta

    meta.source = "merchant_primary_store"
    _log_resolution(meta)
    return store, meta


def log_onboarding_flow_result(
    meta: MerchantOnboardingStoreResolution,
    *,
    ready: bool,
    completed_steps: int,
) -> None:
    meta.ready = ready
    meta.completed_steps = completed_steps
    _log_resolution(meta)


def _log_resolution(meta: MerchantOnboardingStoreResolution) -> None:
    d = meta.to_log_dict()
    log.info(
        "[ONBOARDING STORE RESOLUTION] merchant_id=%s user_email=%s store_id=%s "
        "store_slug=%s store_name=%s source=%s ready=%s completed_steps=%s",
        d.get("merchant_id"),
        d.get("user_email") or "",
        d.get("store_id"),
        d.get("store_slug") or "",
        d.get("store_name") or "",
        d.get("source") or "",
        d.get("ready"),
        d.get("completed_steps"),
    )


__all__ = [
    "MerchantOnboardingStoreResolution",
    "log_onboarding_flow_result",
    "merchant_store_display_name",
    "resolve_merchant_onboarding_store",
]
