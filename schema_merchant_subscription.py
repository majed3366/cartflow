# -*- coding: utf-8 -*-
"""DDL for merchant subscription / plan columns on merchant_users."""
from __future__ import annotations

import logging
import threading
from typing import Any

import models  # noqa: F401
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger("cartflow")

_subscription_schema_once_lock = threading.Lock()
_subscription_schema_once = False

_MERCHANT_SUBSCRIPTION_COLUMNS = (
    ("current_plan", "VARCHAR(32) DEFAULT 'starter' NOT NULL", "VARCHAR(32) DEFAULT 'starter' NOT NULL"),
    ("plan_status", "VARCHAR(32) DEFAULT 'active' NOT NULL", "VARCHAR(32) DEFAULT 'active' NOT NULL"),
    ("plan_source", "VARCHAR(32) DEFAULT 'manual' NOT NULL", "VARCHAR(32) DEFAULT 'manual' NOT NULL"),
    ("plan_started_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
    ("plan_expires_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
    ("trial_started_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
    ("trial_expires_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
    ("billing_interval", "VARCHAR(32)", "VARCHAR(32)"),
)

_AUDIT_LOG_COLUMNS = (
    ("old_billing_interval", "VARCHAR(32)", "VARCHAR(32)"),
    ("new_billing_interval", "VARCHAR(32)", "VARCHAR(32)"),
    ("old_plan_started_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
    ("new_plan_started_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
    ("old_trial_started_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
    ("new_trial_started_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
)


def reset_merchant_subscription_schema_guard_for_tests() -> None:
    global _subscription_schema_once
    _subscription_schema_once = False


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


def ensure_merchant_subscription_schema(db: Any) -> bool:
    global _subscription_schema_once
    if _subscription_schema_once:
        return True
    with _subscription_schema_once_lock:
        if _subscription_schema_once:
            return True
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("merchant_users"):
                log.warning(
                    "merchant subscription schema: merchant_users table missing"
                )
                return False
            dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
            cols = {c["name"] for c in insp.get_columns("merchant_users")}
            for name, sqlite_sql, pg_sql in _MERCHANT_SUBSCRIPTION_COLUMNS:
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
                        "merchant subscription schema: add merchant_users.%s failed: %s",
                        name,
                        exc,
                    )
            if insp.has_table("merchant_subscription_audit_logs"):
                audit_cols = {
                    c["name"] for c in insp.get_columns("merchant_subscription_audit_logs")
                }
                for name, sqlite_sql, pg_sql in _AUDIT_LOG_COLUMNS:
                    try:
                        _add_column_if_missing(
                            db,
                            table="merchant_subscription_audit_logs",
                            name=name,
                            sqlite_sql=sqlite_sql,
                            pg_sql=pg_sql,
                            existing=audit_cols,
                            dialect=dialect,
                        )
                    except SQLAlchemyError as exc:
                        db.session.rollback()
                        log.warning(
                            "merchant subscription schema: add audit.%s failed: %s",
                            name,
                            exc,
                        )
            else:
                db.create_all()
            _subscription_schema_once = True
            return True
        except SQLAlchemyError as exc:
            db.session.rollback()
            log.warning("merchant subscription schema ensure failed: %s", exc)
            return False
