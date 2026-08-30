# -*- coding: utf-8 -*-
"""صحة الخدمة ومسارات اختبار زد (مرحلة التطوير)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from decision_engine import decide_recovery_action
from extensions import db, get_database_url
from integrations.zid_client import fetch_abandoned_carts
from json_response import j
from models import Store

log = logging.getLogger("cartflow")

router = APIRouter()


@router.get("/ping")
def ping():
    return {"ok": True}


@router.get("/config-check")
def config_check():
    from config_system import get_cartflow_config

    config = get_cartflow_config(store_slug="demo")

    return {
        "ok": True,
        "store_slug": "demo",
        "recovery_delay_minutes": config["recovery_delay_minutes"],
    }


@router.get("/decision-check")
def decision_check(reason_tag: str = "price_high"):
    result = decide_recovery_action(reason_tag)
    return {
        "ok": True,
        "reason_tag": reason_tag,
        "action": result["action"],
        "message": result["message"],
    }


def get_mock_abandoned_cart() -> dict:
    """نفس بيانات ‎GET /dev/mock-cart‎ — لإعادة الاستخدام دون ‎HTTP‎ داخلي."""
    from main import _cartflow_demo_test_phone

    return {
        "id": "cart_123",
        "customer_name": "محمد",
        "phone": _cartflow_demo_test_phone(),
        "cart_value": 250,
        "cart_url": "https://example.com/cart/123",
        "items": [
            {"name": "عطر فاخر", "price": 250},
        ],
    }


@router.get("/health")
def health(
    db_probe: int = Query(
        0,
        ge=0,
        le=1,
        alias="db",
        description="1=run SELECT 1 for load/integrity checks",
    ),
) -> Any:
    """
    خفيف لـ‎ LB‎؛ ‎?db=1‎ يُنفّذ ‎SELECT 1‎ (استخدمه باعتدال تحت الضغط العالي).
    """
    out: dict[str, Any] = {"ok": True, "service": "cartflow"}
    if int(db_probe) == 1:
        try:
            from services.db_resource_safety_v1.health_survivability_v1 import (
                health_db_probe_denied_payload,
                pool_pressure_blocks_db_probe,
            )

            blocked, pressure = pool_pressure_blocks_db_probe()
            if blocked:
                return j(health_db_probe_denied_payload(pressure), 503)
        except Exception:  # noqa: BLE001
            pass
        try:
            from services.database_network_guard_v1 import classify_database_url

            db.session.execute(text("SELECT 1"))
            dialect = getattr(getattr(db.session, "bind", None), "dialect", None)
            dialect_name = str(getattr(dialect, "name", "") or "")
            if dialect_name == "postgresql":
                db_name = db.session.execute(text("SELECT current_database()")).scalar()
            else:
                db_name = dialect_name or "local"
            db.session.commit()
            klass = str((classify_database_url() or {}).get("class") or "unknown")
            out["database"] = "ok"
            out["database_name"] = str(db_name or "")
            out["database_host_class"] = klass
        except SQLAlchemyError as e:
            db.session.rollback()
            log.warning("health db probe: %s", e)
            return j({"ok": False, "service": "cartflow", "database": "error"}, 503)
    return j(out)


@router.get("/health/scheduler")
def health_scheduler() -> Any:
    """
    Cached Scheduler liveness. Does not query Postgres.

    Safe for load balancers. Do not use /health/scheduler/deep as a Railway probe.
    """
    from services.recovery_process_role_v1 import build_scheduler_health_snapshot

    snap = build_scheduler_health_snapshot()
    status = 503 if not snap.get("ok") else 200
    return j(snap, status)


@router.get("/health/scheduler/deep")
def health_scheduler_deep(key: str = "") -> Any:
    """Admin-only, rate-limited DB diagnostic. Never a routine healthcheck."""
    from services.scheduler_deep_health_v1 import (
        SchedulerDeepHealthDenied,
        assert_deep_health_allowed,
        build_scheduler_deep_health_snapshot,
    )

    try:
        assert_deep_health_allowed(key)
    except SchedulerDeepHealthDenied as exc:
        code = 429 if str(exc) == "rate_limited" else 403
        return j({"ok": False, "error": str(exc)}, code)
    snap = build_scheduler_deep_health_snapshot()
    status = 503 if not snap.get("ok") else 200
    return j(snap, status)


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
