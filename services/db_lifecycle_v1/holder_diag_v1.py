# -*- coding: utf-8 -*-
"""
Diagnostic-only residual-checkout attribution.

Does not change session/UoW/transaction behavior.
Postgres snapshot uses a one-shot NullPool engine, never the API QueuePool.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

log = logging.getLogger("cartflow")


def emit(line: str) -> None:
    """Railway deploy logs capture stdout. The cartflow logger often has no handler."""
    msg = (line or "")[:800]
    try:
        print(msg, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", msg)
    except Exception:  # noqa: BLE001
        pass


def thread_task_identity() -> dict[str, Any]:
    th = threading.current_thread()
    task_name = ""
    try:
        task = asyncio.current_task()
        if task is not None:
            task_name = (task.get_name() or "")[:64]
    except Exception:  # noqa: BLE001
        task_name = ""
    logical_scope = ""
    uow_id = ""
    try:
        from services.db_lifecycle_v1.request_session_scope import (
            current_logical_scope_id,
            current_uow_id,
        )

        logical_scope = current_logical_scope_id() or ""
        uow_id = current_uow_id() or ""
    except Exception:  # noqa: BLE001
        pass
    return {
        "thread_ident": int(th.ident or 0),
        "thread_name": (th.name or "")[:64],
        "task_name": task_name,
        "logical_scope": logical_scope,
        "uow_id": uow_id,
    }


def engine_inventory() -> dict[str, Any]:
    """Count live Engine objects reachable from the API process entrypoints."""
    from extensions import db

    eng = None
    pool = None
    try:
        eng = db.engine
        pool = getattr(eng, "pool", None)
    except Exception as exc:  # noqa: BLE001
        return {
            "engine_count": 0,
            "pool_count": 0,
            "error": type(exc).__name__,
        }
    return {
        "engine_count": 1,
        "pool_count": 1 if pool is not None else 0,
        "request_engine_id": id(eng),
        "request_pool_id": id(pool) if pool is not None else None,
        "request_engine_type": type(eng).__name__,
        "request_pool_type": type(pool).__name__ if pool is not None else None,
        "instrumented_engine_id": id(eng),
        "same_object": True,
        "create_engine_runtime_paths": ["extensions.init_database"],
        "note": "alembic/env.py create_engine is not imported by the API process",
    }


def _classify_pg(state: str, wait_type: str, wait_event: str, xact_s: Any, query_s: Any) -> str:
    st = (state or "").strip().lower()
    wt = (wait_type or "").strip().lower()
    we = (wait_event or "").strip().lower()
    if wt == "lock" or we in ("lock", "relation", "transactionid"):
        return "LOCK_WAIT"
    if st == "active":
        if query_s is not None and int(query_s) >= 5:
            return "LONG_RUNNING"
        return "ACTIVE"
    if st == "idle in transaction":
        return "IDLE_IN_TRANSACTION"
    if st == "idle":
        return "IDLE"
    if wt:
        return "OTHER_WAIT"
    return "OTHER"


def snapshot_pg_via_isolated_connection() -> dict[str, Any]:
    """
    Short-lived NullPool connection. Open, read pg_stat_activity, dispose.
    Never uses the application QueuePool.
    """
    from extensions import get_database_url

    url = (get_database_url() or "").strip()
    if not url.startswith("postgresql"):
        return {"available": False, "reason": "not_postgresql"}
    eng = create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=False,
        connect_args={"application_name": "cartflow-diag"},
    )
    try:
        with eng.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT pid, application_name, client_addr::text,
                           state, backend_start, xact_start, query_start,
                           state_change, wait_event_type, wait_event,
                           backend_type,
                           EXTRACT(EPOCH FROM (now() - xact_start))::int AS xact_s,
                           EXTRACT(EPOCH FROM (now() - query_start))::int AS query_s,
                           left(regexp_replace(query, '\\s+', ' ', 'g'), 80) AS query_prefix
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                      AND pid <> pg_backend_pid()
                      AND COALESCE(application_name, '') <> 'cartflow-diag'
                    """
                )
            ).mappings().all()
        backends: list[dict[str, Any]] = []
        counts = {
            "ACTIVE": 0,
            "IDLE": 0,
            "IDLE_IN_TRANSACTION": 0,
            "LOCK_WAIT": 0,
            "OTHER_WAIT": 0,
            "LONG_RUNNING": 0,
            "OTHER": 0,
        }
        for raw in rows:
            klass = _classify_pg(
                str(raw.get("state") or ""),
                str(raw.get("wait_event_type") or ""),
                str(raw.get("wait_event") or ""),
                raw.get("xact_s"),
                raw.get("query_s"),
            )
            counts[klass] = int(counts.get(klass) or 0) + 1
            backends.append(
                {
                    "pid": raw.get("pid"),
                    "application_name": str(raw.get("application_name") or "")[:64],
                    "client_addr": str(raw.get("client_addr") or ""),
                    "state": raw.get("state"),
                    "backend_type": str(raw.get("backend_type") or "")[:32],
                    "xact_s": raw.get("xact_s"),
                    "query_s": raw.get("query_s"),
                    "wait_event_type": raw.get("wait_event_type"),
                    "wait_event": raw.get("wait_event"),
                    "query_prefix": str(raw.get("query_prefix") or "")[:80],
                    "class": klass,
                }
            )
        return {
            "available": True,
            "via": "isolated_nullpool",
            "backend_count": len(backends),
            "counts": counts,
            "backends": backends,
        }
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "reason": type(exc).__name__, "detail": str(exc)[:120]}
    finally:
        try:
            eng.dispose()
        except Exception:  # noqa: BLE001
            pass


def reconcile_holders_pg(holders: list[dict[str, Any]], pg: dict[str, Any]) -> list[dict[str, Any]]:
    by_pid: dict[int, dict[str, Any]] = {}
    for b in pg.get("backends") or []:
        try:
            by_pid[int(b.get("pid"))] = b
        except (TypeError, ValueError):
            continue
    rows: list[dict[str, Any]] = []
    for h in holders:
        pid = None
        ident = str(h.get("connection_id") or "")
        if ident.startswith("pg:"):
            try:
                pid = int(ident.split(":", 1)[1])
            except (TypeError, ValueError, IndexError):
                pid = None
        pb = by_pid.get(pid) if pid is not None else None
        rows.append(
            {
                "sqlalchemy_connection_id": ident,
                "record_id": h.get("record_id"),
                "request_id": h.get("request_id"),
                "route": h.get("route"),
                "hold_ms": h.get("hold_ms"),
                "thread_ident": h.get("thread_ident"),
                "thread_name": h.get("thread_name"),
                "request_active": h.get("request_active"),
                "postgres_pid": pid,
                "postgres_state": (pb or {}).get("state"),
                "postgres_class": (pb or {}).get("class"),
                "xact_s": (pb or {}).get("xact_s"),
                "query_s": (pb or {}).get("query_s"),
                "query_prefix": (pb or {}).get("query_prefix"),
                "matched_pg": pb is not None,
            }
        )
    return rows


def diagnostic_bundle(*, include_pg: bool = False) -> dict[str, Any]:
    from services.db_lifecycle_v1.connection_trace import active_holders
    from services.db_lifecycle_v1.pool_truth import pool_truth_snapshot

    holders = active_holders()
    pool = pool_truth_snapshot()
    inv = engine_inventory()
    out: dict[str, Any] = {
        "captured_at": time.time(),
        "pool": pool,
        "engine": inv,
        "holders": holders,
        "holder_count": len(holders),
        "sqlalchemy_checked_out": pool.get("checked_out"),
    }
    if include_pg:
        pg = snapshot_pg_via_isolated_connection()
        out["pg"] = pg
        out["reconcile"] = reconcile_holders_pg(holders, pg)
    return out


__all__ = [
    "diagnostic_bundle",
    "emit",
    "engine_inventory",
    "reconcile_holders_pg",
    "snapshot_pg_via_isolated_connection",
    "thread_task_identity",
]
