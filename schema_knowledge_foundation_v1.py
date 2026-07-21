# -*- coding: utf-8 -*-
"""Optional DDL for knowledge_statements (Knowledge Foundation + ciknow V1)."""
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

# Additive lineage columns for CIS → Knowledge intake (safe on existing ECF rows).
_CIKNOW_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("source_type", "VARCHAR(64)", "'evidence_confidence'"),
    ("source_contract_version", "VARCHAR(64)", "''"),
    ("source_synthesis_id", "VARCHAR(64)", "''"),
    ("source_synthesis_key", "VARCHAR(64)", "''"),
    ("source_rule_key", "VARCHAR(64)", "''"),
    ("source_rule_version", "VARCHAR(32)", "''"),
    ("source_fingerprint", "VARCHAR(64)", "''"),
    ("source_window_start", "TIMESTAMP", None),
    ("source_window_end", "TIMESTAMP", None),
    ("source_domains_json", "TEXT", "'[]'"),
    ("known_facts_json", "TEXT", "'[]'"),
    ("unknown_facts_json", "TEXT", "'[]'"),
    ("prohibited_claims_json", "TEXT", "'[]'"),
    ("is_current", "BOOLEAN", "TRUE"),
    ("superseded_at", "TIMESTAMP", None),
)


def reset_knowledge_foundation_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False


def _ensure_ciknow_columns(db: Any) -> None:
    insp = inspect(db.engine)
    if not insp.has_table("knowledge_statements"):
        return
    existing = {c["name"] for c in insp.get_columns("knowledge_statements")}
    dialect = db.engine.dialect.name
    for name, sql_type, default in _CIKNOW_COLUMNS:
        if name in existing:
            continue
        try:
            if dialect == "postgresql":
                if default is None:
                    stmt = (
                        f"ALTER TABLE knowledge_statements "
                        f"ADD COLUMN IF NOT EXISTS {name} {sql_type}"
                    )
                else:
                    stmt = (
                        f"ALTER TABLE knowledge_statements "
                        f"ADD COLUMN IF NOT EXISTS {name} {sql_type} "
                        f"DEFAULT {default}"
                    )
            else:
                # SQLite / others
                if default is None:
                    stmt = (
                        f"ALTER TABLE knowledge_statements "
                        f"ADD COLUMN {name} {sql_type}"
                    )
                else:
                    stmt = (
                        f"ALTER TABLE knowledge_statements "
                        f"ADD COLUMN {name} {sql_type} DEFAULT {default}"
                    )
            db.session.execute(text(stmt))
            db.session.commit()
        except SQLAlchemyError as exc:
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass
            log.warning("knowledge schema add column %s failed: %s", name, exc)


def ensure_knowledge_foundation_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    with _schema_once_lock:
        if _schema_once:
            return
        try:
            db.create_all()
            insp = inspect(db.engine)
            if not insp.has_table("knowledge_statements"):
                log.warning(
                    "knowledge foundation schema: knowledge_statements "
                    "missing after create_all"
                )
            else:
                _ensure_ciknow_columns(db)
        except SQLAlchemyError as exc:
            log.warning("knowledge foundation schema ensure failed: %s", exc)
        finally:
            _schema_once = True


__all__ = [
    "ensure_knowledge_foundation_schema",
    "reset_knowledge_foundation_schema_guard_for_tests",
]
