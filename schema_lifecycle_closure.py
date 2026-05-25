# -*- coding: utf-8 -*-
"""Optional DDL for lifecycle_closure_records (purchase truth completion v2)."""
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


def reset_lifecycle_closure_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def ensure_lifecycle_closure_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("lifecycle_closure_records"):
                log.warning(
                    "lifecycle closure schema: lifecycle_closure_records missing after create_all"
                )
        except SQLAlchemyError as exc:
            log.warning("lifecycle closure schema ensure failed: %s", exc)
        finally:
            _schema_once = True


__all__ = [
    "ensure_lifecycle_closure_schema",
    "reset_lifecycle_closure_schema_guard_for_tests",
]
