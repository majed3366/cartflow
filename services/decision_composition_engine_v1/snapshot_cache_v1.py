# -*- coding: utf-8 -*-
"""
Gate 2C — Decision Composition snapshot cache.

GET paths must never wait on counter rebuilds.
Serve last snapshot immediately; refresh in background (single-flight).
"""
from __future__ import annotations

import logging
import os
import threading
import time
from copy import deepcopy
from typing import Any, Callable, Mapping, Optional

log = logging.getLogger("cartflow")

ENV_DCE_CACHE_TTL = "CARTFLOW_DCE_SNAPSHOT_TTL_SEC"
ENV_DCE_CACHE_STALE = "CARTFLOW_DCE_SNAPSHOT_STALE_SEC"
ENV_DCE_CACHE_DISABLE = "CARTFLOW_DCE_SNAPSHOT_CACHE_OFF"

_DEFAULT_TTL = 45.0
_DEFAULT_STALE = 300.0
_MAX_ENTRIES = 256

_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}
_inflight: dict[str, threading.Thread] = {}


def _ttl() -> float:
    try:
        return max(5.0, float(os.environ.get(ENV_DCE_CACHE_TTL, _DEFAULT_TTL) or _DEFAULT_TTL))
    except (TypeError, ValueError):
        return _DEFAULT_TTL


def _stale_window() -> float:
    try:
        return max(
            _ttl(),
            float(os.environ.get(ENV_DCE_CACHE_STALE, _DEFAULT_STALE) or _DEFAULT_STALE),
        )
    except (TypeError, ValueError):
        return _DEFAULT_STALE


def snapshot_cache_enabled() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        # Tests call compose directly; cache off unless opted in.
        return str(os.environ.get("CARTFLOW_DCE_TEST_CACHE") or "").strip() in {
            "1",
            "true",
            "on",
            "yes",
        }
    raw = str(os.environ.get(ENV_DCE_CACHE_DISABLE, "0") or "0").strip().lower()
    return raw not in {"1", "true", "on", "yes"}


def _trim_unlocked() -> None:
    if len(_cache) <= _MAX_ENTRIES:
        return
    # Drop oldest by stored_at
    items = sorted(_cache.items(), key=lambda kv: float(kv[1].get("stored_at") or 0))
    for key, _ in items[: max(1, len(items) // 4)]:
        _cache.pop(key, None)


def cache_get(store_slug: str) -> Optional[dict[str, Any]]:
    """Return (package, age_sec, is_fresh) via wrapper — here just package meta."""
    if not snapshot_cache_enabled():
        return None
    slug = str(store_slug or "").strip()
    if not slug:
        return None
    now = time.monotonic()
    with _lock:
        item = _cache.get(slug)
        if not item:
            return None
        age = now - float(item.get("stored_at") or 0)
        if age > _stale_window():
            return None
        pkg = deepcopy(item.get("package") or {})
        pkg["_cache"] = {
            "hit": True,
            "age_sec": round(age, 3),
            "fresh": age <= _ttl(),
            "stale": age > _ttl(),
        }
        return pkg


def cache_set(store_slug: str, package: Mapping[str, Any]) -> None:
    if not snapshot_cache_enabled():
        return
    slug = str(store_slug or "").strip()
    if not slug or not isinstance(package, Mapping):
        return
    with _lock:
        _cache[slug] = {
            "stored_at": time.monotonic(),
            "package": deepcopy(dict(package)),
        }
        _trim_unlocked()


def cache_clear(store_slug: str | None = None) -> None:
    with _lock:
        if store_slug:
            _cache.pop(str(store_slug).strip(), None)
            _inflight.pop(str(store_slug).strip(), None)
        else:
            _cache.clear()
            _inflight.clear()


def _spawn_refresh(
    store_slug: str,
    composer: Callable[[], dict[str, Any]],
) -> None:
    slug = str(store_slug or "").strip()
    if not slug:
        return

    def _run() -> None:
        try:
            pkg = composer()
            if isinstance(pkg, dict):
                pkg = dict(pkg)
                pkg.pop("_cache", None)
                cache_set(slug, pkg)
        except Exception as exc:  # noqa: BLE001
            log.warning("dce_snapshot_refresh_failed store=%s err=%s", slug, exc)
        finally:
            with _lock:
                _inflight.pop(slug, None)

    with _lock:
        if slug in _inflight and _inflight[slug].is_alive():
            return
        t = threading.Thread(target=_run, name=f"dce-refresh-{slug[:24]}", daemon=True)
        _inflight[slug] = t
        t.start()


def get_or_compose_package_v1(
    store_slug: str,
    *,
    composer: Callable[[], dict[str, Any]],
    allow_sync_miss: bool = True,
) -> dict[str, Any]:
    """
    Stale-while-revalidate:

    - Fresh hit → return immediately
    - Stale hit → return immediately + background refresh
    - Miss → sync compose once (first paint) then cache
    """
    slug = str(store_slug or "").strip()
    cached = cache_get(slug)
    if cached is not None:
        meta = cached.get("_cache") or {}
        if meta.get("stale"):
            _spawn_refresh(slug, composer)
        return cached

    if not allow_sync_miss:
        empty = {
            "ok": True,
            "store_slug": slug,
            "decisions": [],
            "portfolio": [],
            "category_landscape": [],
            "suppression_registry": [],
            "counts": {
                "published": 0,
                "suppressed": 0,
                "needs_action_now": 0,
                "monitor": 0,
                "candidates_total": 0,
            },
            "no_decision_supported": True,
            "_cache": {"hit": False, "empty_placeholder": True},
        }
        _spawn_refresh(slug, composer)
        return empty

    t0 = time.perf_counter()
    pkg = composer()
    if not isinstance(pkg, dict):
        pkg = {"ok": False, "store_slug": slug, "decisions": []}
    else:
        pkg = dict(pkg)
    pkg.pop("_cache", None)
    cache_set(slug, pkg)
    out = deepcopy(pkg)
    out["_cache"] = {
        "hit": False,
        "fresh": True,
        "sync_miss_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }
    return out


__all__ = [
    "cache_clear",
    "cache_get",
    "cache_set",
    "get_or_compose_package_v1",
    "snapshot_cache_enabled",
]
