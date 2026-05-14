# -*- coding: utf-8 -*-
"""Short TTL in-process cache for hot widget APIs (ready / public-config).

Reduces repeated DB + schema work when many storefront tabs poll these endpoints.
Not shared across processes — sufficient to absorb bursts on a single worker.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Optional

log = logging.getLogger("cartflow")

_TTL_READY_SEC = 20.0
_TTL_PUBLIC_SEC = 20.0
_MAX_ENTRIES = 400

_lock = threading.Lock()
_ready_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_public_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def widget_public_api_cache_enabled() -> bool:
    """Disabled during pytest (would return stale payloads across cases) or via env."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    v = (os.getenv("CARTFLOW_DISABLE_WIDGET_API_CACHE") or "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return False
    return True


def _trim(cache: dict[str, tuple[float, dict[str, Any]]]) -> None:
    if len(cache) <= _MAX_ENTRIES:
        return
    cache.clear()
    log.warning("cartflow_widget_public_cache: cleared (size cap %s)", _MAX_ENTRIES)


def ready_cache_key(store_slug: str, session_id: str) -> str:
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    return f"r:{ss}\x00{sid}"


def public_cache_key(store_slug: str, cart_total: Optional[float]) -> str:
    ss = (store_slug or "").strip()[:255]
    if cart_total is None:
        return f"p:{ss}\x00"
    try:
        ct = float(cart_total)
    except (TypeError, ValueError):
        ct = 0.0
    return f"p:{ss}\x00{ct:.4f}"


def ready_cache_get(key: str) -> Optional[dict[str, Any]]:
    if not widget_public_api_cache_enabled():
        return None
    now = time.monotonic()
    with _lock:
        item = _ready_cache.get(key)
        if not item:
            return None
        exp, payload = item
        if exp < now:
            del _ready_cache[key]
            return None
        log.info("[CF READY CACHE HIT]")
        return dict(payload)


def ready_cache_set(key: str, payload: dict[str, Any]) -> None:
    if not widget_public_api_cache_enabled():
        return
    now = time.monotonic()
    with _lock:
        _trim(_ready_cache)
        _ready_cache[key] = (now + _TTL_READY_SEC, dict(payload))


def public_cache_get(key: str) -> Optional[dict[str, Any]]:
    if not widget_public_api_cache_enabled():
        return None
    now = time.monotonic()
    with _lock:
        item = _public_cache.get(key)
        if not item:
            return None
        exp, payload = item
        if exp < now:
            del _public_cache[key]
            return None
        log.info("[CF PUBLIC CONFIG CACHE HIT]")
        return dict(payload)


def public_cache_set(key: str, payload: dict[str, Any]) -> None:
    if not widget_public_api_cache_enabled():
        return
    now = time.monotonic()
    with _lock:
        _trim(_public_cache)
        _public_cache[key] = (now + _TTL_PUBLIC_SEC, dict(payload))
