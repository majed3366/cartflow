# -*- coding: utf-8 -*-
"""لقطات حالة ‎SQLAlchemy QueuePool‎ — تشخيص ضغط الاتصالات دون تغيير السلوك."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

log = logging.getLogger("cartflow")

_top_store_id_cache: Optional[int] = None
_top_store_id_cached: bool = False


def pool_status_snapshot() -> Dict[str, Any]:
    """أرقام المسبح الحالية (غير متاحة على ‎NullPool‎ / SQLite اختبارات)."""
    try:
        from extensions import db

        pool = db.engine.pool
        status_fn = getattr(pool, "status", None)
        if callable(status_fn):
            st = status_fn()
            return {
                "pool_impl": type(pool).__name__,
                "status": str(st),
            }
        return {
            "pool_impl": type(pool).__name__,
            "size": getattr(pool, "size", lambda: None)(),
            "checkedin": getattr(pool, "checkedin", lambda: None)(),
            "checkedout": getattr(pool, "checkedout", lambda: None)(),
            "overflow": getattr(pool, "overflow", lambda: None)(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"pool_impl": "unknown", "error": str(exc)[:200]}


def build_db_pool_health_snapshot() -> Dict[str, Any]:
    """
    Canonical pool pressure snapshot for admin ops and deployment gates.

    Fields: size, checked_out, overflow, max_connections, available_slots,
    timeout_count, exhausted, pool_class.
    """
    try:
        from services.admin_operational_health import (
            get_db_pool_snapshot_readonly,
            get_operational_counter_snapshots,
        )

        snap = get_db_pool_snapshot_readonly()
        counters = get_operational_counter_snapshots()
    except Exception as exc:  # noqa: BLE001
        return {
            "available": False,
            "error": str(exc)[:200],
            "timeout_count": 0,
            "exhausted": False,
        }

    metrics = dict(snap.get("metrics") or {})
    size = metrics.get("size")
    checked_out = metrics.get("checked_out")
    overflow = metrics.get("overflow")
    pool_class = metrics.get("pool_class") or snap.get("pool_class")

    max_connections: Optional[int] = None
    available_slots: Optional[int] = None
    if size is not None:
        try:
            max_connections = int(size) + int(overflow or 0)
        except (TypeError, ValueError):
            max_connections = int(size)
    if max_connections is not None and checked_out is not None:
        try:
            available_slots = max(0, int(max_connections) - int(checked_out))
        except (TypeError, ValueError):
            available_slots = None

    timeout_count = int(counters.get("pool_timeout_count") or 0)
    exhausted = False
    if timeout_count > 0:
        exhausted = True
    elif (
        max_connections is not None
        and checked_out is not None
        and int(checked_out) >= int(max_connections)
    ):
        exhausted = True

    return {
        "available": bool(snap.get("available")),
        "pool_class": pool_class,
        "size": size,
        "checked_out": checked_out,
        "overflow": overflow,
        "max_connections": max_connections,
        "available_slots": available_slots,
        "timeout_count": timeout_count,
        "exhausted": exhausted,
        "summary_ar": snap.get("summary_ar"),
    }


def log_pool_checkpoint(tag: str, **extra: Any) -> Dict[str, Any]:
    snap = pool_status_snapshot()
    if extra:
        snap = {**snap, **extra}
    log.info("%s %s", tag, snap)
    return snap


def cached_top_store_id(sess: Any) -> Optional[int]:
    """يُستدعى مرة لكل عملية — يقلّل ‎SELECT max(id)‎ المتكرر على مسار اللوحة."""
    global _top_store_id_cache, _top_store_id_cached
    if _top_store_id_cached:
        return _top_store_id_cache
    try:
        from models import Store

        top = sess.query(Store.id).order_by(Store.id.desc()).limit(1).scalar()
        if top is not None:
            _top_store_id_cache = int(top)
    except Exception:  # noqa: BLE001
        _top_store_id_cache = None
    _top_store_id_cached = True
    return _top_store_id_cache


__all__ = [
    "build_db_pool_health_snapshot",
    "cached_top_store_id",
    "log_pool_checkpoint",
    "pool_status_snapshot",
]
