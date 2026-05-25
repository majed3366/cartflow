# -*- coding: utf-8 -*-
"""Optional DDL: cart_recovery_logs recovery message context columns (v1)."""
from __future__ import annotations

import logging
import threading
from typing import Any

import models  # noqa: F401
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

log = logging.getLogger("cartflow")

_schema_once_lock = threading.Lock()
_schema_once = False

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("recovery_key", "VARCHAR(512)"),
    ("reason_tag", "VARCHAR(64)"),
    ("context_status", "VARCHAR(32)"),
    ("context_json", "TEXT"),
    ("message_type", "VARCHAR(64)"),
    ("source", "VARCHAR(64)"),
    ("provider", "VARCHAR(32)"),
    ("provider_message_sid", "VARCHAR(128)"),
)


def reset_recovery_message_context_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def _add_column_if_missing(
    db: Any, table: str, col: str, sql_type: str, dialect: str
) -> None:
    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns(table)}
    if col in cols:
        return
    if dialect == "postgresql":
        stmt = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {sql_type}"
    else:
        stmt = f"ALTER TABLE {table} ADD COLUMN {col} {sql_type}"
    db.session.execute(text(stmt))
    db.session.commit()


def ensure_recovery_message_context_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("cart_recovery_logs"):
                _schema_once = True
                return
            dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
            for col, sql_type in _COLUMNS:
                try:
                    _add_column_if_missing(
                        db, "cart_recovery_logs", col, sql_type, dialect
                    )
                except (OSError, SQLAlchemyError, IntegrityError):
                    db.session.rollback()
            _schema_once = True
        except (OSError, SQLAlchemyError) as exc:
            db.session.rollback()
            log.debug("recovery_message_context schema: %s", exc)


__all__ = [
    "ensure_recovery_message_context_schema",
    "reset_recovery_message_context_schema_guard_for_tests",
]
