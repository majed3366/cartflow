# -*- coding: utf-8 -*-
"""Short-lived Workspace paint cache — avoid request-time recomposition storms."""
from __future__ import annotations

import copy
import threading
import time
from typing import Any, Optional

_LOCK = threading.Lock()
_CACHE: dict[str, dict[str, Any]] = {}
TTL_SEC = 45.0


def workspace_paint_cache_get(store_slug: str) -> Optional[dict[str, Any]]:
    slug = str(store_slug or "").strip()
    if not slug:
        return None
    now = time.monotonic()
    with _LOCK:
        row = _CACHE.get(slug)
        if not row:
            return None
        if float(row.get("expires_at") or 0) <= now:
            _CACHE.pop(slug, None)
            return None
        proj = row.get("projection")
        if not isinstance(proj, dict):
            return None
        return copy.deepcopy(proj)


def workspace_paint_cache_set(store_slug: str, projection: dict[str, Any]) -> None:
    slug = str(store_slug or "").strip()
    if not slug or not isinstance(projection, dict):
        return
    with _LOCK:
        _CACHE[slug] = {
            "expires_at": time.monotonic() + TTL_SEC,
            "projection": copy.deepcopy(projection),
        }


def workspace_paint_cache_clear(store_slug: str | None = None) -> None:
    with _LOCK:
        if store_slug is None:
            _CACHE.clear()
            return
        _CACHE.pop(str(store_slug or "").strip(), None)


__all__ = [
    "TTL_SEC",
    "workspace_paint_cache_clear",
    "workspace_paint_cache_get",
    "workspace_paint_cache_set",
]
