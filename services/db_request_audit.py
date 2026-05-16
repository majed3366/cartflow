# -*- coding: utf-8 -*-
"""
مراقبة مؤقتة لضغط القاعدة: عدّ الاستعلامات لكل طلب ‎HTTP‎ + مدة + تقدير الـ ‎pool‎.
يُفعَّل عبر ‎CARTFLOW_OBSERVABILITY_MODE=basic|debug‎؛ ‎CARTFLOW_DB_REQUEST_AUDIT=0‎ يعطّل العداد.
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
    try:
        from services.cartflow_observability_mode import (
            observability_request_sql_audit_active,
        )

        return observability_request_sql_audit_active()
    except Exception:  # noqa: BLE001
        return False


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
        if any(
            tok in stmt
            for tok in (
                "abandoned_cart",
                "cart_recovery_reason",
                "cart_recovery_log",
                "recovery_event",
                "abandonment_reason",
                "merchant_followup",
            )
        ):
            bucket["recovery_hits"] = int(bucket.get("recovery_hits") or 0) + 1
        elif any(tok in stmt for tok in ("objection_track", "message_log")):
            bucket["analytics_hits"] = int(bucket.get("analytics_hits") or 0) + 1

    _engine_listener_registered = True


def peek_request_audit_bucket_for_profile() -> Optional[Dict[str, Any]]:
    """
    قراءة فقط لتقرير تعرُّف الطلب — بدون تنظيف (يُنشَأ المفتاح مع ‎audit_request_begin‎).
    """

    bucket = _audit_bucket.get()
    if bucket is None:
        return None
    qn = int(bucket.get("queries") or 0)
    elapsed_ms = (time.perf_counter() - float(bucket["t0"])) * 1000.0
    return {
        "queries": qn,
        "store_queries": int(bucket.get("store_hits") or 0),
        "recovery_queries": int(bucket.get("recovery_hits") or 0),
        "analytics_queries": int(bucket.get("analytics_hits") or 0),
        "elapsed_request_ms_roundtrip": round(elapsed_ms, 1),
    }


def audit_request_begin(request: Any) -> None:
    if not audit_enabled():
        return
    maybe_install_engine_listener()

    try:
        from services.cartflow_observability_mode import (
            observability_db_audit_leak_and_nesting_warnings,
        )

        leak_warn_ok = observability_db_audit_leak_and_nesting_warnings()
    except Exception:  # noqa: BLE001
        leak_warn_ok = False

    nest = _audit_nesting.get()
    if nest > 0 and leak_warn_ok:
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
        "recovery_hits": 0,
        "analytics_hits": 0,
        "t0": time.perf_counter(),
    }
    _audit_bucket.set(bucket)
    try:
        from services.cartflow_observability_mode import (
            observability_middleware_verbose_db_request_logs,
        )

        if observability_middleware_verbose_db_request_logs():
            log.info("[DB REQUEST START] endpoint=%s", endpoint[:500])
    except Exception:  # noqa: BLE001
        pass


def audit_leak_suspected_check(request: Any) -> None:
    """طلبات القراءة مع كيانات ‎ORM‎ قذرة/جديدة دون تنظيف — غالباً سلوك نادر؛ سجلات فقط."""

    if not audit_enabled():
        return
    try:
        from services.cartflow_observability_mode import (
            observability_db_audit_leak_and_nesting_warnings,
        )

        if not observability_db_audit_leak_and_nesting_warnings():
            return
    except Exception:  # noqa: BLE001
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
    try:
        from services.cartflow_observability_mode import (
            observability_middleware_verbose_db_request_logs,
        )

        verbose_ep = observability_middleware_verbose_db_request_logs()
    except Exception:  # noqa: BLE001
        verbose_ep = False

    if verbose_ep:
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
        stall_trace_checkpoint("slow_request_audit_end")

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


def stall_trace_enabled() -> bool:
    """تشخيص تعليقات الطلب — ‎OBSERVABILITY_MODE=debug‎ ولا ‎CARTFLOW_STALL_TRACE=0‎."""
    try:
        from services.cartflow_observability_mode import (
            observability_stall_trace_enabled,
        )

        return observability_stall_trace_enabled()
    except Exception:  # noqa: BLE001
        return False


def _stall_runtime_snapshot() -> Dict[str, Any]:
    """معرّفات زمن التشغيل — يعمل في ‎async‎ و‎sync‎ (لوحة التاجر على ‎thread pool‎)."""
    import os
    import threading

    out: Dict[str, Any] = {
        "thread_id": threading.get_ident(),
        "process_id": os.getpid(),
        "threading_active": threading.active_count(),
    }
    try:
        import asyncio

        loop = asyncio.get_running_loop()
        out["event_loop_id"] = id(loop)
        all_t = asyncio.all_tasks(loop)
        out["asyncio_all_tasks"] = len(all_t)
        out["asyncio_pending_tasks"] = len([t for t in all_t if not t.done()])
    except RuntimeError:
        out["event_loop_id"] = "n/a_sync_context"
        out["asyncio_all_tasks"] = "n/a"
        out["asyncio_pending_tasks"] = "n/a"
    return out


def stall_trace_checkpoint(
    phase: str,
    *,
    bg_tasks_queued: Optional[int] = None,
) -> None:
    """
    نقطة زمنية واحدة لمسار الطلب — لمقارنة التعليق خارج ‎SQL‎ (‎queries=0‎).
    لا يغيّر السلوك.
    """
    if not stall_trace_enabled():
        return
    bucket = _audit_bucket.get()
    elapsed_ms = 0.0
    ep = "?"
    if bucket is not None:
        elapsed_ms = (time.perf_counter() - float(bucket["t0"])) * 1000.0
        ep = str(bucket.get("endpoint") or "?")[:500]
    snap = _stall_runtime_snapshot()
    parts = [
        "[STALL TRACE]",
        f"phase={phase}",
        f"elapsed_ms={elapsed_ms:.1f}",
        f"endpoint={ep}",
        f"thread_id={snap['thread_id']}",
        f"process_id={snap['process_id']}",
        f"threading_active={snap['threading_active']}",
        f"event_loop_id={snap['event_loop_id']}",
        f"asyncio_all_tasks={snap['asyncio_all_tasks']}",
        f"asyncio_pending_tasks={snap['asyncio_pending_tasks']}",
    ]
    if bg_tasks_queued is not None:
        parts.append(f"bg_tasks_queued={int(bg_tasks_queued)}")
    line = " ".join(parts)
    try:
        log.warning("%s", line)
    except Exception:  # noqa: BLE001
        pass

