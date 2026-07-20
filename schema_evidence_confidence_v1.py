# -*- coding: utf-8 -*-
"""Optional DDL for evidence_confidence_evaluations (ECF V1)."""
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


def reset_evidence_confidence_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def ensure_evidence_confidence_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("evidence_confidence_evaluations"):
                log.warning(
                    "evidence confidence schema: evidence_confidence_evaluations "
                    "missing after create_all"
                )
        except SQLAlchemyError as exc:
            log.warning("evidence confidence schema ensure failed: %s", exc)
        finally:
            _schema_once = True


__all__ = [
    "ensure_evidence_confidence_schema",
    "reset_evidence_confidence_schema_guard_for_tests",
]
