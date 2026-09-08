# -*- coding: utf-8 -*-
"""Server-owned tenant gate for Live Decision Hierarchy V1."""
from __future__ import annotations

from typing import Any, Mapping

from services.live_reality_lab_v1.gate_v1 import is_live_reality_lab_tenant


def live_decision_hierarchy_enabled_for_store_slug(store_slug: Any) -> bool:
    """True only for authenticated cf_live_reality_lab. No query-param path."""
    return is_live_reality_lab_tenant(store_slug=store_slug)


def live_decision_hierarchy_enabled_for_store(store: Any = None) -> bool:
    if store is None:
        return False
    return is_live_reality_lab_tenant(store=store)


def reject_client_spoof(*, authenticated_store_slug: Any, claimed_store_slug: Any) -> bool:
    """True when a client-claimed slug must be ignored."""
    auth = str(authenticated_store_slug or "").strip()
    claimed = str(claimed_store_slug or "").strip()
    if not claimed or claimed == auth:
        return False
    return True


def gate_payload(*, store_slug: Any, store: Any = None) -> dict[str, Any]:
    slug = str(store_slug or "").strip()[:191]
    if store is not None:
        enabled = is_live_reality_lab_tenant(store=store)
        if isinstance(store, Mapping):
            slug = str(store.get("zid_store_id") or slug).strip()[:191]
        else:
            slug = str(getattr(store, "zid_store_id", None) or slug).strip()[:191]
    else:
        enabled = is_live_reality_lab_tenant(store_slug=slug)
    return {
        "enabled": bool(enabled),
        "store_slug": slug,
        "gate": "live_reality_lab_v1" if enabled else "not_lab",
        "query_param_bypass": False,
        "frontend_tenant_spoof": False,
    }


__all__ = [
    "gate_payload",
    "live_decision_hierarchy_enabled_for_store",
    "live_decision_hierarchy_enabled_for_store_slug",
    "reject_client_spoof",
]
