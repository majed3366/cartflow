# -*- coding: utf-8 -*-
"""ترقية ‎DB‎ اختيارية: ‎stores.whatsapp_support_url‎ + جدول ‎abandonment_reason_logs‎."""
from __future__ import annotations

import logging
from typing import Any

import models  # noqa: F401  # تسجيل ‎ORM‎ بما فيه ‎AbandonmentReasonLog‎
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

log = logging.getLogger("cartflow")

_store_abandonment_schema_ensured = False
_recovery_reason_widget_cols_ensured = False


def ensure_recovery_reason_widget_schema(db: Any) -> None:
    """
    أعمدة ‎source / created_at‎ على ‎cart_recovery_reasons‎ (ودجت الطبقة ‎D‎).
    """
    global _recovery_reason_widget_cols_ensured
    if _recovery_reason_widget_cols_ensured:
        return
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("cart_recovery_reasons"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        created_sql_type = (
            "TIMESTAMP(0) WITH TIME ZONE"
            if dialect == "postgresql"
            else "DATETIME"
        )
        cols = {c["name"] for c in insp.get_columns("cart_recovery_reasons")}
        if "source" not in cols:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons "
                        "ADD COLUMN IF NOT EXISTS source VARCHAR(32) DEFAULT 'widget'"
                    )
                else:
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons "
                        "ADD COLUMN source VARCHAR(32) DEFAULT 'widget'"
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
        cols = {
            c["name"]
            for c in inspect(db.engine).get_columns("cart_recovery_reasons")
        }
        if "created_at" not in cols:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons ADD COLUMN IF NOT EXISTS "
                        "created_at " + created_sql_type
                    )
                else:
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons ADD COLUMN created_at "
                        + created_sql_type
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
            try:
                db.session.execute(
                    text(
                        "UPDATE cart_recovery_reasons SET created_at = updated_at "
                        "WHERE created_at IS NULL"
                    )
                )
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
        _recovery_reason_widget_cols_ensured = True
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("recovery_reason_widget_schema: %s", e)


def _ensure_reason_subcategory_columns(db: Any) -> None:
    """إضافة ‎sub_category‎ عند الترقية (جدول سابق بلا العمود). تُنادى بشكل idempotent."""
    try:
        db.create_all()
        for tname, stmt in (
            (
                "cart_recovery_reasons",
                "ALTER TABLE cart_recovery_reasons ADD COLUMN sub_category VARCHAR(64)",
            ),
            (
                "abandonment_reason_logs",
                "ALTER TABLE abandonment_reason_logs ADD COLUMN sub_category VARCHAR(64)",
            ),
        ):
            insp = inspect(db.engine)
            if not insp.has_table(tname):
                continue
            col_names = {c["name"] for c in insp.get_columns(tname)}
            if "sub_category" in col_names:
                continue
            try:
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget sub_category: %s", e)


def ensure_store_widget_schema(db: Any) -> None:
    """يُنادى من مسارات ‎API‎ (لا يعتمد على ‎main‎)."""
    _ensure_reason_subcategory_columns(db)
    ensure_recovery_reason_widget_schema(db)
    global _store_abandonment_schema_ensured
    if _store_abandonment_schema_ensured:
        return
    try:
        db.create_all()
        insp = inspect(db.engine)
        if insp.has_table("stores"):
            existing = {c["name"] for c in insp.get_columns("stores")}
            if "whatsapp_support_url" not in existing:
                try:
                    db.session.execute(
                        text("ALTER TABLE stores ADD COLUMN whatsapp_support_url VARCHAR(2048)")
                    )
                    db.session.commit()
                except (OSError, SQLAlchemyError, IntegrityError):
                    db.session.rollback()
        _store_abandonment_schema_ensured = True
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget: %s", e)
