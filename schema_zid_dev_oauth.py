# -*- coding: utf-8 -*-
"""Optional Store columns for Zid development-store OAuth (additive DDL)."""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

_schema_ensured = False


def ensure_store_zid_integration_schema(db) -> None:
    """Add integration_source + connected_at on stores when missing."""
    global _schema_ensured
    if _schema_ensured:
        return
    try:
        insp = inspect(db.engine)
        if "stores" not in insp.get_table_names():
            return
        dialect = (db.engine.dialect.name or "").lower()
        specs = (
            ("integration_source", "VARCHAR(64)", "VARCHAR(64)"),
            ("connected_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
        )
        existing = {c["name"] for c in insp.get_columns("stores")}
        for name, sqlite_sql, pg_sql in specs:
            if name in existing:
                continue
            if dialect in ("postgresql", "postgres"):
                stmt = f"ALTER TABLE stores ADD COLUMN IF NOT EXISTS {name} {pg_sql}"
            else:
                stmt = f"ALTER TABLE stores ADD COLUMN {name} {sqlite_sql}"
            try:
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
        _schema_ensured = True
    except (OSError, SQLAlchemyError):
        db.session.rollback()
