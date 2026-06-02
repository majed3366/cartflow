# -*- coding: utf-8 -*-
"""
Production store schema bootstrap — run before any Store ORM load.

Adds missing columns on Railway Postgres (schema drift) without Alembic on deploy.
"""
from __future__ import annotations

import logging
import threading
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import inspect

from extensions import get_database_url

log = logging.getLogger("cartflow")

_bootstrap_lock = threading.Lock()
_bootstrap_verified_ok = False


def reset_production_store_schema_bootstrap_for_tests() -> None:
    global _bootstrap_verified_ok
    _bootstrap_verified_ok = False
    from schema_merchant_auth import reset_merchant_auth_schema_guard_for_tests
    from schema_zid_dev_oauth import reset_store_zid_integration_schema_cache_for_tests

    reset_merchant_auth_schema_guard_for_tests()
    reset_store_zid_integration_schema_cache_for_tests()


def log_production_database_identity(*, context: str = "startup") -> dict[str, str]:
    """Safe log of which DB the app uses (no credentials)."""
    raw = (get_database_url() or "").strip()
    host = ""
    database = ""
    scheme = ""
    try:
        parsed = urlparse(raw)
        scheme = (parsed.scheme or "").split("+")[0]
        host = parsed.hostname or ""
        database = (parsed.path or "").lstrip("/") or ""
    except (ValueError, AttributeError):
        scheme = "unknown"
    line = (
        f"[PRODUCTION DB IDENTITY] context={context} "
        f"scheme={scheme or '-'} host={host or '-'} database={database or '-'} "
        f"configured={'true' if bool(raw) else 'false'}"
    )
    if not raw:
        line += " review=ENV_DATABASE_URL_MISSING"
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.info("%s", line)
    return {"scheme": scheme, "host": host, "database": database}


def verify_production_store_schema(db: Any) -> dict[str, Any]:
    from schema_merchant_auth import verify_merchant_auth_schema
    from schema_zid_dev_oauth import verify_store_zid_integration_schema

    merchant = verify_merchant_auth_schema(db)
    zid = verify_store_zid_integration_schema(db)
    missing = sorted(
        set(merchant.get("missing_columns") or [])
        | set(merchant.get("missing_tables") or [])
        | set(zid.get("missing_columns") or [])
    )
    ok = bool(merchant.get("ok")) and bool(zid.get("ok"))
    return {
        "ok": ok,
        "merchant_auth": merchant,
        "zid_integration": zid,
        "missing": missing,
    }


def ensure_production_store_schema(db: Any, *, context: str = "startup") -> bool:
    """
    Idempotent DDL for merchant ↔ store linkage + Zid OAuth store columns.

    Returns True only when verification passes (never caches a failed run).
    """
    global _bootstrap_verified_ok
    if _bootstrap_verified_ok:
        status = verify_production_store_schema(db)
        return bool(status.get("ok"))

    with _bootstrap_lock:
        if _bootstrap_verified_ok:
            status = verify_production_store_schema(db)
            return bool(status.get("ok"))

        log_production_database_identity(context=context)

        from schema_merchant_auth import (
            ensure_merchant_auth_schema,
            log_merchant_auth_schema_status,
        )
        from schema_zid_dev_oauth import (
            ensure_store_zid_integration_schema,
            log_store_zid_integration_schema_status,
        )

        ensure_merchant_auth_schema(db)
        log_merchant_auth_schema_status(db, context=context)
        zid_ok = ensure_store_zid_integration_schema(db)
        zid_status = log_store_zid_integration_schema_status(db, context=context)

        status = verify_production_store_schema(db)
        ok = bool(status.get("ok")) and zid_ok
        tag = "[PRODUCTION DB SCHEMA]"
        if ok:
            _bootstrap_verified_ok = True
            line = f"{tag} context={context} ok=true"
            level = logging.INFO
        else:
            _bootstrap_verified_ok = False
            line = (
                f"{tag} context={context} ok=false "
                f"missing={','.join(status.get('missing') or []) or '-'}"
            )
            level = logging.ERROR
        try:
            print(line, flush=True)
        except OSError:
            pass
        log.log(level, "%s", line)
        if not ok and zid_status.get("missing_columns"):
            log.error(
                "%s manual_sql_review=run scripts/production_store_schema_repair.sql "
                "on the database shown in [PRODUCTION DB IDENTITY]",
                tag,
            )
        return ok


def ensure_production_store_schema_before_request(db: Any) -> None:
    """Fast path for HTTP middleware — bootstrap once per process when not yet verified."""
    if _bootstrap_verified_ok:
        return
    try:
        ensure_production_store_schema(db, context="request")
    except Exception as exc:  # noqa: BLE001
        log.warning("production store schema bootstrap before request failed: %s", exc)
