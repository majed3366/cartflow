# -*- coding: utf-8 -*-
"""اختيار صف ‎Store‎ لواجهات الودجيت العامة (‎public-config‎ / ‎ready‎) حسب ‎store_slug‎."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import Store
from services.vip_abandoned_cart_phone import resolve_store_row_for_cartflow_slug


def store_row_for_widget_public_api(store_slug: str) -> Optional[Store]:
    row = resolve_store_row_for_cartflow_slug(store_slug)
    if row is not None:
        return row
    try:
        return db.session.query(Store).order_by(Store.id.desc()).first()
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return None
