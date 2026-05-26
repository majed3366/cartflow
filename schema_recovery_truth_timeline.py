# -*- coding: utf-8 -*-
"""DDL for recovery_truth_timeline_events (proven send/reply timeline)."""
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


def reset_recovery_truth_timeline_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def ensure_recovery_truth_timeline_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("recovery_truth_timeline_events"):
                db.create_all()
            _schema_once = True
        except (OSError, SQLAlchemyError) as exc:
            db.session.rollback()
            log.debug("recovery_truth_timeline schema: %s", exc)


__all__ = [
    "ensure_recovery_truth_timeline_schema",
    "reset_recovery_truth_timeline_schema_guard_for_tests",
]
