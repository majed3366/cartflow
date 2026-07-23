# -*- coding: utf-8 -*-
"""Optional DDL for commercial_guidance_records (CGF + cguide V1)."""
from __future__ import annotations

import logging
import threading
from typing import Any

import models  # noqa: F401
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger("cartflow")

_schema_once_lock = threading.Lock()
_schema_once = False

# Additive cguide_v1 columns (safe no-op when already present).
_CGUIDE_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("knowledge_id", "VARCHAR(64)", "''"),
    ("knowledge_type", "VARCHAR(64)", "''"),
    ("merchant_objective", "TEXT", "''"),
    ("eligible_actions_json", "TEXT", "'[]'"),
    ("forbidden_actions_json", "TEXT", "'[]'"),
    ("confidence_level", "VARCHAR(32)", "''"),
    ("source_knowledge_fingerprint", "VARCHAR(64)", "''"),
)


def reset_commercial_guidance_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def _ensure_cguide_columns(db: Any) -> None:
    try:
        insp = inspect(db.engine)
        if not insp.has_table("commercial_guidance_records"):
            return
        existing = {c["name"] for c in insp.get_columns("commercial_guidance_records")}
        dialect = db.engine.dialect.name
        for name, sql_type, default in _CGUIDE_COLUMNS:
            if name in existing:
                continue
            if dialect == "postgresql":
                if default in {"''", "'[]'"}:
                    db.session.execute(
                        text(
                            f"ALTER TABLE commercial_guidance_records "
                            f"ADD COLUMN IF NOT EXISTS {name} {sql_type} "
                            f"DEFAULT {default}"
                        )
                    )
                else:
                    db.session.execute(
                        text(
                            f"ALTER TABLE commercial_guidance_records "
                            f"ADD COLUMN IF NOT EXISTS {name} {sql_type}"
                        )
                    )
            else:
                db.session.execute(
                    text(
                        f"ALTER TABLE commercial_guidance_records "
                        f"ADD COLUMN {name} {sql_type} DEFAULT {default}"
                    )
                )
        db.session.commit()
    except SQLAlchemyError as exc:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        log.warning("commercial guidance cguide columns ensure failed: %s", exc)


def ensure_commercial_guidance_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("commercial_guidance_records"):
                log.warning(
                    "commercial guidance schema: commercial_guidance_records "
                    "missing after create_all"
                )
            else:
                _ensure_cguide_columns(db)
        except SQLAlchemyError as exc:
            log.warning("commercial guidance schema ensure failed: %s", exc)
        finally:
            _schema_once = True


__all__ = [
    "ensure_commercial_guidance_schema",
    "reset_commercial_guidance_schema_guard_for_tests",
]
