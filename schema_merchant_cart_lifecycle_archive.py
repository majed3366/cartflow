# -*- coding: utf-8 -*-
"""DDL guard for merchant_cart_lifecycle_archives."""
from __future__ import annotations

import logging
import threading
from typing import Any

import models  # noqa: F401
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger("cartflow")

_schema_once_lock = threading.Lock()
_schema_once = False


def reset_merchant_cart_lifecycle_archive_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def ensure_merchant_cart_lifecycle_archive_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if insp.has_table("merchant_cart_lifecycle_archives"):
                _schema_once = True
            else:
                log.warning(
                    "merchant_cart_lifecycle_archives table missing after create_all"
                )
        except (OSError, SQLAlchemyError) as exc:
            db.session.rollback()
            log.warning("merchant_cart_lifecycle_archive schema: %s", exc)


__all__ = [
    "ensure_merchant_cart_lifecycle_archive_schema",
    "reset_merchant_cart_lifecycle_archive_schema_guard_for_tests",
]
