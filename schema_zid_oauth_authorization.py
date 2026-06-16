# -*- coding: utf-8 -*-
"""Optional Store column for per-store Zid OAuth Authorization token (additive DDL)."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

log = logging.getLogger("cartflow")

_SCHEMA_COLUMNS = (
    ("zid_authorization_token", "TEXT", "TEXT"),
)

_schema_ensured = False


def verify_store_zid_oauth_authorization_schema(db) -> dict[str, Any]:
    """Read-only check: zid_authorization_token column on ``stores``."""
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


def log_store_zid_oauth_authorization_schema_status(
    db, *, context: str = "startup"
) -> dict[str, Any]:
    status = verify_store_zid_oauth_authorization_schema(db)
    tag = "[STORE ZID OAUTH AUTH SCHEMA]"
    if status.get("ok"):
        line = (
            f"{tag} context={context} ok=true "
            f"columns={','.join(status.get('present_columns') or [])}"
        )
        level = logging.INFO
    else:
        line = (
            f"{tag} context={context} ok=false "
            f"missing={','.join(status.get('missing_columns') or []) or '-'}"
        )
        err = status.get("error")
        if err:
            line += f" error={err}"
        level = logging.ERROR
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.log(level, "%s", line)
    return status


def ensure_store_zid_oauth_authorization_schema(db) -> bool:
    """Add zid_authorization_token on stores when missing."""
    global _schema_ensured
    from services.db_ready_diag_v1 import db_ready_substage  # noqa: PLC0415

    if _schema_ensured:
        with db_ready_substage("zid_oauth_auth_verify_cached"):
            return bool(verify_store_zid_oauth_authorization_schema(db).get("ok"))
    try:
        dialect = ""
        existing: set[str] = set()
        with db_ready_substage("zid_oauth_auth_inspect"):
            insp = inspect(db.engine)
            if "stores" not in insp.get_table_names():
                return False
            dialect = (db.engine.dialect.name or "").lower()
            existing = {c["name"] for c in insp.get_columns("stores")}
        for name, sqlite_sql, pg_sql in _SCHEMA_COLUMNS:
            if name in existing:
                continue
            with db_ready_substage(f"zid_oauth_auth_{name}"):
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
                        "ensure_store_zid_oauth_authorization_schema: add %s failed: %s",
                        name,
                        exc,
                    )
        with db_ready_substage("zid_oauth_auth_verify"):
            status = verify_store_zid_oauth_authorization_schema(db)
        _schema_ensured = bool(status.get("ok"))
        return _schema_ensured
    except (OSError, SQLAlchemyError) as exc:
        db.session.rollback()
        log.warning("ensure_store_zid_oauth_authorization_schema failed: %s", exc)
        return False


def reset_store_zid_oauth_authorization_schema_cache_for_tests() -> None:
    global _schema_ensured
    _schema_ensured = False
