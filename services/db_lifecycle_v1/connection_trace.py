# -*- coding: utf-8 -*-
"""
Checkout/checkin attribution (INV-DB-11). Production-safe: no SQL params, no secrets.

Installed once on the live engine pool. NullPool has no checkout events — skip quietly.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from services.db_lifecycle_v1.holder_diag_v1 import emit, thread_task_identity
from services.db_lifecycle_v1.pool_truth import note_checked_out, note_timeout, pool_truth_from_pool
from services.db_lifecycle_v1.request_owner import LONG_HOLD_WARN_MS, current_owner
from services.db_lifecycle_v1.request_session_scope import (
    current_logical_scope_id,
    current_uow_id,
)

log = logging.getLogger("cartflow")

_lock = threading.Lock()
_installed = False
_holders: dict[int, dict[str, Any]] = {}


def active_holders() -> list[dict[str, Any]]:
    now = time.perf_counter()
    owner = current_owner()
    active_rid = (owner or {}).get("request_id") if owner else None
    with _lock:
        out = []
        for rec in _holders.values():
            row = dict(rec)
            t0 = rec.get("t0")
            row["hold_ms"] = (
                round((now - float(t0)) * 1000.0, 1) if t0 is not None else 0.0
            )
            row["request_active"] = bool(active_rid) and row.get("request_id") == active_rid
            out.append(row)
        return out


def reset_for_tests() -> None:
    with _lock:
        _holders.clear()


def _conn_identity(dbapi_conn: Any, connection_record: Any) -> str:
    pid = getattr(dbapi_conn, "get_backend_pid", None)
    if callable(pid):
        try:
            return f"pg:{int(pid())}"
        except Exception:  # noqa: BLE001
            pass
    return f"rec:{id(connection_record)}"


def maybe_install_connection_trace() -> None:
    global _installed
    with _lock:
        if _installed:
            return
        try:
            from sqlalchemy import event
            from sqlalchemy.exc import TimeoutError as SATimeoutError

            from extensions import db

            eng = db.engine
            pool = getattr(eng, "pool", None)
            if pool is None or type(pool).__name__ == "NullPool":
                _installed = True
                return

            @event.listens_for(pool, "checkout")
            def _on_checkout(dbapi_conn: Any, connection_record: Any, connection_proxy: Any) -> None:  # noqa: ARG001
                owner = current_owner() or {}
                ident = _conn_identity(dbapi_conn, connection_record)
                ident_ctx = thread_task_identity()
                rec = {
                    "connection_id": ident,
                    "record_id": id(connection_record),
                    "dbapi_id": id(dbapi_conn),
                    "request_id": owner.get("request_id") or "unowned",
                    "uow_id": current_uow_id() or "",
                    "logical_scope": current_logical_scope_id() or "",
                    "route": owner.get("route") or "-",
                    "method": owner.get("method") or "-",
                    "merchant": owner.get("merchant") or "",
                    "t0": time.perf_counter(),
                    "ts": time.time(),
                    "request_start_t0": owner.get("t0"),
                    "admission": owner.get("admission") or "n/a",
                    **ident_ctx,
                }
                connection_record._cartflow_lifecycle_ident = ident  # type: ignore[attr-defined]
                connection_record._cartflow_lifecycle_t0 = rec["t0"]  # type: ignore[attr-defined]
                with _lock:
                    _holders[id(connection_record)] = rec
                    n = len(_holders)
                note_checked_out(n)
                if owner:
                    owner["checkout_count"] = int(owner.get("checkout_count") or 0) + 1
                    owner["last_checkout_ts"] = rec["ts"]
                snap = pool_truth_from_pool(pool)
                if not str(rec["route"]).startswith("/static/"):
                    emit(
                        "[DB CHECKOUT] request_id=%s uow=%s route=%s method=%s conn=%s "
                        "record=%s thread=%s/%s task=%s checked_out=%s overflow=%s admission=%s"
                        % (
                            rec["request_id"],
                            rec["uow_id"] or "-",
                            rec["route"],
                            rec["method"],
                            ident,
                            rec["record_id"],
                            rec["thread_ident"],
                            rec["thread_name"],
                            rec["task_name"] or "-",
                            snap.get("checked_out"),
                            snap.get("overflow"),
                            rec["admission"],
                        )
                    )

            @event.listens_for(pool, "checkin")
            def _on_checkin(dbapi_conn: Any, connection_record: Any) -> None:  # noqa: ARG001
                t0 = getattr(connection_record, "_cartflow_lifecycle_t0", None)
                ident = getattr(connection_record, "_cartflow_lifecycle_ident", "") or _conn_identity(
                    dbapi_conn, connection_record
                )
                hold_ms = (
                    round((time.perf_counter() - float(t0)) * 1000.0, 1)
                    if t0 is not None
                    else 0.0
                )
                with _lock:
                    held = _holders.pop(id(connection_record), None)
                owner = current_owner() or {}
                if owner:
                    owner["checkin_count"] = int(owner.get("checkin_count") or 0) + 1
                    owner["last_checkin_ts"] = time.time()
                    owner["last_hold_ms"] = hold_ms
                route = (held or {}).get("route") or owner.get("route") or "-"
                rid = (held or {}).get("request_id") or owner.get("request_id") or "unowned"
                ctx = thread_task_identity()
                if not str(route).startswith("/static/"):
                    emit(
                        "[DB CHECKIN] request_id=%s route=%s conn=%s hold_ms=%.1f "
                        "checkout_thread=%s finally_thread=%s/%s"
                        % (
                            rid,
                            route,
                            ident,
                            hold_ms,
                            (held or {}).get("thread_ident") or "-",
                            ctx["thread_ident"],
                            ctx["thread_name"],
                        )
                    )
                if hold_ms >= LONG_HOLD_WARN_MS:
                    emit(
                        "[DB LONG HOLD] request_id=%s route=%s method=%s conn=%s "
                        "hold_ms=%.1f merchant=%s checkout_thread=%s"
                        % (
                            rid,
                            route,
                            (held or {}).get("method") or owner.get("method") or "-",
                            ident,
                            hold_ms,
                            (held or {}).get("merchant") or owner.get("merchant") or "",
                            (held or {}).get("thread_ident") or "-",
                        )
                    )
                try:
                    from services.db_resource_safety_v1.observability_v1 import record_hold

                    record_hold(
                        path=str(route),
                        hold_ms=hold_ms,
                        checkout_wait_ms=0.0,
                        network_while_held=False,
                    )
                except Exception:  # noqa: BLE001
                    pass

            @event.listens_for(eng, "handle_error")
            def _on_error(exception_context: Any) -> None:
                exc = getattr(exception_context, "original_exception", None)
                if exc is None:
                    return
                msg = str(exc).lower()
                if isinstance(exc, (SATimeoutError, TimeoutError)) or "queuepool" in msg or "timed out" in msg:
                    note_timeout()
                    owner = current_owner() or {}
                    log.warning(
                        "[DB POOL TIMEOUT] request_id=%s route=%s detail=%s",
                        owner.get("request_id") or "unowned",
                        owner.get("route") or "-",
                        str(exc)[:160],
                    )

            _installed = True
            emit(
                "[DB TRACE INSTALLED] engine=%s pool=%s pool_type=%s"
                % (id(eng), id(pool), type(pool).__name__)
            )
        except Exception as exc:  # noqa: BLE001
            emit("[DB TRACE INSTALL SKIPPED] %s" % (type(exc).__name__,))
            log.debug("connection_trace install skipped: %s", exc)
            _installed = True


def install_on_pool(pool: Any, engine: Optional[Any] = None) -> None:
    """Test helper: attach the same listeners to an isolated QueuePool."""
    from sqlalchemy import event

    @event.listens_for(pool, "checkout")
    def _t_checkout(dbapi_conn: Any, connection_record: Any, connection_proxy: Any) -> None:  # noqa: ARG001
        connection_record._cartflow_lifecycle_t0 = time.perf_counter()  # type: ignore[attr-defined]
        with _lock:
            _holders[id(connection_record)] = {
                "connection_id": f"rec:{id(connection_record)}",
                "request_id": (current_owner() or {}).get("request_id") or "test",
                "route": (current_owner() or {}).get("route") or "test",
                "method": "TEST",
                "t0": connection_record._cartflow_lifecycle_t0,
            }
            note_checked_out(len(_holders))

    @event.listens_for(pool, "checkin")
    def _t_checkin(dbapi_conn: Any, connection_record: Any) -> None:  # noqa: ARG001
        with _lock:
            _holders.pop(id(connection_record), None)
