# -*- coding: utf-8 -*-
"""
Global request timing markers — Reliability Foundation V1 (permanent in production-like).

Disable: CARTFLOW_REQUEST_TIMING_AUDIT=0
"""
from __future__ import annotations

import logging
import os
import threading
import time
from contextvars import ContextVar
from typing import Any, Optional

log = logging.getLogger("cartflow")

_PREFIX_REQUEST = "[REQUEST_ENTER]"
_PREFIX_DB_WAIT_START = "[DB_WAIT_START]"
_PREFIX_DB_WAIT_END = "[DB_WAIT_END]"
_PREFIX_ROUTE_START = "[ROUTE_START]"
_PREFIX_ROUTE_END = "[ROUTE_END]"

_request_t0: ContextVar[Optional[float]] = ContextVar("_request_timing_t0", default=None)
_route_t0: ContextVar[Optional[float]] = ContextVar("_request_timing_route_t0", default=None)
_request_path: ContextVar[str] = ContextVar("_request_timing_path", default="")
_pool_listener_lock = threading.Lock()
_pool_listener_installed = False


def request_timing_audit_enabled() -> bool:
    raw = (os.environ.get("CARTFLOW_REQUEST_TIMING_AUDIT") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    try:
        from services.recovery_scheduler_guardrails import is_production_like_runtime

        if is_production_like_runtime():
            return True
    except Exception:  # noqa: BLE001
        pass
    try:
        from services.cartflow_observability_mode import observability_mode

        return observability_mode() == "debug"
    except Exception:  # noqa: BLE001
        return False


def _elapsed_ms(since: float) -> float:
    return round((time.perf_counter() - since) * 1000.0, 1)


def _pool_checked_out_connections() -> Optional[int]:
    try:
        from services.db_pool_diagnostics import pool_status_snapshot

        snap = pool_status_snapshot()
        co = snap.get("checkedout")
        if co is None:
            co = snap.get("checked_out")
        return int(co) if co is not None else None
    except Exception:  # noqa: BLE001
        return None


def _emit(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def request_timing_begin(*, path: str, method: str = "") -> None:
    if not request_timing_audit_enabled():
        return
    p = (path or "/")[:256]
    _request_path.set(p)
    t0 = time.perf_counter()
    _request_t0.set(t0)
    _route_t0.set(None)
    m = (method or "")[:16]
    checked_out = _pool_checked_out_connections()
    co_part = f" checked_out_connections={checked_out}" if checked_out is not None else ""
    _emit(f"{_PREFIX_REQUEST} path={p} method={m or '-'}{co_part} elapsed_ms=0")


def request_timing_route_start() -> None:
    if not request_timing_audit_enabled():
        return
    p = _request_path.get() or "-"
    t0 = _request_t0.get()
    el = _elapsed_ms(t0) if t0 is not None else 0.0
    _route_t0.set(time.perf_counter())
    checked_out = _pool_checked_out_connections()
    co_part = f" checked_out_connections={checked_out}" if checked_out is not None else ""
    _emit(f"{_PREFIX_ROUTE_START} path={p} pre_route_ms={el}{co_part}")


def request_timing_route_end() -> None:
    if not request_timing_audit_enabled():
        return
    p = _request_path.get() or "-"
    t0 = _request_t0.get()
    el = _elapsed_ms(t0) if t0 is not None else 0.0
    rt0 = _route_t0.get()
    route_ms = _elapsed_ms(float(rt0)) if rt0 is not None else el
    checked_out = _pool_checked_out_connections()
    co_part = f" checked_out_connections={checked_out}" if checked_out is not None else ""
    _emit(
        f"{_PREFIX_ROUTE_END} path={p} elapsed_ms={el} route_ms={route_ms}{co_part}"
    )


def request_timing_db_wait_start(*, wait_ms: float = 0.0) -> None:
    if not request_timing_audit_enabled():
        return
    p = _request_path.get() or "-"
    t0 = _request_t0.get()
    el = _elapsed_ms(t0) if t0 is not None else 0.0
    checked_out = _pool_checked_out_connections()
    co_part = f" checked_out_connections={checked_out}" if checked_out is not None else ""
    _emit(
        f"{_PREFIX_DB_WAIT_START} path={p} request_elapsed_ms={el} "
        f"pool_wait_ms={round(float(wait_ms or 0.0), 1)}{co_part}"
    )


def request_timing_db_wait_end(*, hold_ms: float = 0.0) -> None:
    if not request_timing_audit_enabled():
        return
    p = _request_path.get() or "-"
    t0 = _request_t0.get()
    el = _elapsed_ms(t0) if t0 is not None else 0.0
    checked_out = _pool_checked_out_connections()
    co_part = f" checked_out_connections={checked_out}" if checked_out is not None else ""
    _emit(
        f"{_PREFIX_DB_WAIT_END} path={p} request_elapsed_ms={el} "
        f"checkout_hold_ms={round(float(hold_ms or 0.0), 1)}{co_part}"
    )


def maybe_install_pool_checkout_timing_listener() -> None:
    """Record pool checkout wait vs hold per HTTP request (when audit enabled)."""
    global _pool_listener_installed
    if not request_timing_audit_enabled():
        return
    with _pool_listener_lock:
        if _pool_listener_installed:
            return
        try:
            from sqlalchemy import event

            from extensions import db

            eng = db.engine
            pool = getattr(eng, "pool", None)
            if pool is None:
                _pool_listener_installed = True
                return

            @event.listens_for(pool, "before_checkout")
            def _before_checkout(  # noqa: ARG001
                dbapi_conn: Any,
                connection_record: Any,
                connection_proxy: Any,
            ) -> None:
                if _request_t0.get() is None:
                    return
                connection_record._cartflow_checkout_wait_t0 = time.perf_counter()  # type: ignore[attr-defined]

            @event.listens_for(pool, "checkout")
            def _on_checkout(dbapi_conn: Any, connection_record: Any, connection_proxy: Any) -> None:  # noqa: ARG001
                if _request_t0.get() is None:
                    return
                wait_t0 = getattr(connection_record, "_cartflow_checkout_wait_t0", None)
                wait_ms = (
                    round((time.perf_counter() - float(wait_t0)) * 1000.0, 1)
                    if wait_t0 is not None
                    else 0.0
                )
                request_timing_db_wait_start(wait_ms=wait_ms)
                connection_record._cartflow_checkout_t0 = time.perf_counter()  # type: ignore[attr-defined]

            @event.listens_for(pool, "checkin")
            def _on_checkin(dbapi_conn: Any, connection_record: Any) -> None:  # noqa: ARG001
                if _request_t0.get() is None:
                    return
                t_chk = getattr(connection_record, "_cartflow_checkout_t0", None)
                hold_ms = _elapsed_ms(float(t_chk)) if t_chk is not None else 0.0
                request_timing_db_wait_end(hold_ms=hold_ms)

            _pool_listener_installed = True
        except Exception as exc:  # noqa: BLE001
            log.warning("request timing pool listener skipped: %s", exc)
            _pool_listener_installed = True


__all__ = [
    "maybe_install_pool_checkout_timing_listener",
    "request_timing_audit_enabled",
    "request_timing_begin",
    "request_timing_route_end",
    "request_timing_route_start",
]
