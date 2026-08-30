# -*- coding: utf-8 -*-
"""لقطات حالة ‎SQLAlchemy QueuePool‎ — تشخيص ضغط الاتصالات دون تغيير السلوك."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

log = logging.getLogger("cartflow")

_top_store_id_cache: Optional[int] = None
_top_store_id_cached: bool = False


def pool_status_snapshot() -> Dict[str, Any]:
    """Real QueuePool counters — never status-string-only (INV-DB-12)."""
    try:
        from services.db_lifecycle_v1.pool_truth import pool_truth_snapshot

        snap = pool_truth_snapshot()
        return {
            "pool_impl": snap.get("pool_impl"),
            "size": snap.get("size"),
            "checkedin": snap.get("checked_in"),
            "checkedout": snap.get("checked_out"),
            "checked_out": snap.get("checked_out"),
            "overflow": snap.get("overflow"),
            "available": snap.get("available"),
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
        from services.admin_operational_health import get_operational_counter_snapshots
        from services.db_lifecycle_v1.pool_truth import pool_truth_snapshot

        truth = pool_truth_snapshot()
        counters = get_operational_counter_snapshots()
    except Exception as exc:  # noqa: BLE001
        return {
            "available": False,
            "error": str(exc)[:200],
            "timeout_count": 0,
            "exhausted": False,
        }

    size = truth.get("size")
    checked_out = truth.get("checked_out")
    overflow = truth.get("overflow")
    pool_class = truth.get("pool_impl")
    max_connections = truth.get("max_connections")
    available_slots = truth.get("available_slots")

    timeout_count = max(
        int(counters.get("pool_timeout_count") or 0),
        int(truth.get("timeout_count") or 0),
    )
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
        "available": bool(truth.get("available")),
        "pool_class": pool_class,
        "size": size,
        "checked_out": checked_out,
        "overflow": overflow,
        "max_connections": max_connections,
        "available_slots": available_slots,
        "timeout_count": timeout_count,
        "exhausted": exhausted,
        "summary_ar": f"{pool_class} checked_out={checked_out} size={size}",
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
