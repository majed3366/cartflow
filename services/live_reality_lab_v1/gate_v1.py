# -*- coding: utf-8 -*-
"""Live Reality Laboratory V1 — server-side identity gate."""
from __future__ import annotations

from typing import Any, Mapping

from services.live_reality_lab_v1.contract_v1 import (
    LAB_INTEGRATION_SOURCE,
    LAB_PRODUCTION_ALLOWLIST,
    LAB_STORE_SLUG,
)


def normalize_store_slug(store_slug: Any) -> str:
    return str(store_slug or "").strip()[:191]


def is_live_reality_lab_tenant(
    *,
    store_slug: Any = None,
    integration_source: Any = None,
    store: Any = None,
) -> bool:
    """
    True only for cf_live_reality_lab.

    Prefer authenticated ``store=`` row. Never trust client slug alone when
    a Store object is available.
    """
    slug = normalize_store_slug(store_slug)
    src_override = integration_source

    if store is not None:
        slug = normalize_store_slug(
            getattr(store, "zid_store_id", None)
            if not isinstance(store, Mapping)
            else store.get("zid_store_id")
        )
        src = (
            store.get("integration_source")
            if isinstance(store, Mapping)
            else getattr(store, "integration_source", None)
        )
        if src is not None:
            src_override = src

    if slug not in LAB_PRODUCTION_ALLOWLIST:
        return False
    if slug != LAB_STORE_SLUG:
        return False

    src_s = str(src_override or "").strip().lower()
    if not src_s:
        return True
    if src_s == LAB_INTEGRATION_SOURCE.lower():
        return True
    return False


def assert_lab_operation_allowed(
    *,
    authenticated_store_slug: Any,
    store: Any = None,
) -> None:
    """Raise ValueError if caller is not the live lab tenant."""
    auth = normalize_store_slug(authenticated_store_slug)
    if auth != LAB_STORE_SLUG:
        raise ValueError("live_reality_lab_unauthorized_tenant")
    if store is not None and not is_live_reality_lab_tenant(store=store):
        raise ValueError("live_reality_lab_identity_mismatch")
    if not is_live_reality_lab_tenant(
        store_slug=auth,
        store=store,
        integration_source=getattr(store, "integration_source", None)
        if store is not None and not isinstance(store, Mapping)
        else (store.get("integration_source") if isinstance(store, Mapping) else None),
    ):
        raise ValueError("live_reality_lab_gate_denied")


__all__ = [
    "assert_lab_operation_allowed",
    "is_live_reality_lab_tenant",
    "normalize_store_slug",
]
