# -*- coding: utf-8 -*-
"""صحة الخدمة ومسارات اختبار زد (مرحلة التطوير)."""
from __future__ import annotations

from flask import Blueprint, jsonify, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from integrations.zid_client import fetch_abandoned_carts
from models import Store

bp = Blueprint("ops", __name__)


@bp.get("/health")
def health():
    return jsonify({"ok": True, "service": "cartflow"})


@bp.get("/debug/db")
def debug_db():
    uri = str(current_app.config.get("SQLALCHEMY_DATABASE_URI") or "")
    return jsonify(
        {
            "database_url_prefix": uri[:20],
            "is_sqlite": uri.lower().startswith("sqlite:"),
        }
    )


_INIT_DB_KEY = "dev-init"


@bp.get("/admin/init-db")
def admin_init_db():
    if (request.args.get("key") or "").strip() != _INIT_DB_KEY:
        return jsonify({"ok": False, "error": "forbidden"}), 403
    try:
        db.create_all()
    except SQLAlchemyError as e:
        current_app.logger.warning("admin init-db: %s", e)
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "create_all_failed",
                }
            ),
            500,
        )
    return jsonify(
        {
            "ok": True,
            "message": "database initialized",
        }
    )


# تطوير فقط — لاختبار ‎/test/zid/abandoned-carts‎؛ احذفه أو اقفله قبل الإنتاج
@bp.route("/dev/set-token", methods=["GET", "POST"])
def dev_set_token():
    if request.method == "GET":
        zid = "test-store"
        token = "TEST_TOKEN"
    else:
        data = request.get_json(silent=True) or {}
        zid = (data.get("zid_store_id") or "").strip()
        token = (data.get("access_token") or "").strip()
        if not zid or not token:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "zid_store_id and access_token are required",
                    }
                ),
                400,
            )
    try:
        row = Store.query.filter_by(zid_store_id=zid).first()
        if row is None:
            row = Store(
                zid_store_id=zid,
                access_token=token,
                is_active=True,
            )
            db.session.add(row)
        else:
            row.access_token = token
            row.is_active = True
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.warning("dev set-token: %s", e)
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "database_error",
                }
            ),
            500,
        )
    if request.method == "GET":
        return jsonify({"ok": True})
    return jsonify({"ok": True, "zid_store_id": zid, "is_active": True})


def _is_schema_error(exc: SQLAlchemyError) -> bool:
    """Missing table/column/relation — engine is up, schema not created or mismatch."""
    msg = (str(getattr(exc, "orig", None) or exc) or "").lower()
    if "no such table" in msg or "no such column" in msg:
        return True
    if "relation" in msg and "does not exist" in msg:
        return True
    return False


@bp.get("/test/zid/abandoned-carts")
def test_zid_abandoned_carts():
    try:
        store = Store.query.filter_by(is_active=True).first()
    except SQLAlchemyError as e:
        if _is_schema_error(e):
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "no_database_schema",
                    }
                ),
                200,
            )
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
