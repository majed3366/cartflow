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


def reset_merchant_auth_schema_guard_for_tests() -> None:
    global _merchant_auth_schema_once
    _merchant_auth_schema_once = False


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
            if not insp.has_table("stores"):
                _merchant_auth_schema_once = True
                return
            dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
            cols = {c["name"] for c in insp.get_columns("stores")}
            if "merchant_user_id" not in cols:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                        "merchant_user_id INTEGER REFERENCES merchant_users(id)"
                    )
                else:
                    stmt = "ALTER TABLE stores ADD COLUMN merchant_user_id INTEGER"
                db.session.execute(text(stmt))
                db.session.commit()
            _merchant_auth_schema_once = True
        except SQLAlchemyError as exc:
            db.session.rollback()
            log.warning("merchant auth schema ensure skipped: %s", exc)
