# -*- coding: utf-8 -*-
"""Optional DDL for WP-ET-10.6 Evidence Truth materialization tables."""
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


def reset_evidence_truth_materialization_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def ensure_evidence_truth_materialization_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            for table in (
                "evidence_truth_materialization_runs",
                "evidence_truth_shadow_artifacts",
            ):
                if not insp.has_table(table):
                    log.warning(
                        "evidence truth materialization schema: %s missing after create_all",
                        table,
                    )
        except SQLAlchemyError as exc:
            log.warning("evidence truth materialization schema ensure failed: %s", exc)
        finally:
            _schema_once = True


__all__ = [
    "ensure_evidence_truth_materialization_schema",
    "reset_evidence_truth_materialization_schema_guard_for_tests",
]
