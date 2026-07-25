# -*- coding: utf-8 -*-
"""
Business Fact Registry V1 — in-process index of extracted facts per store.

Not a durable DB table in V1. Provides stable lookup for routing / Home / Workspace.
"""
from __future__ import annotations

import threading
from typing import Any, Mapping, Optional

_LOCK = threading.Lock()
_REGISTRY: dict[str, dict[str, Any]] = {}


def register_business_facts_v1(
    store_slug: str, package: Mapping[str, Any]
) -> dict[str, Any]:
    slug = str(store_slug or "").strip()
    if not slug:
        return {"ok": False, "error": "store_slug_required"}
    facts = [f for f in list(package.get("facts") or []) if isinstance(f, Mapping)]
    by_id = {str(f.get("fact_id")): dict(f) for f in facts if f.get("fact_id")}
    entry = {
        "store_slug": slug,
        "package": dict(package),
        "by_id": by_id,
        "fact_ids": list(by_id.keys()),
        "count": len(by_id),
    }
    with _LOCK:
        _REGISTRY[slug] = entry
    return {"ok": True, "store_slug": slug, "count": len(by_id)}


def get_registered_business_facts_v1(store_slug: str) -> Optional[dict[str, Any]]:
    slug = str(store_slug or "").strip()
    if not slug:
        return None
    with _LOCK:
        entry = _REGISTRY.get(slug)
        return dict(entry) if entry else None


def clear_business_facts_registry_v1(store_slug: str | None = None) -> None:
    with _LOCK:
        if store_slug is None:
            _REGISTRY.clear()
        else:
            _REGISTRY.pop(str(store_slug).strip(), None)


__all__ = [
    "clear_business_facts_registry_v1",
    "get_registered_business_facts_v1",
    "register_business_facts_v1",
]
