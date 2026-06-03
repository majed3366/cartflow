# -*- coding: utf-8 -*-
"""Store columns for storefront runtime truth gate + beacon (additive DDL)."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

log = logging.getLogger("cartflow")

_SCHEMA_COLUMNS = (
    ("widget_last_runtime_slug", "TEXT", "VARCHAR(255)"),
    ("widget_last_beacon_json", "TEXT", "TEXT"),
    ("widget_runtime_truth_status", "TEXT", "VARCHAR(32)"),
    ("widget_runtime_truth_json", "TEXT", "TEXT"),
    ("widget_runtime_truth_at", "DATETIME", "TIMESTAMP NULL"),
)

_schema_ensured = False


def verify_storefront_runtime_truth_schema(db) -> dict[str, Any]:
    required = [name for name, _, _ in _SCHEMA_COLUMNS]
    out: dict[str, Any] = {
        "table": "stores",
        "required_columns": required,
        "present_columns": [],
        "missing_columns": required[:],
        "ok": False,
    }
    try:
        insp = inspect(db.engine)
        if "stores" not in insp.get_table_names():
            out["error"] = "stores_table_missing"
            return out
        existing = {c["name"] for c in insp.get_columns("stores")}
        present = [n for n in required if n in existing]
        missing = [n for n in required if n not in existing]
        out["present_columns"] = present
        out["missing_columns"] = missing
        out["ok"] = not missing
        return out
    except (OSError, SQLAlchemyError) as exc:
        out["error"] = type(exc).__name__
        return out


def ensure_storefront_runtime_truth_schema(db) -> bool:
    global _schema_ensured
    if _schema_ensured:
        return bool(verify_storefront_runtime_truth_schema(db).get("ok"))
    try:
        insp = inspect(db.engine)
        if "stores" not in insp.get_table_names():
            return False
        dialect = (db.engine.dialect.name or "").lower()
        existing = {c["name"] for c in insp.get_columns("stores")}
        for name, sqlite_sql, pg_sql in _SCHEMA_COLUMNS:
            if name in existing:
                continue
            if dialect in ("postgresql", "postgres"):
                stmt = f"ALTER TABLE stores ADD COLUMN IF NOT EXISTS {name} {pg_sql}"
            else:
                stmt = f"ALTER TABLE stores ADD COLUMN {name} {sqlite_sql}"
            try:
                db.session.execute(text(stmt))
                db.session.commit()
                existing.add(name)
            except (OSError, SQLAlchemyError, IntegrityError) as exc:
                db.session.rollback()
                log.warning(
                    "ensure_storefront_runtime_truth_schema: add %s failed: %s",
                    name,
                    exc,
                )
        status = verify_storefront_runtime_truth_schema(db)
        _schema_ensured = bool(status.get("ok"))
        return _schema_ensured
    except (OSError, SQLAlchemyError) as exc:
        db.session.rollback()
        log.warning("ensure_storefront_runtime_truth_schema failed: %s", exc)
        return False


def reset_storefront_runtime_truth_schema_cache_for_tests() -> None:
    global _schema_ensured
    _schema_ensured = False
