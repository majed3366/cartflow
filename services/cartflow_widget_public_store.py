# -*- coding: utf-8 -*-
"""اختيار صف ‎Store‎ لواجهات الودجيت العامة (‎public-config‎ / ‎ready‎) حسب ‎store_slug‎."""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import Store

_log = logging.getLogger("cartflow.widget_public_store")


def store_row_for_widget_public_session(
    session: Any, store_slug: str
) -> Optional[Store]:
    """
    Exact ‎zid_store_id‎ match only — no «latest Store» fallback (avoids wrong merchant row).
    """
    ss = (store_slug or "").strip()[:255]
    if not ss:
        return None
    try:
        return session.query(Store).filter(Store.zid_store_id == ss).first()
    except (SQLAlchemyError, OSError):
        try:
            session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None


def store_row_for_widget_public_api(store_slug: str) -> Optional[Store]:
    """Same canonical resolver as merchant dashboard (‎resolve_recovery_store_row_canonical‎)."""
    from services.recovery_store_lookup import resolve_recovery_store_row_canonical

    try:
        return resolve_recovery_store_row_canonical(
            store_slug, allow_schema_warm=False
        )
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return None
