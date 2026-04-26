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


def ensure_store_widget_schema(db: Any) -> None:
    """يُنادى من مسارات ‎API‎ (لا يعتمد على ‎main‎)."""
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
