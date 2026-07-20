# -*- coding: utf-8 -*-
"""Optional DDL for product evidence assembly tables (PEA V1)."""
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


def reset_product_evidence_assembly_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def ensure_product_evidence_assembly_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            for table in ("product_evidence_bundles", "product_evidence_items"):
                if not insp.has_table(table):
                    log.warning(
                        "product evidence assembly schema: %s missing after create_all",
                        table,
                    )
        except SQLAlchemyError as exc:
            log.warning("product evidence assembly schema ensure failed: %s", exc)
        finally:
            _schema_once = True


__all__ = [
    "ensure_product_evidence_assembly_schema",
    "reset_product_evidence_assembly_schema_guard_for_tests",
]
