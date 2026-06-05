# -*- coding: utf-8 -*-
"""Optional DDL for DB ready operational snapshot singleton."""
from __future__ import annotations

import logging
import threading
from typing import Any

import models  # noqa: F401
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger("cartflow")

_schema_once_lock = threading.Lock()
_schema_once = False


def reset_db_ready_operational_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def ensure_db_ready_operational_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("db_ready_operational_snapshots"):
                log.warning(
                    "db ready operational schema: db_ready_operational_snapshots "
                    "missing after create_all"
                )
            else:
                _ensure_startup_warm_columns(db, insp)
                _ensure_restart_survival_columns(db, insp)
        except SQLAlchemyError as exc:
            log.warning("db ready operational schema ensure failed: %s", exc)
        finally:
            _schema_once = True


def _ensure_startup_warm_columns(db: Any, insp: Any) -> None:
    """Add Step 4B.3 startup warm columns when table already exists."""
    try:
        cols = {c["name"] for c in insp.get_columns("db_ready_operational_snapshots")}
    except Exception:  # noqa: BLE001
        return
    dialect = db.engine.dialect.name
    alters: list[str] = []
    if "startup_warm_status" not in cols:
        alters.append(
            "ALTER TABLE db_ready_operational_snapshots "
            "ADD COLUMN startup_warm_status VARCHAR(16) NOT NULL DEFAULT 'not_started'"
        )
    if "startup_warm_duration_ms" not in cols:
        alters.append(
            "ALTER TABLE db_ready_operational_snapshots "
            "ADD COLUMN startup_warm_duration_ms FLOAT NOT NULL DEFAULT 0"
        )
    if "startup_warm_error" not in cols:
        alters.append(
            "ALTER TABLE db_ready_operational_snapshots "
            "ADD COLUMN startup_warm_error VARCHAR(255)"
        )
    if "last_request_cached_verification" not in cols:
        if dialect == "sqlite":
            alters.append(
                "ALTER TABLE db_ready_operational_snapshots "
                "ADD COLUMN last_request_cached_verification BOOLEAN"
            )
        else:
            alters.append(
                "ALTER TABLE db_ready_operational_snapshots "
                "ADD COLUMN last_request_cached_verification BOOLEAN"
            )
    for stmt in alters:
        try:
            db.session.execute(text(stmt))
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            log.warning("db ready operational column migrate skipped: %s", exc)


def _ensure_restart_survival_columns(db: Any, insp: Any) -> None:
    """Add Step 4B.4 restart survival columns when table already exists."""
    try:
        cols = {c["name"] for c in insp.get_columns("db_ready_operational_snapshots")}
    except Exception:  # noqa: BLE001
        return
    alters: list[str] = []
    if "restart_startup_at" not in cols:
        alters.append(
            "ALTER TABLE db_ready_operational_snapshots "
            "ADD COLUMN restart_startup_at TIMESTAMP"
        )
    if "restart_warm_completed_at" not in cols:
        alters.append(
            "ALTER TABLE db_ready_operational_snapshots "
            "ADD COLUMN restart_warm_completed_at TIMESTAMP"
        )
    if "restart_first_dashboard_at" not in cols:
        alters.append(
            "ALTER TABLE db_ready_operational_snapshots "
            "ADD COLUMN restart_first_dashboard_at TIMESTAMP"
        )
    if "restart_first_dashboard_duration_ms" not in cols:
        alters.append(
            "ALTER TABLE db_ready_operational_snapshots "
            "ADD COLUMN restart_first_dashboard_duration_ms FLOAT NOT NULL DEFAULT 0"
        )
    if "restart_first_dashboard_cached_verification" not in cols:
        alters.append(
            "ALTER TABLE db_ready_operational_snapshots "
            "ADD COLUMN restart_first_dashboard_cached_verification BOOLEAN"
        )
    if "restart_first_dashboard_heavy_warm" not in cols:
        alters.append(
            "ALTER TABLE db_ready_operational_snapshots "
            "ADD COLUMN restart_first_dashboard_heavy_warm BOOLEAN"
        )
    if "restart_survival_result" not in cols:
        alters.append(
            "ALTER TABLE db_ready_operational_snapshots "
            "ADD COLUMN restart_survival_result VARCHAR(8) NOT NULL DEFAULT 'pending'"
        )
    if "restart_survival_evaluated_at" not in cols:
        alters.append(
            "ALTER TABLE db_ready_operational_snapshots "
            "ADD COLUMN restart_survival_evaluated_at TIMESTAMP"
        )
    for stmt in alters:
        try:
            db.session.execute(text(stmt))
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            log.warning("db ready restart survival column migrate skipped: %s", exc)


__all__ = [
    "ensure_db_ready_operational_schema",
    "reset_db_ready_operational_schema_guard_for_tests",
]
