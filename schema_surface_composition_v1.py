# -*- coding: utf-8 -*-
"""Optional DDL for surface_compositions (SCF V1)."""
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


def reset_surface_composition_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def ensure_surface_composition_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("surface_compositions"):
                log.warning(
                    "surface composition schema: surface_compositions "
                    "missing after create_all"
                )
        except SQLAlchemyError as exc:
            log.warning("surface composition schema ensure failed: %s", exc)
        finally:
            _schema_once = True


__all__ = [
    "ensure_surface_composition_schema",
    "reset_surface_composition_schema_guard_for_tests",
]
