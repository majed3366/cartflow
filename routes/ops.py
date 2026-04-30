# -*- coding: utf-8 -*-
"""صحة الخدمة ومسارات اختبار زد (مرحلة التطوير)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy.exc import SQLAlchemyError

from extensions import db, get_database_url
from integrations.zid_client import fetch_abandoned_carts
from json_response import j
from models import Store

log = logging.getLogger("cartflow")

router = APIRouter()


def get_mock_abandoned_cart() -> dict:
    """نفس بيانات ‎GET /dev/mock-cart‎ — لإعادة الاستخدام دون ‎HTTP‎ داخلي."""
    from main import DEV_TEST_PHONE

    return {
        "id": "cart_123",
        "customer_name": "محمد",
        "phone": DEV_TEST_PHONE,
        "cart_value": 250,
        "cart_url": "https://example.com/cart/123",
        "items": [
            {"name": "عطر فاخر", "price": 250},
        ],
    }


@router.get("/health")
def health() -> Any:
    return j({"ok": True, "service": "cartflow"})


@router.get("/debug/db")
def debug_db() -> Any:
    uri = str(get_database_url() or "")
    return j(
        {
            "database_url_prefix": uri[:20],
            "is_sqlite": uri.lower().startswith("sqlite:"),
        }
    )


# تطوير فقط — بيانات سلة وهمية للواجهات/التدفق
@router.get("/dev/mock-cart")
def dev_mock_cart() -> Any:
    return j(get_mock_abandoned_cart())


_INIT_DB_KEY = "dev-init"


@router.get("/admin/init-db")
def admin_init_db(key: str = "") -> Any:
    if (key or "").strip() != _INIT_DB_KEY:
        return j({"ok": False, "error": "forbidden"}, 403)
    try:
        db.create_all()
    except SQLAlchemyError as e:
        log.warning("admin init-db: %s", e)
        return j(
            {
                "ok": False,
                "error": "create_all_failed",
            },
            500,
        )
    return j(
        {
            "ok": True,
            "message": "database initialized",
        }
    )


# تطوير فقط — لاختبار ‎/test/zid/abandoned-carts‎؛ احذفه أو اقفله قبل الإنتاج
@router.get("/dev/set-token")
def dev_set_token_get() -> Any:
    return _dev_set_token_impl("GET", "test-store", "TEST_TOKEN")


@router.post("/dev/set-token")
async def dev_set_token_post(request: Request) -> Any:
    try:
        data = await request.json()
    except Exception:  # noqa: BLE001
        data = None
    if not isinstance(data, dict):
        data = {}
    zid = (data.get("zid_store_id") or "").strip()
    token = (data.get("access_token") or "").strip()
    if not zid or not token:
        return j(
            {
                "ok": False,
                "error": "zid_store_id and access_token are required",
            },
            400,
        )
    return _dev_set_token_impl("POST", zid, token)


def _dev_set_token_impl(method: str, zid: str, token: str) -> Any:
    try:
        # ‎SQLite‎ / نسخة تطوير: تأكد من الجداول دون ‎create_all()‎ عند إقلاع التطبيق
        db.create_all()
        row = db.session.query(Store).filter_by(zid_store_id=zid).first()
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
        log.warning("dev set-token: %s", e)
        return j(
            {
                "ok": False,
                "error": "database_error",
            },
            500,
        )
    if method == "GET":
        return j({"ok": True})
    return j({"ok": True, "zid_store_id": zid, "is_active": True})


def _is_schema_error(exc: SQLAlchemyError) -> bool:
    """Missing table/column/relation — engine is up, schema not created or mismatch."""
    msg = (str(getattr(exc, "orig", None) or exc) or "").lower()
    if "no such table" in msg or "no such column" in msg:
        return True
    if "relation" in msg and "does not exist" in msg:
        return True
    return False


@router.get("/test/zid/abandoned-carts")
def test_zid_abandoned_carts() -> Any:
    try:
        store = db.session.query(Store).filter_by(is_active=True).first()
    except SQLAlchemyError as e:
        if _is_schema_error(e):
            return j(
                {
                    "ok": False,
                    "error": "no_database_schema",
                },
                200,
            )
        log.warning("test abandoned-carts: db error %s", e)
        return j(
            {
                "ok": False,
                "error": "database_unavailable",
            },
            503,
        )
    if not store or not (store.access_token or "").strip():
        return j({"ok": False, "error": "no_active_store_token"}, 200)
    body, status = fetch_abandoned_carts(store)
    return j(body, status)
