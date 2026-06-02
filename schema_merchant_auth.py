# -*- coding: utf-8 -*-
"""Optional DDL for merchant auth tables/columns."""
from __future__ import annotations

import logging
import threading
from typing import Any

import models  # noqa: F401
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger("cartflow")

_merchant_auth_schema_once_lock = threading.Lock()
_merchant_auth_schema_once = False

_MERCHANT_USER_COLUMNS = (
    ("primary_store_id", "INTEGER", "INTEGER"),
    ("merchant_name", "VARCHAR(255)", "VARCHAR(255)"),
    ("created_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
    ("updated_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
)


def reset_merchant_auth_schema_guard_for_tests() -> None:
    global _merchant_auth_schema_once
    _merchant_auth_schema_once = False


def _add_column_if_missing(
    db: Any,
    *,
    table: str,
    name: str,
    sqlite_sql: str,
    pg_sql: str,
    existing: set[str],
    dialect: str,
) -> None:
    if name in existing:
        return
    if dialect in ("postgresql", "postgres"):
        stmt = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {pg_sql}"
    else:
        stmt = f"ALTER TABLE {table} ADD COLUMN {name} {sqlite_sql}"
    db.session.execute(text(stmt))
    db.session.commit()
    existing.add(name)


def ensure_merchant_auth_schema(db: Any) -> None:
    global _merchant_auth_schema_once
    if _merchant_auth_schema_once:
        return
    with _merchant_auth_schema_once_lock:
        if _merchant_auth_schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""

            if not insp.has_table("merchant_users"):
                log.warning(
                    "merchant auth schema: merchant_users table missing after create_all"
                )
            else:
                cols = {c["name"] for c in insp.get_columns("merchant_users")}
                for name, sqlite_sql, pg_sql in _MERCHANT_USER_COLUMNS:
                    try:
                        _add_column_if_missing(
                            db,
                            table="merchant_users",
                            name=name,
                            sqlite_sql=sqlite_sql,
                            pg_sql=pg_sql,
                            existing=cols,
                            dialect=dialect,
                        )
                    except SQLAlchemyError as exc:
                        db.session.rollback()
                        log.warning(
                            "merchant auth schema: add merchant_users.%s failed: %s",
                            name,
                            exc,
                        )

            if insp.has_table("stores"):
                cols = {c["name"] for c in insp.get_columns("stores")}
                if "merchant_user_id" not in cols:
                    try:
                        if dialect in ("postgresql", "postgres"):
                            stmt = (
                                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                                "merchant_user_id INTEGER REFERENCES merchant_users(id)"
                            )
                        else:
                            stmt = (
                                "ALTER TABLE stores ADD COLUMN "
                                "merchant_user_id INTEGER"
                            )
                        db.session.execute(text(stmt))
                        db.session.commit()
                    except SQLAlchemyError as exc:
                        db.session.rollback()
                        log.warning(
                            "merchant auth schema: add stores.merchant_user_id failed: %s",
                            exc,
                        )

            _merchant_auth_schema_once = True
            log.info("[MERCHANT AUTH SCHEMA] ensured merchant_users + stores linkage columns")
        except SQLAlchemyError as exc:
            db.session.rollback()
            log.warning("merchant auth schema ensure skipped: %s", exc)
