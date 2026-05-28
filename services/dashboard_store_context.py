# -*- coding: utf-8 -*-
"""Canonical merchant dashboard Store row — same zid as runtime recovery (never latest Store.id)."""
from __future__ import annotations

from typing import Optional

from models import Store

DEFAULT_MERCHANT_DASHBOARD_STORE_SLUG = "demo"


def normalize_merchant_store_slug(raw: Optional[str]) -> Optional[str]:
    """Strip and reject placeholder slugs; None if empty."""
    s = (raw or "").strip()[:255]
    if not s or s in ("(dashboard_latest_store)", "(unknown)", "(null)"):
        return None
    return s


def resolve_dashboard_merchant_store_slug(
    *,
    query_slug: Optional[str] = None,
    body_slug: Optional[str] = None,
    header_slug: Optional[str] = None,
) -> str:
    """
    Merchant dashboard runtime-facing store key.
    Priority: query → POST body → header → authenticated merchant slug → demo.
    """
    for cand in (query_slug, body_slug, header_slug):
        n = normalize_merchant_store_slug(cand)
        if n:
            return n
    try:
        from services.merchant_auth_context import get_merchant_auth_store_slug

        auth = normalize_merchant_store_slug(get_merchant_auth_store_slug())
        if auth:
            return auth
    except Exception:  # noqa: BLE001
        pass
    return DEFAULT_MERCHANT_DASHBOARD_STORE_SLUG


def dashboard_canonical_store_row(
    store_slug: str,
    *,
    allow_schema_warm: bool = True,
) -> Optional[Store]:
    """Same Store row as runtime: resolve_recovery_store_row_canonical(store_slug)."""
    from services.recovery_store_lookup import resolve_recovery_store_row_canonical

    ss = resolve_dashboard_merchant_store_slug(query_slug=store_slug)
    return resolve_recovery_store_row_canonical(ss, allow_schema_warm=allow_schema_warm)
