# -*- coding: utf-8 -*-
"""Optional DDL for DB ready operational snapshot singleton."""
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


def reset_db_ready_operational_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def ensure_db_ready_operational_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("db_ready_operational_snapshots"):
                log.warning(
                    "db ready operational schema: db_ready_operational_snapshots "
                    "missing after create_all"
                )
        except SQLAlchemyError as exc:
            log.warning("db ready operational schema ensure failed: %s", exc)
        finally:
            _schema_once = True


__all__ = [
    "ensure_db_ready_operational_schema",
    "reset_db_ready_operational_schema_guard_for_tests",
]
