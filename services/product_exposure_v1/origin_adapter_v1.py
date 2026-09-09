# -*- coding: utf-8 -*-
"""
Storefront Origin → platform adapter → StoreIdentityAlias → canonical Store.

Zid host matching lives here only. Core persist/ingest never inspects *.zid.store.
CORS allowlist is not tenant proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

from services.store_identity_v1 import (
    canonical_store_slug_on_row,
    extract_zid_permalink_from_url,
    is_widget_sandbox_slug,
    resolve_store_row_by_identifier,
)


@dataclass(frozen=True)
class OriginAdapterMatch:
    commerce_platform: str
    adapter: str
    identity_value: str


@dataclass(frozen=True)
class TenantAuthority:
    store: Any
    canonical_store_slug: str
    commerce_platform: str
    origin_matched_via: str
    payload_matched_via: str


def parse_origin_header(origin: Optional[str]) -> Optional[str]:
    o = (origin or "").strip().rstrip("/")
    return o or None


def origin_adapter_match(origin: str) -> Optional[OriginAdapterMatch]:
    """Map Origin to an identity value. Zid permalink extraction is adapter-only."""
    o = parse_origin_header(origin)
    if not o:
        return None
    try:
        parsed = urlparse(o)
    except ValueError:
        return None
    if parsed.scheme != "https":
        return None
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return None
    permalink = extract_zid_permalink_from_url(o)
    if permalink:
        return OriginAdapterMatch(
            commerce_platform="zid",
            adapter="zid_host",
            identity_value=permalink,
        )
    return OriginAdapterMatch(
        commerce_platform="unknown",
        adapter="exact_origin",
        identity_value=o,
    )


def resolve_tenant_authority(
    *,
    origin: Optional[str],
    payload_store_slug: str,
) -> tuple[Optional[TenantAuthority], Optional[str]]:
    """
    Returns (authority, error_code).

    error_code: missing_origin | invalid_origin | unknown_store |
                store_origin_mismatch | lab_tenant_forbidden
    """
    o = parse_origin_header(origin)
    if not o:
        return None, "missing_origin"
    match = origin_adapter_match(o)
    if match is None:
        return None, "invalid_origin"

    origin_row, origin_via = resolve_store_row_by_identifier(match.identity_value)
    if origin_row is None and match.adapter == "exact_origin":
        host = (urlparse(o).hostname or "").strip().lower()
        if host:
            origin_row, origin_via = resolve_store_row_by_identifier(host)
    if origin_row is None:
        return None, "unknown_store"

    payload_row, payload_via = resolve_store_row_by_identifier(payload_store_slug)
    if payload_row is None:
        return None, "unknown_store"
    if int(getattr(payload_row, "id", 0) or 0) != int(getattr(origin_row, "id", 0) or 0):
        return None, "store_origin_mismatch"

    canonical = canonical_store_slug_on_row(origin_row)
    if not canonical:
        return None, "unknown_store"
    if is_widget_sandbox_slug(canonical) or is_widget_sandbox_slug(payload_store_slug):
        return None, "lab_tenant_forbidden"

    return (
        TenantAuthority(
            store=origin_row,
            canonical_store_slug=canonical,
            commerce_platform=match.commerce_platform,
            origin_matched_via=origin_via,
            payload_matched_via=payload_via,
        ),
        None,
    )
