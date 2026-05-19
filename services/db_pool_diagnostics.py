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
