# -*- coding: utf-8 -*-
"""Optional DDL for product_metric_values (Product Metrics Foundation V1)."""
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


def reset_product_metric_values_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def ensure_product_metric_values_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("product_metric_values"):
                log.warning(
                    "product metrics schema: product_metric_values missing after create_all"
                )
        except SQLAlchemyError as exc:
            log.warning("product metrics schema ensure failed: %s", exc)
        finally:
            _schema_once = True


__all__ = [
    "ensure_product_metric_values_schema",
    "reset_product_metric_values_schema_guard_for_tests",
]
