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


def merchant_auth_schema_warm_done() -> bool:
    """Read-only: merchant auth schema warm completed this process (diagnostics)."""
    return bool(_merchant_auth_schema_once)


def verify_merchant_auth_schema(db: Any) -> dict[str, Any]:
    """Read-only check for minimum merchant ↔ store linkage columns."""
    required_user_cols = ["primary_store_id"]
    out: dict[str, Any] = {
        "ok": False,
        "missing_tables": [],
        "missing_columns": [],
        "present_columns": [],
    }
    try:
        insp = inspect(db.engine)
        if not insp.has_table("merchant_users"):
            out["missing_tables"].append("merchant_users")
        else:
            existing = {c["name"] for c in insp.get_columns("merchant_users")}
            for name in required_user_cols:
                if name not in existing:
                    out["missing_columns"].append(f"merchant_users.{name}")
                else:
                    out["present_columns"].append(f"merchant_users.{name}")
        if insp.has_table("stores"):
            store_cols = {c["name"] for c in insp.get_columns("stores")}
            if "merchant_user_id" not in store_cols:
                out["missing_columns"].append("stores.merchant_user_id")
            else:
                out["present_columns"].append("stores.merchant_user_id")
        else:
            out["missing_tables"].append("stores")
        out["ok"] = not out["missing_tables"] and not out["missing_columns"]
        return out
    except SQLAlchemyError as exc:
        out["error"] = type(exc).__name__
        return out


def log_merchant_auth_schema_status(db: Any, *, context: str = "startup") -> dict[str, Any]:
    status = verify_merchant_auth_schema(db)
    tag = "[MERCHANT AUTH SCHEMA]"
    if status.get("ok"):
        line = (
            f"{tag} context={context} ok=true "
            "ensured=merchant_users+stores_linkage_columns"
        )
        level = logging.INFO
    else:
        line = (
            f"{tag} context={context} ok=false "
            f"missing={','.join(status.get('missing_columns') or []) or '-'}"
        )
        if status.get("missing_tables"):
            line += f" missing_tables={','.join(status['missing_tables'])}"
        level = logging.ERROR
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.log(level, "%s", line)
    return status


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


def ensure_merchant_auth_schema(db: Any) -> bool:
    global _merchant_auth_schema_once
    from services.db_ready_diag_v1 import db_ready_substage  # noqa: PLC0415

    if _merchant_auth_schema_once:
        with db_ready_substage("merchant_auth_verify_cached"):
            return bool(verify_merchant_auth_schema(db).get("ok"))
    with _merchant_auth_schema_once_lock:
        if _merchant_auth_schema_once:
            with db_ready_substage("merchant_auth_verify_cached"):
                return bool(verify_merchant_auth_schema(db).get("ok"))
        try:
            with db_ready_substage("merchant_auth_create_all"):
                db.create_all()
            with db_ready_substage("merchant_auth_inspect"):
                insp = inspect(db.engine)
                dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""

            if not insp.has_table("merchant_users"):
                log.warning(
                    "merchant auth schema: merchant_users table missing after create_all"
                )
            else:
                cols = {c["name"] for c in insp.get_columns("merchant_users")}
                for name, sqlite_sql, pg_sql in _MERCHANT_USER_COLUMNS:
                    with db_ready_substage(f"merchant_auth_users_{name}"):
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
                    with db_ready_substage("merchant_auth_stores_user_id"):
                        try:
                            if dialect in ("postgresql", "postgres"):
                                stmt = (
                                    "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                                    "merchant_user_id INTEGER NULL"
                                )
                            else:
                                stmt = (
                                    "ALTER TABLE stores ADD COLUMN "
                                    "merchant_user_id INTEGER"
                                )
                            db.session.execute(text(stmt))
                            db.session.commit()
                            cols.add("merchant_user_id")
                        except SQLAlchemyError as exc:
                            db.session.rollback()
                            log.warning(
                                "merchant auth schema: add stores.merchant_user_id failed: %s",
                                exc,
                            )

            with db_ready_substage("merchant_auth_verify"):
                status = verify_merchant_auth_schema(db)
            with db_ready_substage("merchant_subscription_schema"):
                from schema_merchant_subscription import (  # noqa: PLC0415
                    ensure_merchant_subscription_schema,
                )

                ensure_merchant_subscription_schema(db)
            _merchant_auth_schema_once = bool(status.get("ok"))
            return _merchant_auth_schema_once
        except SQLAlchemyError as exc:
            db.session.rollback()
            log.warning("merchant auth schema ensure skipped: %s", exc)
            return False
    with db_ready_substage("merchant_auth_verify_cached"):
        return bool(verify_merchant_auth_schema(db).get("ok"))
