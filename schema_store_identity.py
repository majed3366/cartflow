# -*- coding: utf-8 -*-
"""DDL for store_identity_aliases — canonical platform → Store mapping."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

log = logging.getLogger("cartflow")

_schema_ensured = False


def reset_store_identity_schema_cache_for_tests() -> None:
    global _schema_ensured
    _schema_ensured = False


def verify_store_identity_schema(db: Any) -> dict[str, Any]:
    required_cols = [
        "id",
        "store_id",
        "alias_kind",
        "alias_value",
        "platform",
        "created_at",
        "updated_at",
    ]
    out: dict[str, Any] = {
        "table": "store_identity_aliases",
        "required_columns": required_cols,
        "present_columns": [],
        "missing_columns": required_cols[:],
        "ok": False,
    }
    try:
        insp = inspect(db.engine)
        if "store_identity_aliases" not in insp.get_table_names():
            out["error"] = "table_missing"
            return out
        existing = {c["name"] for c in insp.get_columns("store_identity_aliases")}
        present = [n for n in required_cols if n in existing]
        missing = [n for n in required_cols if n not in existing]
        out["present_columns"] = present
        out["missing_columns"] = missing
        out["ok"] = not missing
        return out
    except (OSError, SQLAlchemyError) as exc:
        out["error"] = type(exc).__name__
        return out


def log_store_identity_schema_status(db: Any, *, context: str = "startup") -> dict[str, Any]:
    status = verify_store_identity_schema(db)
    tag = "[STORE IDENTITY SCHEMA]"
    if status.get("ok"):
        line = f"{tag} context={context} ok=true table=store_identity_aliases"
        level = logging.INFO
    else:
        line = (
            f"{tag} context={context} ok=false "
            f"missing={','.join(status.get('missing_columns') or []) or status.get('error') or '-'}"
        )
        level = logging.ERROR
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.log(level, "%s", line)
    return status


def ensure_store_identity_schema(db: Any) -> bool:
    """Create store_identity_aliases via ORM metadata when missing."""
    global _schema_ensured
    from services.db_ready_diag_v1 import db_ready_substage  # noqa: PLC0415

    if _schema_ensured:
        with db_ready_substage("store_identity_verify_cached"):
            return bool(verify_store_identity_schema(db).get("ok"))
    try:
        import models  # noqa: F401

        with db_ready_substage("store_identity_create_table"):
            models.StoreIdentityAlias.__table__.create(bind=db.engine, checkfirst=True)
        dialect = (db.engine.dialect.name or "").lower()
        if dialect in ("postgresql", "postgres"):
            with db_ready_substage("store_identity_indexes"):
                for stmt in (
                    "CREATE INDEX IF NOT EXISTS ix_store_identity_aliases_store_id "
                    "ON store_identity_aliases (store_id)",
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_store_identity_aliases_alias_value "
                    "ON store_identity_aliases (alias_value)",
                ):
                    try:
                        db.session.execute(text(stmt))
                        db.session.commit()
                    except (OSError, SQLAlchemyError, IntegrityError):
                        db.session.rollback()
        _schema_ensured = True
        with db_ready_substage("store_identity_verify"):
            return bool(verify_store_identity_schema(db).get("ok"))
    except (OSError, SQLAlchemyError, IntegrityError) as exc:
        db.session.rollback()
        log.warning("ensure_store_identity_schema failed: %s", exc)
        return False
