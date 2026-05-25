# -*- coding: utf-8 -*-
"""Optional DDL for lifecycle_closure_records (purchase truth completion v2)."""
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


def reset_lifecycle_closure_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def _ensure_closure_scope_columns(engine: Any, insp: Any) -> None:
    """Add store_slug / session_id / cart_id when table predates v1 scope columns."""
    try:
        cols = {c["name"] for c in insp.get_columns("lifecycle_closure_records")}
    except SQLAlchemyError:
        return
    additions = (
        ("store_slug", "VARCHAR(255)"),
        ("session_id", "VARCHAR(512)"),
        ("cart_id", "VARCHAR(255)"),
    )
    for name, ddl in additions:
        if name in cols:
            continue
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(f"ALTER TABLE lifecycle_closure_records ADD COLUMN {name} {ddl}")
                )
        except SQLAlchemyError as exc:
            log.warning("lifecycle closure schema add column %s: %s", name, exc)


def ensure_lifecycle_closure_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("lifecycle_closure_records"):
                log.warning(
                    "lifecycle closure schema: lifecycle_closure_records missing after create_all"
                )
            else:
                _ensure_closure_scope_columns(db.engine, insp)
        except SQLAlchemyError as exc:
            log.warning("lifecycle closure schema ensure failed: %s", exc)
        finally:
            _schema_once = True


__all__ = [
    "ensure_lifecycle_closure_schema",
    "reset_lifecycle_closure_schema_guard_for_tests",
]
