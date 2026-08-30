# -*- coding: utf-8 -*-
"""
SQLAlchemy pool vs Postgres pg_stat_activity (Phase 3).

Do not call a connection a leak unless both sides agree.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

CLASS_ACTIVE_QUERY = "ACTIVE_QUERY"
CLASS_IDLE = "IDLE"
CLASS_IDLE_IN_TRANSACTION = "IDLE_IN_TRANSACTION"
CLASS_LOCK_WAIT = "LOCK_WAIT"
CLASS_UNKNOWN = "UNKNOWN"


def classify_backend(row: dict[str, Any]) -> str:
    state = str(row.get("state") or "").strip().lower()
    wait_type = str(row.get("wait_event_type") or "").strip().lower()
    wait_event = str(row.get("wait_event") or "").strip().lower()
    if wait_type == "lock" or wait_event in ("lock", "relation", "transactionid"):
        return CLASS_LOCK_WAIT
    if state == "active":
        return CLASS_ACTIVE_QUERY
    if state == "idle in transaction":
        return CLASS_IDLE_IN_TRANSACTION
    if state == "idle":
        return CLASS_IDLE
    return CLASS_UNKNOWN


def snapshot_pg_stat_activity(sess: Any) -> dict[str, Any]:
    """
    Read pg_stat_activity for this database. Empty on non-Postgres.
    Does not log query text (may contain customer data).
    """
    bind = getattr(sess, "bind", None)
    dialect = str(getattr(getattr(bind, "dialect", None), "name", "") or "")
    if dialect != "postgresql":
        return {
            "available": False,
            "reason": "not_postgresql",
            "dialect": dialect,
            "backends": [],
        }
    rows = sess.execute(
        text(
            """
            SELECT pid, state, xact_start, query_start, state_change,
                   wait_event_type, wait_event,
                   application_name, client_addr,
                   backend_type
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND pid <> pg_backend_pid()
            """
        )
    ).mappings().all()
    backends: list[dict[str, Any]] = []
    idle_in_xact = 0
    active = 0
    idle = 0
    lock_wait = 0
    for raw in rows:
        rec = {
            "pid": raw.get("pid"),
            "state": raw.get("state"),
            "xact_start": str(raw.get("xact_start") or ""),
            "query_start": str(raw.get("query_start") or ""),
            "state_change": str(raw.get("state_change") or ""),
            "wait_event_type": raw.get("wait_event_type"),
            "wait_event": raw.get("wait_event"),
            "application_name": str(raw.get("application_name") or "")[:64],
            "client_addr": str(raw.get("client_addr") or ""),
            "backend_type": str(raw.get("backend_type") or "")[:32],
        }
        rec["class"] = classify_backend(rec)
        if rec["class"] == CLASS_IDLE_IN_TRANSACTION:
            idle_in_xact += 1
        elif rec["class"] == CLASS_ACTIVE_QUERY:
            active += 1
        elif rec["class"] == CLASS_IDLE:
            idle += 1
        elif rec["class"] == CLASS_LOCK_WAIT:
            lock_wait += 1
        backends.append(rec)
    return {
        "available": True,
        "dialect": dialect,
        "backend_count": len(backends),
        "active": active,
        "idle": idle,
        "idle_in_transaction": idle_in_xact,
        "lock_wait": lock_wait,
        "backends": backends,
    }


def reconcile(sqlalchemy_pool: dict[str, Any], pg: dict[str, Any]) -> dict[str, Any]:
    """Compare sides. Leak is only claimed when both support it."""
    sa_out = sqlalchemy_pool.get("checked_out")
    pg_iit = pg.get("idle_in_transaction")
    verdict = "UNKNOWN"
    if not pg.get("available"):
        verdict = "PG_UNAVAILABLE"
    elif sa_out is None:
        verdict = "SA_METRICS_UNAVAILABLE"
    elif int(sa_out or 0) == 0 and int(pg_iit or 0) == 0:
        verdict = "EQUILIBRIUM"
    elif int(pg_iit or 0) > 0:
        verdict = "IDLE_IN_TRANSACTION_PRESENT"
    elif int(sa_out or 0) > 0:
        verdict = "SA_CHECKED_OUT_PG_NO_IIT"
    return {
        "verdict": verdict,
        "sqlalchemy_checked_out": sa_out,
        "pg_idle_in_transaction": pg_iit,
        "pg_active": pg.get("active"),
        "leak_claimed": False,
        "note": "Leak requires both sides: SA checked_out>0 after request end AND PG idle-in-transaction or unmatched backend.",
    }
