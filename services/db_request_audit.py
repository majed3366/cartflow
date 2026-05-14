# -*- coding: utf-8 -*-
"""
مراقبة مؤقتة لضغط القاعدة: عدّ الاستعلامات لكل طلب ‎HTTP‎ + مدة + تقدير الـ ‎pool‎.
يُفعَّل عبر ‎ENV=development‎ (افتراضي) أو ‎CARTFLOW_DB_REQUEST_AUDIT=1‎، ويُعطَّل بـ ‎CARTFLOW_DB_REQUEST_AUDIT=0‎.
لا يغيِّر سلوك التطبيق سوى السجلات.
"""
from __future__ import annotations

import contextvars
import logging
import os
import time
from typing import Any, Dict, Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine

log = logging.getLogger("cartflow")

_audit_bucket: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "db_audit_bucket", default=None
)
_audit_nesting: contextvars.ContextVar[int] = contextvars.ContextVar(
    "db_audit_nesting_depth", default=0
)

_engine_listener_registered = False

_SLOW_MS_DEFAULT = 750.0


def audit_enabled() -> bool:
    v = (os.getenv("CARTFLOW_DB_REQUEST_AUDIT") or "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    if v in ("1", "true", "yes", "on"):
        return True
    return (os.getenv("ENV") or "").strip().lower() == "development"


def slow_request_threshold_ms() -> float:
    raw = (os.getenv("CARTFLOW_DB_SLOW_REQUEST_MS") or "").strip()
    if not raw:
        return _SLOW_MS_DEFAULT
    try:
        return max(50.0, float(raw))
    except (TypeError, ValueError):
        return _SLOW_MS_DEFAULT


def maybe_install_engine_listener() -> None:
    """يُربَط مرّة واحدة بعد جاهزية ‎engine‎."""

    global _engine_listener_registered
    if _engine_listener_registered or not audit_enabled():
        return
    try:
        from extensions import db

        eng = db.engine
    except Exception:  # noqa: BLE001
        return

    @event.listens_for(eng, "before_cursor_execute", retval=False)
    def _count_cursor(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: Any,
    ) -> None:
        bucket = _audit_bucket.get()
        if bucket is None:
            return
        bucket["queries"] = int(bucket.get("queries") or 0) + 1
        stmt = (statement or "").lower()
        if any(
            tok in stmt
            for tok in (
                " from stores",
                " join stores",
                '"stores"',
                "`stores`",
                "stores.",
            )
        ):
            bucket["store_hits"] = int(bucket.get("store_hits") or 0) + 1

    _engine_listener_registered = True


def audit_request_begin(request: Any) -> None:
    if not audit_enabled():
        return
    maybe_install_engine_listener()

    nest = _audit_nesting.get()
    if nest > 0:
        path = getattr(getattr(request, "url", None), "path", "") or ""
        log.warning(
            "[DB SESSION LEAK SUSPECTED] nested_db_audit_context depth=%s path=%s",
            nest,
            path[:200],
        )
    _audit_nesting.set(nest + 1)

    method = getattr(request, "method", "") or ""
    path = getattr(getattr(request, "url", None), "path", "") or ""
    qs = getattr(getattr(request, "url", None), "query", "") or ""
    qs_s = str(qs)[:200]
    endpoint = f"{method} {path}"
    if qs_s:
        endpoint = f"{endpoint}?{qs_s}"
    bucket: Dict[str, Any] = {
        "endpoint": endpoint,
        "path": path[:512],
        "method": method,
        "queries": 0,
        "store_hits": 0,
        "t0": time.perf_counter(),
    }
    _audit_bucket.set(bucket)
    log.info("[DB REQUEST START] endpoint=%s", endpoint[:500])


def audit_leak_suspected_check(request: Any) -> None:
    """طلبات القراءة مع كيانات ‎ORM‎ قذرة/جديدة دون تنظيف — غالباً سلوك نادر؛ سجلات فقط."""

    if not audit_enabled():
        return
    method = (getattr(request, "method", "") or "").upper()
    if method not in ("GET", "HEAD", "OPTIONS"):
        return
    bucket = _audit_bucket.get()
    ep = bucket.get("endpoint") if bucket else "?"
    try:
        from extensions import db

        sess = db.session
        n_new = len(getattr(sess, "new", ()))
        n_dirty = len(getattr(sess, "dirty", ()))
        if n_new or n_dirty:
            log.warning(
                "[DB SESSION LEAK SUSPECTED] endpoint=%s new=%s dirty=%s hint=readonly_with_pending_writes",
                ep[:500],
                n_new,
                n_dirty,
            )
    except Exception as exc:  # noqa: BLE001
        log.debug("db_audit leak check skipped: %s", exc)


def audit_request_end() -> None:
    if not audit_enabled():
        return
    bucket = _audit_bucket.get()
    try:
        _audit_nesting.set(max(0, _audit_nesting.get() - 1))
    except Exception:  # noqa: BLE001
        pass
    if bucket is None:
        return

    elapsed_ms = (time.perf_counter() - bucket["t0"]) * 1000.0
    endpoint = str(bucket.get("endpoint") or "?")
    qn = int(bucket.get("queries") or 0)
    sh = int(bucket.get("store_hits") or 0)

    pool_line = _pool_line()

    log.info("[DB REQUEST END] endpoint=%s duration_ms=%.1f %s", endpoint[:500], elapsed_ms, pool_line)
    log.info(
        "[DB QUERY COUNT] endpoint=%s queries=%s store_sql_hits=%s",
        endpoint[:500],
        qn,
        sh,
    )

    if elapsed_ms >= slow_request_threshold_ms():
        log.warning(
            "[DB SLOW REQUEST] endpoint=%s duration_ms=%.1f queries=%s store_sql_hits=%s",
            endpoint[:500],
            elapsed_ms,
            qn,
            sh,
        )

    _audit_bucket.set(None)


def _pool_line() -> str:
    """تقدير بسيط — ‎NullPool‎ (‏SQLite‏) لا يعرض نفس العدادات."""

    try:
        from extensions import db

        pool = getattr(db.engine, "pool", None)
        if pool is None:
            return "pool=n/a"

        checked = getattr(pool, "checkedout", None)
        psz = getattr(pool, "size", None)
        out = ""
        if callable(checked):
            try:
                out = f"checked_out={checked()}"
            except Exception:
                out = "checked_out=?"
        overflow = getattr(pool, "overflow", None)
        if callable(overflow):
            try:
                out = f"{out} overflow={overflow()}" if out else f"overflow={overflow()}"
            except Exception:
                pass
        if callable(psz):
            try:
                sz = psz()
                out = f"{out} size={sz}" if out else f"size={sz}"
            except Exception:
                pass

        pname = pool.__class__.__name__
        return f"pool={pname} " + (out or "metrics=n/a").strip()
    except Exception:
        return "pool=err"

