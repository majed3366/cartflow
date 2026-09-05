# -*- coding: utf-8 -*-
"""DDL guard for commercial_decision_commitments (CDC V1)."""
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


def reset_commercial_decision_commitment_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def ensure_commercial_decision_commitment_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if insp.has_table("commercial_decision_commitments"):
                _schema_once = True
            else:
                log.warning(
                    "commercial_decision_commitments table missing after create_all"
                )
        except (OSError, SQLAlchemyError) as exc:
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass
            log.warning("commercial_decision_commitment schema: %s", exc)


__all__ = [
    "ensure_commercial_decision_commitment_schema",
    "reset_commercial_decision_commitment_schema_guard_for_tests",
]
