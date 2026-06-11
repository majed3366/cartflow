# -*- coding: utf-8 -*-
"""Canonical merchant dashboard Store row — same zid as runtime recovery (never latest Store.id)."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from models import Store

DEFAULT_MERCHANT_DASHBOARD_STORE_SLUG = "demo"
_WIDGET_PLACEHOLDER_SLUGS = frozenset({"demo", "demo2", "default"})


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
    """Same Store row as runtime: exact zid lookup via resolve_recovery_store_row_canonical."""
    from services.recovery_store_lookup import resolve_recovery_store_row_canonical

    ss = normalize_merchant_store_slug(store_slug)
    if not ss:
        return None
    return resolve_recovery_store_row_canonical(ss, allow_schema_warm=allow_schema_warm)


def resolve_dashboard_trigger_templates_store(
    *,
    query_slug: Optional[str] = None,
    body: Optional[Dict[str, Any]] = None,
    header_slug: Optional[str] = None,
    allow_schema_warm: bool = True,
) -> Tuple[str, Optional[Store]]:
    """
    Store row for trigger-template GET/POST — aligned with _dashboard_recovery_store_row.

    When the client sends a widget placeholder slug (demo) but the merchant session is
    authenticated to a real store, persist on the authenticated store row.
    """
    body_slug = body.get("store_slug") if isinstance(body, dict) else None
    canon = resolve_dashboard_merchant_store_slug(
        query_slug=query_slug,
        body_slug=body_slug,
        header_slug=header_slug,
    )
    row = dashboard_canonical_store_row(canon, allow_schema_warm=allow_schema_warm)

    auth: Optional[str] = None
    try:
        from services.merchant_auth_context import get_merchant_auth_store_slug

        auth = normalize_merchant_store_slug(get_merchant_auth_store_slug())
    except Exception:  # noqa: BLE001
        auth = None

    if auth and auth not in _WIDGET_PLACEHOLDER_SLUGS:
        if row is None or canon in _WIDGET_PLACEHOLDER_SLUGS:
            auth_row = dashboard_canonical_store_row(auth, allow_schema_warm=allow_schema_warm)
            if auth_row is not None:
                row = auth_row
                canon = auth

    return canon, row


def dashboard_recovery_store_row(*, allow_schema_warm: bool = False) -> Optional[Store]:
    """
    Authenticated merchant Store for dashboard saves/reads.
    Matches ``main._dashboard_recovery_store_row`` (dev bypass → demo sandbox).
    """
    try:
        from services.merchant_auth_context import get_merchant_auth_store_slug
        from services.merchant_auth_v1 import development_dashboard_bypass_active

        slug = normalize_merchant_store_slug(get_merchant_auth_store_slug())
        if slug:
            row = dashboard_canonical_store_row(slug, allow_schema_warm=allow_schema_warm)
            if row is not None:
                return row
        if development_dashboard_bypass_active():
            return dashboard_canonical_store_row(
                DEFAULT_MERCHANT_DASHBOARD_STORE_SLUG,
                allow_schema_warm=allow_schema_warm,
            )
    except Exception:  # noqa: BLE001
        pass
    return None
