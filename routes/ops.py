# -*- coding: utf-8 -*-
"""صحة الخدمة ومسارات اختبار زد (مرحلة التطوير)."""
from __future__ import annotations

from flask import Blueprint, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError

from integrations.zid_client import fetch_abandoned_carts
from models import Store

bp = Blueprint("ops", __name__)


@bp.get("/health")
def health():
    return jsonify({"ok": True, "service": "cartflow"})


@bp.get("/test/zid/abandoned-carts")
def test_zid_abandoned_carts():
    try:
        store = Store.query.filter_by(is_active=True).first()
    except SQLAlchemyError as e:
        current_app.logger.warning("test abandoned-carts: db error %s", e)
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "database_unavailable",
                }
            ),
            503,
        )
    if not store or not (store.access_token or "").strip():
        return (
            jsonify({"ok": False, "error": "no_active_store_token"}),
            200,
        )
    body, status = fetch_abandoned_carts(store)
    return jsonify(body), status
