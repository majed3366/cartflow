# -*- coding: utf-8 -*-
"""
CartFlow — تطبيق FastAPI الرئيسي لاستقبال الويبهوك ولوحة التاجر.
"""
import asyncio
import hashlib
import json
import logging
import os
import threading
import tempfile
import traceback
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import anthropic
import requests
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Body, FastAPI, Query, Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.trustedhost import TrustedHostMiddleware

from extensions import db, init_database, remove_scoped_session
from integrations.zid_client import exchange_code_for_token, verify_webhook_signature
from json_response import UTF8JSONResponse, j
from sqlalchemy import func, inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from decision_engine import decide_recovery_action

load_dotenv()

import models  # noqa: F401, E402
init_database()

# ASGI مُعطى ‎uvicorn / Railway‎: ‎python start.py‎ یا ‎uvicorn main:app‎ — ‎root_path‎ فارغ لعدم احتساب مسار خلف وكيل.
app = FastAPI(
    default_response_class=UTF8JSONResponse,
    title="CartFlow",
    root_path="",
)


@app.get("/ping")
def ping():
    return {"ok": True}


@app.get("/config-check")
def config_check():
    from config_system import get_cartflow_config

    config = get_cartflow_config(store_slug="demo")

    return {
        "ok": True,
        "store_slug": "demo",
        "recovery_delay_minutes": config["recovery_delay_minutes"],
    }


@app.get("/dev/routes")
def list_routes():
    return [route.path for route in app.routes]


@app.get("/dev/config-system-verify")
def config_system_verify():
    from config_system import get_cartflow_config

    config = get_cartflow_config(store_slug="demo")

    return {
        "ok": True,
        "config_loaded": True,
    }


@app.get("/decision-check")
def decision_check(reason_tag: str = "price_high"):
    result = decide_recovery_action(reason_tag)
    return {
        "ok": True,
        "reason_tag": reason_tag,
        "action": result["action"],
        "message": result["message"],
    }


@app.get("/webhook/whatsapp")
def whatsapp_webhook_get():
    return PlainTextResponse("WEBHOOK OK")


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()

    message = form.get("Body")
    from_number = form.get("From")

    print("[WA REPLY]", message)
    print("[WA FROM]", from_number)

    return PlainTextResponse("OK")


@app.post("/dev/whatsapp-decision-test")
def whatsapp_decision_test(payload: dict = Body(...)) -> dict[str, Any]:
    """تجربة قرار الواتساب + إرسال مباشر (يسجَّل أيضاً خارج ‎ENV=development‎ لمطابقة ‎/decision-check‎)."""
    from decision_engine import decide_recovery_action
    from services.whatsapp_send import send_whatsapp

    phone = payload.get("phone")
    reason_tag = payload.get("reason_tag")

    result = decide_recovery_action(reason_tag)
    message = result["message"]

    send_result = send_whatsapp(phone, message, reason_tag=reason_tag)
    print("[WHATSAPP TEST] phone=", phone)
    print("[WHATSAPP TEST] message=", message)
    print("[WHATSAPP TEST] result=", send_result)
    sent_ok = isinstance(send_result, dict) and send_result.get("ok") is True
    return {
        "ok": True,
        "reason_tag": reason_tag,
        "action": result["action"],
        "message": message,
        "send_result": send_result,
        "sent": sent_ok,
    }


app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],
)


app.state.secret_key = os.getenv("SECRET_KEY", "dev-only-change-in-production")
_ROOT = os.path.dirname(os.path.abspath(__file__))
# مسار مُطلَق: يعمل حتى اختلاف ‎working directory‎ على ‎Railway / Docker‎
templates = Jinja2Templates(directory=os.path.join(_ROOT, "templates"))
_static = os.path.join(_ROOT, "static")
if os.path.isdir(_static):
    app.mount("/static", StaticFiles(directory=_static), name="static")

from models import (  # noqa: E402
    AbandonedCart,
    CartRecoveryLog,
    CartRecoveryReason,
    ObjectionTrack,
    RecoveryEvent,
    Store,
)
from routes.cartflow import router as cartflow_router  # noqa: E402
from routes.cart_recovery_reason import router as cart_recovery_reason_router  # noqa: E402
from routes.demo_panel import router as demo_panel_router  # noqa: E402
from routes.ops import router as ops_router  # noqa: E402

app.include_router(ops_router)
app.include_router(cartflow_router)
app.include_router(cart_recovery_reason_router)
app.include_router(demo_panel_router, prefix="/demo")

from services.ai_message_builder import build_abandoned_cart_message  # noqa: E402
from services.whatsapp_recovery import build_whatsapp_recovery_message  # noqa: E402
from services.whatsapp_queue import start_whatsapp_queue_worker  # noqa: E402
from services.recovery_delay import get_recovery_delay  # noqa: E402
from services.whatsapp_send import (  # noqa: E402
    recovery_uses_real_whatsapp,
    send_whatsapp,
    should_send_whatsapp,
)
from schema_widget import ensure_store_widget_schema
from services.cartflow_whatsapp_mock import REASON_CHOICES as CF_REASON_CHOICES
from services.recovery_decision import get_primary_recovery_reason

log = logging.getLogger("cartflow")


def _ensure_store_widget_schema() -> None:
    ensure_store_widget_schema(db)


@app.get("/api/recovery/primary-reason")
def api_recovery_primary_reason(
    store_id: str = Query(..., min_length=1, max_length=255),
) -> Any:
    """
    أكثر سبب تردد من ‎CartRecoveryReason‎ لهذا المتجر (نفس مفتاح ‎store_slug‎ في الجدول).
    """
    try:
        db.create_all()
        slug = (store_id or "").strip()[:255]
        pr = get_primary_recovery_reason(slug)
        if not pr or pr not in CF_REASON_CHOICES:
            pr = "price"
        return j({"primary_reason": pr})
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("api_recovery_primary_reason: %s", e)
        return j({"primary_reason": "price"})


@app.on_event("startup")
async def _startup_whatsapp_queue() -> None:
    await start_whatsapp_queue_worker()


def _is_development_mode() -> bool:
    """
    ‎/dev/‎ يعمل فقط عند ‎ENV=development‎ صراحةً. غير ذلك = إنتاج (ويمكن ترك ‎ENV‎
    غير مضبوط). محلياً: أضف ‎ENV=development‎ إلى ‎.env‎.
    """
    return (os.getenv("ENV") or "").strip().lower() == "development"


def _app_test_client() -> Any:
    """يُستورد ‎TestClient‎ عند الاستدعاء فقط (تخفيف أعباء الاستيراد عند الإقلاع)."""
    from fastapi.testclient import TestClient

    return TestClient(app)


@app.middleware("http")
async def set_embed_csp_middleware(request: Request, call_next: Any) -> Any:
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001
        raise
    else:
        response.headers["X-Frame-Options"] = "ALLOWALL"
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors https://*.zid.sa https://zid.sa;"
        )
        return response
    finally:
        remove_scoped_session()


@app.middleware("http")
async def no_dev_in_production(request: Request, call_next: Any) -> Any:
    """يُنفَّذ أوّل مسار؛ ‎404‎ لـ ‎/dev‎ و ‎/dev/*‎ عندما ‎ENV‎ ليس ‎development‎ (استثناء: تجربة واتساب/قرار مسجّلة مع ‎/decision-check‎ في ‎Swagger‎)."""
    p = request.url.path
    if p == "/dev" or (p.startswith("/dev/") and p != "/dev/whatsapp-decision-test"):
        if not _is_development_mode():
            return Response(status_code=404)
    return await call_next(request)


def _app_route_get_exists(path: str) -> bool:
    for r in app.routes:
        p = getattr(r, "path", None)
        if p != path:
            continue
        m = getattr(r, "methods", None) or set()
        if "GET" in m:
            return True
    return False


def _minimal_get_request(path: str) -> Request:
    """
    ‎Request‎ بسيط لاستدعاء ‎view‎ مباشراً.
    ‎(بدل ‎TestClient‎: يتجنّب طلبات ‎ASGI‎ مُتداخلة + ضرب السجلات على ‎Railway‎.
    """
    bpath = path.encode("utf-8")
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "path": path,
            "raw_path": bpath,
            "root_path": "",
            "scheme": "http",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 0),
            "server": ("testserver", 80),
        }
    )


@app.get("/dev/run-flow")
def dev_run_flow():
    from routes.ops import get_mock_abandoned_cart

    cart = get_mock_abandoned_cart()
    message = build_abandoned_cart_message(cart)
    return j(
        {
            "cart": cart,
            "message": message,
        }
    )


_DEV_WIDGET_TEST_HTML = """<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CartFlow widget test</title>
</head>
<body>
<p style="font:14px system-ui;padding:1rem">اختبار الويدجت: 3 ث ثم 8 ث هدوء — تظهر الفقاعة.</p>
<script>
if (location.pathname.indexOf("/cart") < 0) {
  try { history.replaceState(null, "", "/dev/widget-test/cart"); } catch (e) {}
}
</script>
<script src="/static/cartflow_widget.js"></script>
</body>
</html>"""


@app.get("/dev/widget-test")
@app.get("/dev/widget-test/cart")
def dev_widget_test():
    return Response(
        content=_DEV_WIDGET_TEST_HTML, media_type="text/html; charset=utf-8"
    )


def _track_objection_cors(resp: Response) -> Response:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.api_route("/track/objection", methods=["POST", "OPTIONS"])
async def track_objection(request: Request):
    if request.method == "OPTIONS":
        return _track_objection_cors(
            Response(status_code=204, content=b"")
        )
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = None
    if not isinstance(body, dict):
        body = {}
    t = (body.get("type") or "").strip()
    if t not in ("price", "quality"):
        return _track_objection_cors(
            j({"ok": False, "error": "invalid_type"}, 400)
        )
    try:
        db.create_all()
        _ensure_objection_track_test_columns()
        now = datetime.utcnow()
        row = ObjectionTrack(object_type=t, created_at=now)
        db.session.add(row)
        db.session.commit()
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return _track_objection_cors(
            j({"ok": False, "error": str(e)}, 500)
        )
    return _track_objection_cors(j({"ok": True}))


_MSG_WA_PRICE = (
    "هلا 👋 لاحظنا إن السعر كان ممكن يكون سبب التردد… حبيت أقول لك إن المنتج هذا من أكثر الأشياء اللي الناس ترجع تشتريه لأنه فعلاً يستاهل."
)
_MSG_WA_QUALITY = (
    "هلا 👋 واضح إنك تهتم بالجودة… وهذا اختيار ممتاز 👍 المنتج هذا معروف إنه من أكثر المنتجات اللي الناس تثق فيها وترجع له."
)


@app.get("/dev/send-whatsapp-test")
def dev_send_whatsapp_test():
    try:
        db.create_all()
        _ensure_objection_track_test_columns()
        row = db.session.query(ObjectionTrack).order_by(
            ObjectionTrack.created_at.desc()
        ).first()
        if row is None:
            return j({"ok": False, "error": "no_objection"}, 404)
        t = (row.object_type or "").strip()
        if t == "price":
            msg = _MSG_WA_PRICE
        elif t == "quality":
            msg = _MSG_WA_QUALITY
        else:
            return j({"ok": False, "error": "unknown_type"}, 400)
        return j({"ok": True, "message": msg})
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


_WHATSAPP_TEST_CART = {
    "customer_name": "ماجد",
    "cart_url": "https://example.com/cart",
}

# ‎/dev/recovery-settings-test‎ — سجل ‎Store‎ اختباري عند عدم وجود بيانات
_DEV_RECOVERY_SETTINGS_STORE_ZID = "dev-recovery-settings-test"
# عند فرد ‎DB‎: سجل بـ ‎zid‎ ثابت (لتفادي تعدد ‎NULL‎ مع ‎UNIQUE‎) — آمن عند تزامن أول طلبات.
CARTFLOW_DEFAULT_RECOVERY_STORE_ZID = "cartflow-default-recovery"
_VALID_RECOVERY_UNITS = frozenset({"minutes", "hours", "days"})


def _ensure_default_store_for_recovery() -> None:
    """
    ينشئ ‎Store‎ افتراضياً عند عدم وجود أي سطر — للإنتاج وواجهة الاسترجاع.
    ‎recovery_delay=1، minutes، recovery_attempts=1‎. عند تزامن: ‎IntegrityError‎ ثم نُبقى السطر الحالي.
    """
    if db.session.query(Store).order_by(Store.id.desc()).first() is not None:
        return
    row = Store(
        zid_store_id=CARTFLOW_DEFAULT_RECOVERY_STORE_ZID,
        recovery_delay=1,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()


def _dev_apply_recovery_settings_update(
    recovery_delay: Any,
    recovery_delay_unit: Any,
    recovery_attempts: Any,
    *,
    whatsapp_support_url: Any = None,
    update_whatsapp: bool = False,
) -> Tuple[Dict[str, Any], int]:
    """
    نفس منطق ‎POST /dev/recovery-settings-update‎ — تعديل أحدث ‎Store‎ بعد التحقق.
    """
    if (
        recovery_delay is None
        or recovery_delay_unit is None
        or recovery_attempts is None
    ):
        return {"ok": False, "error": "missing_fields"}, 400
    try:
        rd_i = int(recovery_delay)
        ra_i = int(recovery_attempts)
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_number"}, 400
    if rd_i < 1:
        return {"ok": False, "error": "recovery_delay_min_1"}, 400
    if ra_i < 1:
        return {"ok": False, "error": "recovery_attempts_min_1"}, 400
    unit = (str(recovery_delay_unit) if recovery_delay_unit is not None else "").strip().lower()
    if unit not in _VALID_RECOVERY_UNITS:
        return {"ok": False, "error": "invalid_recovery_delay_unit"}, 400
    _ensure_store_widget_schema()
    db.create_all()
    _ensure_default_store_for_recovery()
    row = db.session.query(Store).order_by(Store.id.desc()).first()
    if row is None:
        return {"ok": False, "error": "no_store"}, 404
    row.recovery_delay = rd_i
    row.recovery_delay_unit = unit
    row.recovery_attempts = ra_i
    if update_whatsapp:
        if whatsapp_support_url is None or (
            isinstance(whatsapp_support_url, str) and not (whatsapp_support_url or "").strip()
        ):
            row.whatsapp_support_url = None
        else:
            row.whatsapp_support_url = str(whatsapp_support_url).strip()[:2048]
    db.session.commit()
    wa: Optional[str] = getattr(row, "whatsapp_support_url", None)
    if not (isinstance(wa, str) and wa.strip()):
        wa = None
    return {
        "ok": True,
        "recovery_delay": row.recovery_delay,
        "recovery_delay_unit": row.recovery_delay_unit,
        "recovery_attempts": row.recovery_attempts,
        "whatsapp_support_url": wa,
    }, 200

# ‎/dev/recovery-flow-test?type=…‎ — بدون قراءة من ‎DB‎
_RECOVERY_TEST_SCENARIOS = {
    "price_new": ("price", "new"),
    "quality_new": ("quality", "new"),
    "price_returning": ("price", "returning"),
}

# إضافة أعمدة ‎ObjectionTrack‎ اختيارية — جداول قديمة: ‎ALTER‎ (مرة لكل عملية بعد الإقلاع)
_objection_extras_ensured = False


def _ensure_objection_track_test_columns() -> None:
    """للتنمية/الإنتاج: ‎objection_tracks‎ يتوسّع بأعمدة اختيارية بلا فقد بيانات."""
    global _objection_extras_ensured
    if _objection_extras_ensured:
        return
    try:
        insp = inspect(db.engine)
        if not insp.has_table("objection_tracks"):
            return
    except (OSError, SQLAlchemyError):
        return
    existing = {c["name"] for c in insp.get_columns("objection_tracks")}
    dname = (db.engine.dialect.name or "").lower()
    t_dt = "TIMESTAMP WITH TIME ZONE" if dname in ("postgresql", "postgres") else "DATETIME"
    specs = (
        ("customer_name", "VARCHAR(500)"),
        ("customer_phone", "VARCHAR(100)"),
        ("cart_url", "VARCHAR(2048)"),
        ("customer_type", "VARCHAR(20)"),
        ("last_activity_at", t_dt),
    )
    for name, typ in specs:
        if name in existing:
            continue
        try:
            db.session.execute(text(f"ALTER TABLE objection_tracks ADD COLUMN {name} {typ}"))
        except (OSError, SQLAlchemyError):
            db.session.rollback()
            return
    try:
        db.session.commit()
    except (OSError, SQLAlchemyError):
        db.session.rollback()
        return
    _objection_extras_ensured = True


@app.get("/dev/whatsapp-message-test")
def dev_whatsapp_message_test():
    c = _WHATSAPP_TEST_CART
    return j(
        {
            "new_price": build_whatsapp_recovery_message("new", "price", c),
            "new_quality": build_whatsapp_recovery_message("new", "quality", c),
            "returning_price": build_whatsapp_recovery_message("returning", "price", c),
            "returning_quality": build_whatsapp_recovery_message("returning", "quality", c),
        }
    )


@app.get("/dev/should-send-test")
def dev_should_send_test():
    # محاكاة: نشاط حديث (< دقيقتين) مقابل سكون ≥ دقيقتين
    now = datetime.now(timezone.utc)
    recent = should_send_whatsapp(now - timedelta(minutes=1), now=now)
    idle = should_send_whatsapp(now - timedelta(minutes=3), now=now)
    return j({"recent": recent, "idle": idle})


@app.get("/dev/recovery-timing-test")
def dev_recovery_timing_test():
    """
    أزمنة ‎should_send_whatsapp‎ فقط (بدون واتساب) — للتجارب.
    """
    now = datetime.now(timezone.utc)
    last_recent = now - timedelta(minutes=1)
    last_idle = now - timedelta(minutes=3)
    return j(
        {
            "ok": True,
            "cases": {
                "recent_activity": {
                    "should_send": should_send_whatsapp(
                        last_recent, user_returned_to_site=False, now=now
                    ),
                },
                "idle_activity": {
                    "should_send": should_send_whatsapp(
                        last_idle, user_returned_to_site=False, now=now
                    ),
                },
            },
        }
    )


@app.get("/dev/recovery-delay-verify")
def dev_recovery_delay_verify():
    """
    استيثاق تأثير ‎recovery_delay‎: سكون ‎2‎ د مع حد ‎1‎ د ‎=‎ يُرسل، مع حد ‎5‎ د ‎=‎ لا.
    ‎Store‎ مُمثّل بـ ‎SimpleNamespace‎ (نفس حقول ‎Store.recovery_*‎).
    """
    now = datetime.now(timezone.utc)
    last = now - timedelta(minutes=2)
    store_fast = SimpleNamespace(
        recovery_delay=1,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    store_slow = SimpleNamespace(
        recovery_delay=5,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    return j(
        {
            "ok": True,
            "case_fast": {
                "should_send": should_send_whatsapp(
                    last,
                    user_returned_to_site=False,
                    now=now,
                    store=store_fast,
                )
            },
            "case_slow": {
                "should_send": should_send_whatsapp(
                    last,
                    user_returned_to_site=False,
                    now=now,
                    store=store_slow,
                )
            },
        }
    )


@app.get("/dev/recovery-attempts-verify")
def dev_recovery_attempts_verify():
    """
    سلة ثابتة: ‎sent_count=0‎ ثم ‎1‎ مع ‎recovery_attempts=1‎ — ‎should_send_whatsapp‎ فقط، بدون واتساب.
    """
    now = datetime.now(timezone.utc)
    last = now - timedelta(minutes=3)
    store = SimpleNamespace(
        recovery_delay=2,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    return j(
        {
            "ok": True,
            "first_attempt": {
                "should_send": should_send_whatsapp(
                    last,
                    user_returned_to_site=False,
                    now=now,
                    store=store,
                    sent_count=0,
                )
            },
            "second_attempt": {
                "should_send": should_send_whatsapp(
                    last,
                    user_returned_to_site=False,
                    now=now,
                    store=store,
                    sent_count=1,
                )
            },
        }
    )


@app.get("/dev/recovery-unit-verify")
def dev_recovery_unit_verify():
    """
    تحويل ‎recovery_delay_unit‎ (دقائق / ساعات / أيام) عبر ‎should_send_whatsapp‎ — بدون واتساب.
    """
    now = datetime.now(timezone.utc)
    last_minutes = now - timedelta(minutes=2)
    last_hours = now - timedelta(minutes=30)
    last_days = now - timedelta(hours=2)
    st_m = SimpleNamespace(
        recovery_delay=1,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    st_h = SimpleNamespace(
        recovery_delay=1,
        recovery_delay_unit="hours",
        recovery_attempts=1,
    )
    st_d = SimpleNamespace(
        recovery_delay=1,
        recovery_delay_unit="days",
        recovery_attempts=1,
    )
    return j(
        {
            "ok": True,
            "minutes_case": {
                "should_send": should_send_whatsapp(
                    last_minutes,
                    user_returned_to_site=False,
                    now=now,
                    store=st_m,
                    sent_count=0,
                )
            },
            "hours_case": {
                "should_send": should_send_whatsapp(
                    last_hours,
                    user_returned_to_site=False,
                    now=now,
                    store=st_h,
                    sent_count=0,
                )
            },
            "days_case": {
                "should_send": should_send_whatsapp(
                    last_days,
                    user_returned_to_site=False,
                    now=now,
                    store=st_d,
                    sent_count=0,
                )
            },
        }
    )


@app.get("/dev/recovery-duplicate-test")
def dev_recovery_duplicate_test():
    """
    تكرار لنفس «السلة»: المحاولة الأولى — سكون ≥ دقيقتين يُسمح بالإرسال.
    بعدها نُمثّل تسجيل لمسة/إرسال (آخر نشاط = ‎now‎) فينخفض الإرسال لاحقاً بمنطق ‎should_send_whatsapp‎ فقط.
    """
    now = datetime.now(timezone.utc)
    first_last = now - timedelta(minutes=3)
    first = should_send_whatsapp(
        first_last, user_returned_to_site=False, now=now
    )
    # محاكاة: نفس السلة لكن بعد تسجيل الاسترجاع «آخر نشاط» = الآن (ضمن ‎2‎ د) → لا إرسال ثانٍ
    second = should_send_whatsapp(now, user_returned_to_site=False, now=now)
    return j(
        {
            "ok": True,
            "first_attempt": {
                "should_send": first,
            },
            "second_attempt": {
                "should_send": second,
            },
        }
    )


@app.get("/dev/recovery-settings-test")
def dev_recovery_settings_test():
    """
    آخر ‎Store‎: حقول ‎recovery_*‎ (بدون واتساب / بدون تغيير منطق الاسترجاع).
    إن لم يوجد متجر: يُنشأ سجل تجريبي بإعدادات افتراضية.
    """
    try:
        db.create_all()
        row = db.session.query(Store).order_by(Store.id.desc()).first()
        if row is None:
            row = Store(
                zid_store_id=_DEV_RECOVERY_SETTINGS_STORE_ZID,
                recovery_delay=2,
                recovery_delay_unit="minutes",
                recovery_attempts=1,
            )
            db.session.add(row)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                row = db.session.query(Store).order_by(Store.id.desc()).first()
            if row is None:
                return j({"ok": False, "error": "no_store"}, 500)
        return j(
            {
                "ok": True,
                "recovery_delay": row.recovery_delay,
                "recovery_delay_unit": row.recovery_delay_unit,
                "recovery_attempts": row.recovery_attempts,
            }
        )
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


@app.post("/dev/recovery-settings-update")
async def dev_recovery_settings_update(request: Request):
    """
    يحدّث أحدث ‎Store‎ — ‎recovery_delay / unit / recovery_attempts‎ (تجارب فقط).
    """
    try:
        db.create_all()
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = None
        if not isinstance(body, dict):
            return j({"ok": False, "error": "json_object_required"}, 400)
        uw = "whatsapp_support_url" in body
        data, code = _dev_apply_recovery_settings_update(
            body.get("recovery_delay"),
            body.get("recovery_delay_unit"),
            body.get("recovery_attempts"),
            whatsapp_support_url=body.get("whatsapp_support_url") if uw else None,
            update_whatsapp=uw,
        )
        return j(data, code)
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


@app.post("/api/recovery-settings")
async def api_recovery_settings(request: Request):
    """
    واجهة ‎API‎ — تحديث أحدث ‎Store‎ (نفس التحقق والمنطق مثل ‎/dev/recovery-settings-update‎).
    """
    try:
        db.create_all()
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = None
        if not isinstance(body, dict):
            return j({"ok": False, "error": "json_object_required"}, 400)
        uw = "whatsapp_support_url" in body
        data, code = _dev_apply_recovery_settings_update(
            body.get("recovery_delay"),
            body.get("recovery_delay_unit"),
            body.get("recovery_attempts"),
            whatsapp_support_url=body.get("whatsapp_support_url") if uw else None,
            update_whatsapp=uw,
        )
        return j(data, code)
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


@app.get("/api/recovery-settings")
def api_recovery_settings_get():
    """
    واجهة ‎API‎ — قراءة أحدث ‎Store.recovery_*‎.
    """
    try:
        _ensure_store_widget_schema()
        db.create_all()
        _ensure_default_store_for_recovery()
        row = db.session.query(Store).order_by(Store.id.desc()).first()
        if row is None:
            return j({"ok": False, "error": "no_store"}, 500)
        wa: Optional[str] = getattr(row, "whatsapp_support_url", None)
        if not (isinstance(wa, str) and wa.strip()):
            wa = None
        return j(
            {
                "ok": True,
                "recovery_delay": row.recovery_delay,
                "recovery_delay_unit": row.recovery_delay_unit,
                "recovery_attempts": row.recovery_attempts,
                "whatsapp_support_url": wa,
            }
        )
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


# جلسة واحدة = تسلسل استرجاع + ‎sent‎ عند اكتمال الخطوات (لكل عملية ‎worker‎)
_session_recovery_started: dict[str, bool] = {}
_session_recovery_logged: dict[str, bool] = {}
_session_recovery_sent: dict[str, bool] = {}
_session_recovery_converted: dict[str, bool] = {}
_recovery_session_lock = threading.Lock()

# خطوة إضافية منطقية (سابقاً كان عندها خطوتان أخريان) — لسجلات «توقفت بعد الأولى»
_RECOVERY_SEQUENCE_STEPS: tuple[tuple[int, str], ...] = (
    (1, "يبدو أنك نسيت سلتك 🛒"),
    (2, "المنتج اللي اخترته عليه طلب عالي"),
    (3, "ممكن يخلص قريب 👀"),
)

_DEFAULT_DECISION_FALLBACK_MESSAGE = (
    "لاحظنا إنك مهتم 👌 حاب نساعدك تكمل الطلب؟"
)


def _normalize_store_slug(payload: dict[str, Any]) -> str:
    raw = payload.get("store")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return "default"


def _session_part_from_payload(payload: dict[str, Any]) -> str:
    """بصمة الجلسة/السلة (نفس الجزء الثاني من ‎recovery_key‎)."""
    sid = payload.get("session_id")
    if isinstance(sid, str) and sid.strip():
        return sid.strip()
    cid = payload.get("cart_id")
    if isinstance(cid, str) and cid.strip():
        return cid.strip()
    cart = payload.get("cart")
    raw = json.dumps(cart if cart is not None else [], sort_keys=True, default=str)
    return "fp:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _recovery_key_from_payload(payload: dict[str, Any]) -> str:
    """مفتاح عزل الاسترجاع: ‎store_slug + session_id‎ (أو ‎cart_id / بصمة السلة‎ عند الغياب)."""
    store_slug = _normalize_store_slug(payload)
    return f"{store_slug}:{_session_part_from_payload(payload)}"


def _recovery_key_from_store_and_session(store_slug: str, session_id: str) -> str:
    """نفس ‎recovery_key‎ المستخدم في أحداث السلة — لـ ‎POST /api/conversion‎."""
    return _recovery_key_from_payload(
        {"store": store_slug, "session_id": session_id}
    )


def _cart_id_str_from_payload(payload: dict[str, Any]) -> Optional[str]:
    c = payload.get("cart_id")
    if c is None:
        return None
    s = str(c).strip()
    return s if s else None


def _recovery_message_for_step(step: int) -> str:
    for s, t in _RECOVERY_SEQUENCE_STEPS:
        if s == step:
            return t
    return _RECOVERY_SEQUENCE_STEPS[0][1]


def _default_recovery_message() -> str:
    """نص الخطوة ‎1‎ (للتوافق مع السجلات السابقة/التخطي)."""
    return _recovery_message_for_step(1)


def _reason_tag_for_session(store_slug: str, session_id: str) -> Optional[str]:
    """آخر ‎reason_tag‎ محفوظ في ‎cart_recovery_reasons‎ لهذه الجلسة، أو ‎None‎."""
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    if not ss or not sid:
        return None
    try:
        db.create_all()
        row = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == ss,
                CartRecoveryReason.session_id == sid,
            )
            .order_by(CartRecoveryReason.updated_at.desc())
            .first()
        )
        if row is None:
            return None
        tag = (row.reason or "").strip()
        return tag if tag else None
    except Exception:  # noqa: BLE001
        db.session.rollback()
        return None


def _is_user_converted(recovery_key: str) -> bool:
    with _recovery_session_lock:
        return bool(_session_recovery_converted.get(recovery_key))


def _mark_user_converted_for_payload(payload: dict[str, Any]) -> None:
    key = _recovery_key_from_payload(payload)
    with _recovery_session_lock:
        _session_recovery_converted[key] = True
    log.info("user_converted recorded for recovery_key=%s", key)


def _mark_session_converted(store_slug: str, session_id: str) -> str:
    """يضبط تحويلاً للجلسة (شراء مكتمل). يُرجع ‎recovery_key‎."""
    key = _recovery_key_from_store_and_session(store_slug, session_id)
    with _recovery_session_lock:
        _session_recovery_converted[key] = True
    log.info("conversion recorded for recovery_key=%s", key)
    return key


def _persist_cart_recovery_log(
    *,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    phone: Optional[str],
    message: str,
    status: str,
    sent_at: Optional[datetime] = None,
    step: Optional[int] = None,
) -> None:
    try:
        db.create_all()
        row = CartRecoveryLog(
            store_slug=store_slug[:255],
            session_id=session_id[:512],
            cart_id=(cart_id[:255] if cart_id else None),
            phone=(phone[:100] if phone else None),
            message=message or "",
            status=status[:50],
            step=step,
            created_at=datetime.now(timezone.utc),
            sent_at=sent_at,
        )
        db.session.add(row)
        db.session.commit()
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        log.warning("CartRecoveryLog persist failed: %s", e)


def _try_claim_recovery_session(recovery_key: str) -> bool:
    """
    يضبط ‎recovery_started‎ لـ ‎recovery_key‎ (لكل متجر + جلسة) قبل جدولة المهمة.
    """
    with _recovery_session_lock:
        if _session_recovery_started.get(recovery_key):
            return False
        _session_recovery_started[recovery_key] = True
        return True


_MOCK_RECOVERY_PHONE = "0500000000"


def _recovery_destination_phone() -> str:
    """
    رقم الوجهة لرسائل الاسترجاع.
    ‎WHATSAPP_RECOVERY_TO_PHONE‎ اختياري: للاختبار بأرقام ‎WABA‎ الخاصة بك فقط قبل العملاء.
    بدون ضبط: نفس الرقم الوهمي السابق (سلوك قديم).
    """
    o = (os.getenv("WHATSAPP_RECOVERY_TO_PHONE") or "").strip()
    if o:
        return o[:100]
    return _MOCK_RECOVERY_PHONE


async def _run_recovery_sequence_after_cart_abandoned(
    recovery_key: str,
    delay_seconds: float,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
) -> None:
    """
    ينتظر ‎delay_seconds‎ ثم يرسل رسالة واتساب واحدة: نص من محرّك القراءة حسب ‎reason_tag‎
    المحفوظ، أو رسالة احتياطية. إرسال عبر ‎send_whatsapp‎ (بدون خطوات إضافية ولا تأخيرات جديدة).
    """
    try:
        await asyncio.sleep(delay_seconds)
    except asyncio.CancelledError:
        raise
    with _recovery_session_lock:
        if _session_recovery_logged.get(recovery_key):
            return
        _session_recovery_logged[recovery_key] = True
    print("recovery triggered after delay (single message, decision engine)")
    if _is_user_converted(recovery_key):
        print("recovery sequence stopped: user converted (after initial delay, before step 1)")
        t1 = _recovery_message_for_step(1)
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=t1,
            status="stopped_converted",
            step=1,
        )
        return

    step_num = 1
    reason_tag = _reason_tag_for_session(store_slug, session_id)
    if reason_tag is not None:
        text = decide_recovery_action(reason_tag)["message"]
    else:
        text = _DEFAULT_DECISION_FALLBACK_MESSAGE

    phone = _recovery_destination_phone()
    _persist_cart_recovery_log(
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        phone=phone,
        message=text,
        status="queued",
        step=step_num,
    )
    if _is_user_converted(recovery_key):
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status="stopped_converted",
            step=step_num,
        )
        return

    send_whatsapp(phone, text, reason_tag=reason_tag)

    now = datetime.now(timezone.utc)
    _persist_cart_recovery_log(
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        phone=phone,
        message=text,
        status="mock_sent",
        sent_at=now,
        step=step_num,
    )
    # إن كان التحويل أثناء الإرسال: سلوك شبيه بالتخطي بعد خطوة أولى
    if _is_user_converted(recovery_key):
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=_recovery_message_for_step(2),
            status="stopped_converted",
            step=2,
        )
        return

    with _recovery_session_lock:
        _session_recovery_sent[recovery_key] = True
    print("recovery marked as sent (single message)")


async def handle_cart_abandoned(
    background_tasks: BackgroundTasks, payload: dict[str, Any]
) -> dict[str, Any]:
    store_slug = _normalize_store_slug(payload)
    print("store:", store_slug)
    recovery_key = _recovery_key_from_payload(payload)
    print("recovery key:", recovery_key)
    session_id_log = _session_part_from_payload(payload)
    cart_id_log = _cart_id_str_from_payload(payload)
    msg_log = _default_recovery_message()
    if _is_user_converted(recovery_key):
        print("recovery skipped: user already converted")
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id_log,
            cart_id=cart_id_log,
            phone=None,
            message=msg_log,
            status="stopped_converted",
        )
        return {
            "recovery_scheduled": False,
            "recovery_skipped": True,
            "recovery_state": "converted",
        }
    with _recovery_session_lock:
        if _session_recovery_sent.get(recovery_key):
            print("recovery already sent, skipping")
            _persist_cart_recovery_log(
                store_slug=store_slug,
                session_id=session_id_log,
                cart_id=cart_id_log,
                phone=None,
                message=msg_log,
                status="skipped_delay",
            )
            return {
                "recovery_scheduled": False,
                "recovery_skipped": True,
                "recovery_state": "sent",
            }
    if not _try_claim_recovery_session(recovery_key):
        print("recovery already scheduled, skipping")
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id_log,
            cart_id=cart_id_log,
            phone=None,
            message=msg_log,
            status="skipped_duplicate",
        )
        return {
            "recovery_scheduled": False,
            "recovery_skipped": True,
            "recovery_state": "pending",
        }
    # ‎_session_recovery_started[recovery_key]‎ مضبوط — قبل تحميل المتجر أو ‎add_task‎
    print("entered recovery handler")
    log.info("cart abandoned received")
    try:
        db.create_all()
        _ensure_default_store_for_recovery()
        store = db.session.query(Store).order_by(Store.id.desc()).first()
    except Exception:  # noqa: BLE001
        db.session.rollback()
        store = None
    print("store settings loaded")
    reason_tag = _reason_tag_for_session(store_slug, session_id_log)
    config = None  # future: dashboard may pass recovery_delays overrides
    delay_s = float(get_recovery_delay(reason_tag, store_config=config))
    print("starting delay task")
    background_tasks.add_task(
        _run_recovery_sequence_after_cart_abandoned,
        recovery_key,
        delay_s,
        store_slug,
        session_id_log,
        cart_id_log,
    )
    return {
        "recovery_scheduled": True,
        "recovery_delay_seconds": delay_s,
        "recovery_state": "scheduled",
    }


@app.post("/api/cart-event")
async def api_cart_event(request: Request, background_tasks: BackgroundTasks):
    """
    أحداث سلة من الواجهة (مثل ‎cart_abandoned‎).
    يقبل ‎store‎ (معرّف المتجر/السياق) مع ‎session_id‎ و‎cart‎.
    عند ‎cart_abandoned‎: لا إرسال فوري — جدولة مؤجّلة حسب ‎Store.recovery_*‎؛ مفتاح الاسترجاع ‎store + session‎.
    بدون واتساب.
    """
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        payload = None
    if not isinstance(payload, dict):
        payload = {}
    out: dict[str, Any] = {
        "ok": True,
        "event": payload.get("event"),
    }
    if (
        payload.get("user_converted") is True
        or payload.get("event") == "user_converted"
        or payload.get("purchase_completed") is True
    ):
        _mark_user_converted_for_payload(payload)
        out["conversion_tracked"] = True
    if payload.get("event") == "cart_abandoned":
        out.update(await handle_cart_abandoned(background_tasks, payload))
    return j(out, 200)


@app.post("/api/conversion")
async def api_conversion(request: Request) -> Any:
    """
    يعلّم جلسة كمُحوّلة (شراء مكتمل) — يوقف تسلسل الاسترجاع.
    جسم: ‎store_slug‎، ‎session_id‎؛ ‎purchase_completed: true‎ اختياري للتحقق.
    """
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = None
    if not isinstance(body, dict):
        return j({"ok": False, "error": "json_object_required"}, 400)
    ss = body.get("store_slug")
    sid = body.get("session_id")
    if not isinstance(ss, str) or not str(ss).strip():
        return j({"ok": False, "error": "store_slug_required"}, 400)
    if not isinstance(sid, str) or not str(sid).strip():
        return j({"ok": False, "error": "session_id_required"}, 400)
    if "purchase_completed" in body and body.get("purchase_completed") is not True:
        return j({"ok": False, "error": "purchase_completed_must_be_true"}, 400)
    key = _mark_session_converted(str(ss).strip(), str(sid).strip())
    return j(
        {
            "ok": True,
            "purchase_completed": True,
            "recovery_key": key,
        }
    )


@app.get("/dev/recovery-settings-read-test")
def dev_recovery_settings_read_test():
    """
    نفس ‎GET /api/recovery-settings‎ (استدعاء مباشر لنفس الدالة).
    إن لم يوجد ‎Store‎: إنشاء تجريبي ‎15 / minutes / 2‎.
    """
    try:
        db.create_all()
        if db.session.query(Store).order_by(Store.id.desc()).first() is None:
            _row = Store(
                zid_store_id=_DEV_RECOVERY_SETTINGS_STORE_ZID,
                recovery_delay=15,
                recovery_delay_unit="minutes",
                recovery_attempts=2,
            )
            db.session.add(_row)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
            if db.session.query(Store).order_by(Store.id.desc()).first() is None:
                return j({"ok": False, "error": "no_store"}, 500)
        return api_recovery_settings_get()
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


@app.get("/dev/recovery-dashboard-test")
def dev_recovery_dashboard_test():
    """
    محاكاة لوحة: ‎GET /api/recovery-settings‎ ثم ‎POST‎ ثم ‎GET‎ (عبر ‎TestClient‎).
    """
    try:
        db.create_all()
        tc = _app_test_client()
        jdata = tc.get("/api/recovery-settings").json()
        if not jdata or not jdata.get("ok"):
            if db.session.query(Store).order_by(Store.id.desc()).first() is None:
                _row = Store(
                    zid_store_id=_DEV_RECOVERY_SETTINGS_STORE_ZID,
                    recovery_delay=15,
                    recovery_delay_unit="minutes",
                    recovery_attempts=2,
                )
                db.session.add(_row)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
            jdata = tc.get("/api/recovery-settings").json()
        if not jdata or not jdata.get("ok"):
            return j({"ok": False, "error": "no_store"}, 500)
        before = {
            "recovery_delay": jdata["recovery_delay"],
            "recovery_delay_unit": jdata["recovery_delay_unit"],
            "recovery_attempts": jdata["recovery_attempts"],
        }
        r_post = tc.post(
            "/api/recovery-settings",
            json={
                "recovery_delay": 20,
                "recovery_delay_unit": "minutes",
                "recovery_attempts": 2,
            },
        )
        j_post = r_post.json()
        if not j_post or not j_post.get("ok"):
            return j(
                {
                    "ok": False,
                    "error": j_post.get("error", "post_failed") if j_post else "post_failed",
                },
                400,
            )
        j2 = tc.get("/api/recovery-settings").json()
        if not j2 or not j2.get("ok"):
            return j({"ok": False, "error": "read_after_failed"}, 500)
        after = {
            "recovery_delay": j2["recovery_delay"],
            "recovery_delay_unit": j2["recovery_delay_unit"],
            "recovery_attempts": j2["recovery_attempts"],
        }
        return j({"ok": True, "before": before, "after": after})
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


def _ensure_dev_readiness_store() -> bool:
    """
    لمسار ‎/dev/platform-readiness-test‎ فقط: تضمين ‎Store‎ اختباري عند عدم وجود سجل
    (نفس فكرة ‎/dev/recovery-settings-test‎) حتى ‎GET/POST /api/recovery-settings‎
    ينجحان على ‎Railway‎.
    """
    db.create_all()
    row = db.session.query(Store).order_by(Store.id.desc()).first()
    if row is not None:
        return True
    row = Store(
        zid_store_id=_DEV_RECOVERY_SETTINGS_STORE_ZID,
        recovery_delay=2,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        row = db.session.query(Store).order_by(Store.id.desc()).first()
    return row is not None


@app.get("/dev/platform-readiness-test")
def dev_platform_readiness_test():
    """
    فحوص سريعة: ‎API‎، لوحة، ‎send_whatsapp‎ وهمي، ‎should_send_whatsapp‎.
    بدون ‎TestClient‎ — استدعاء مباشر فقط (طلب ‎HTTP‎ واحد = سجل وصول واحد).
    """
    from inspect import getsource  # stdlib (لا يتعارض مع ‎sqlalchemy.inspect‎)

    if not _ensure_dev_readiness_store():
        get_ok = False
        post_ok = False
    else:
        api_r = api_recovery_settings_get()
        try:
            jg = json.loads((api_r.body or b"{}").decode("utf-8"))
        except (json.JSONDecodeError, UnicodeError):
            jg = None
        get_ok = bool(isinstance(jg, dict) and (jg.get("ok") is True))
        post_ok = False
        if get_ok and isinstance(jg, dict):
            pbody, pcode = _dev_apply_recovery_settings_update(
                jg.get("recovery_delay"),
                jg.get("recovery_delay_unit"),
                jg.get("recovery_attempts"),
            )
            post_ok = bool(
                pcode == 200
                and isinstance(pbody, dict)
                and pbody.get("ok") is True
            )
    recovery_settings_api_ready = bool(get_ok and post_ok)
    d = dashboard_recovery_settings(
        _minimal_get_request("/dashboard/recovery-settings")
    )
    dct = d.body or b""
    dashboard_flow_ready = bool(
        d.status_code == 200 and (b"recovery_delay" in dct)
    )
    s_src = getsource(send_whatsapp)
    whatsapp_send_is_mocked = bool(
        "no provider" in s_src.lower() and "logger" in s_src
    )
    _now = datetime.now(timezone.utc)
    _last = _now - timedelta(minutes=3)
    recovery_logic_ready = bool(
        should_send_whatsapp(
            _last, user_returned_to_site=False, now=_now, store=None, sent_count=0
        )
    )
    all_ok = all(
        [
            recovery_settings_api_ready,
            dashboard_flow_ready,
            whatsapp_send_is_mocked,
            recovery_logic_ready,
        ]
    )
    return {
        "ok": all_ok,
        "recovery_settings_api_ready": recovery_settings_api_ready,
        "dashboard_flow_ready": dashboard_flow_ready,
        "whatsapp_send_is_mocked": whatsapp_send_is_mocked,
        "recovery_logic_ready": recovery_logic_ready,
    }


@app.get("/dev/recovery-dashboard-render-test")
def dev_recovery_dashboard_render_test():
    """
    يتحقق من مسار ‎/dashboard/recovery-settings‎ وأن الرد ‎HTML‎.
    """
    try:
        route_exists = _app_route_get_exists("/dashboard/recovery-settings")
        tc = _app_test_client()
        resp = tc.get("/dashboard/recovery-settings")
        head = (resp.content or b"")[:3000]
        head_l = head.lstrip().lower()
        ct = (resp.headers.get("Content-Type") or "").lower()
        returns_html = bool(
            resp.status_code == 200
            and "text/html" in ct
            and (
                head_l.startswith(b"<!doctype")
                or head_l.startswith(b"<html")
            )
        )
        ok = bool(route_exists and returns_html)
        return j(
            {
                "ok": ok,
                "route_exists": route_exists,
                "returns_html": returns_html,
            }
        )
    except Exception as e:  # noqa: BLE001
        return j(
            {
                "ok": False,
                "error": str(e),
                "route_exists": False,
                "returns_html": False,
            },
            500,
        )


@app.get("/dev/recovery-settings-api-test")
def dev_recovery_settings_api_test():
    """
    نفس جسم ‎POST /api/recovery-settings‎ — ‎15 / minutes / 2‎ عبر ‎_dev_apply_recovery_settings_update‎.
    """
    try:
        db.create_all()
        if db.session.query(Store).order_by(Store.id.desc()).first() is None:
            _row = Store(
                zid_store_id=_DEV_RECOVERY_SETTINGS_STORE_ZID,
                recovery_delay=2,
                recovery_delay_unit="minutes",
                recovery_attempts=1,
            )
            db.session.add(_row)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
            if db.session.query(Store).order_by(Store.id.desc()).first() is None:
                return j({"ok": False, "error": "no_store"}, 500)
        data, code = _dev_apply_recovery_settings_update(15, "minutes", 2)
        return j(data, code)
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


@app.get("/dev/recovery-settings-update-test")
def dev_recovery_settings_update_test():
    """
    يستدعي نفس تعديل الإعدادات: ‎10 / minutes / 1‎ — من غير ‎JSON‎ (للمتصفح/السريع).
    إن لم يوجد ‎Store‎: يُنشأ سجل تجريبي مثل ‎/dev/recovery-settings-test‎ ثم التحديث.
    """
    try:
        db.create_all()
        if db.session.query(Store).order_by(Store.id.desc()).first() is None:
            _row = Store(
                zid_store_id=_DEV_RECOVERY_SETTINGS_STORE_ZID,
                recovery_delay=2,
                recovery_delay_unit="minutes",
                recovery_attempts=1,
            )
            db.session.add(_row)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
            if db.session.query(Store).order_by(Store.id.desc()).first() is None:
                return j({"ok": False, "error": "no_store"}, 500)
        data, code = _dev_apply_recovery_settings_update(10, "minutes", 1)
        return j(data, code)
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


@app.get("/dev/recovery-settings-live-verify")
def dev_recovery_settings_live_verify():
    """
    يثبّت ‎10‎ د ‎+‎ دقائق على أحدث ‎Store‎، ثم ‎should_send_whatsapp(last = now-5d)‎ ينبغي ‎false‎.
    """
    try:
        db.create_all()
        if db.session.query(Store).order_by(Store.id.desc()).first() is None:
            _row = Store(
                zid_store_id=_DEV_RECOVERY_SETTINGS_STORE_ZID,
                recovery_delay=2,
                recovery_delay_unit="minutes",
                recovery_attempts=1,
            )
            db.session.add(_row)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
            if db.session.query(Store).order_by(Store.id.desc()).first() is None:
                return j({"ok": False, "error": "no_store"}, 500)
        data, code = _dev_apply_recovery_settings_update(10, "minutes", 1)
        if code != 200:
            return j(data, code)
        row = db.session.query(Store).order_by(Store.id.desc()).first()
        now = datetime.now(timezone.utc)
        last = now - timedelta(minutes=5)
        ss = should_send_whatsapp(
            last,
            user_returned_to_site=False,
            now=now,
            store=row,
            sent_count=0,
        )
        return j(
            {
                "ok": True,
                "recovery_delay": data["recovery_delay"],
                "recovery_delay_unit": data["recovery_delay_unit"],
                "should_send": ss,
            }
        )
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


@app.get("/dev/create-test-objection")
def dev_create_test_objection():
    """
    ينشئ ‎ObjectionTrack‎ اختباري (تجارب ‎/dev/recovery-flow-test‎ فقط) — بدون واتساب.
    """
    try:
        db.create_all()
        _ensure_objection_track_test_columns()
        now = datetime.now(timezone.utc)
        last = now - timedelta(minutes=3)
        row = ObjectionTrack(
            object_type="price",
            created_at=now,
            customer_name="ماجد",
            customer_phone="0500000000",
            cart_url="https://example.com/cart",
            customer_type="new",
            last_activity_at=last,
        )
        db.session.add(row)
        db.session.commit()
        return j({"ok": True, "objection_id": row.id})
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


@app.get("/dev/recovery-flow-test")
def dev_recovery_flow_test(request: Request):
    """
    تدفق كامل: آخر objection + نص الاسترجاع + ‎should_send‎ (سكون مُدخَّل) + ‎send_whatsapp‎ وهمي.
    ‎?type=price_new|quality_new|price_returning‎ — مُنطَق ثابت دون ‎DB‎.
    """
    try:
        sc = (request.query_params.get("type") or "").strip()
        if sc:
            if sc not in _RECOVERY_TEST_SCENARIOS:
                return j({"ok": False, "error": "invalid_type"}, 400)
            t, customer_type = _RECOVERY_TEST_SCENARIOS[sc]
            cart = {
                "customer_name": "ماجد",
                "cart_url": "https://example.com/cart",
            }
            message = build_whatsapp_recovery_message(customer_type, t, cart)
            now = datetime.now(timezone.utc)
            last = now - timedelta(minutes=3)
            db.create_all()
            st = db.session.query(Store).order_by(Store.id.desc()).first()
            should_send = should_send_whatsapp(
                last, user_returned_to_site=False, now=now, store=st
            )
            if should_send:
                send_whatsapp(phone="0500000000", message=message)
            return j(
                {
                    "ok": True,
                    "scenario": sc,
                    "message": message,
                    "should_send": should_send,
                }
            )
        db.create_all()
        _ensure_objection_track_test_columns()
        row = db.session.query(ObjectionTrack).order_by(
            ObjectionTrack.created_at.desc()
        ).first()
        if row is None:
            return j({"ok": False, "error": "no_objection"}, 404)
        t = (row.object_type or "").strip()
        if t not in ("price", "quality"):
            return j({"ok": False, "error": "unknown_type"}, 400)
        ct = (row.customer_type or "new").strip().lower()
        if ct not in ("new", "returning"):
            ct = "new"
        customer_type = ct
        cart = {
            "customer_name": row.customer_name
            or _WHATSAPP_TEST_CART.get("customer_name", ""),
            "cart_url": row.cart_url
            or _WHATSAPP_TEST_CART.get("cart_url", ""),
        }
        message = build_whatsapp_recovery_message(customer_type, t, cart)
        now = datetime.now(timezone.utc)
        last = row.last_activity_at
        if last is None:
            last = now - timedelta(minutes=3)
        st = db.session.query(Store).order_by(Store.id.desc()).first()
        should_send = should_send_whatsapp(
            last, user_returned_to_site=False, now=now, store=st
        )
        send_result = None
        if should_send:
            send_result = send_whatsapp(
                phone=row.customer_phone or "0500000000", message=message
            )
        return j(
            {
                "ok": True,
                "should_send": should_send,
                "message": message,
                "send_result": send_result,
            }
        )
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


@app.get("/send-test-whatsapp")
def send_test_whatsapp_get():
    return j({"ok": True, "message": "test sent"})


@app.post("/send-test-whatsapp")
async def send_test_whatsapp_post(request: Request):
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = None
    if not isinstance(body, dict):
        return j({"ok": False, "error": "json_object_required"}, 400)
    phone = (body.get("phone") or "").strip()
    message = body.get("message")
    if not phone or message is None:
        return j({"ok": False, "error": "phone_and_message_required"}, 400)
    if not isinstance(message, str):
        message = str(message)
    return j(send_whatsapp(phone, message))


# تسمية مودل Claude (يمكن تغييره من البيئة)
DEFAULT_CLAUDE_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

ZID_OAUTH_BASE = (os.getenv("ZID_OAUTH_BASE") or "https://oauth.zid.sa").rstrip("/")
ZID_PROFILE_API = os.getenv("ZID_PROFILE_API_URL", "https://api.zid.sa/v1/managers/account/profile")

# --- دعم القراءة من الحقول العامة (يُستدعى قبل ‎extract_cart_url‎) ---


# (رؤوس ‎CSP / X-Frame-Options‎: الوسيط ‎set_embed_csp_middleware‎ في أعلى ‎main.py‎)


def _parse_zid_store_id_from_token(data: dict[str, Any]) -> Optional[str]:
    for key in ("zid_store_id", "store_id", "merchant_id"):
        v = data.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    store = data.get("store")
    if isinstance(store, dict) and store.get("id") is not None:
        return str(store["id"]).strip()
    user = data.get("user")
    if isinstance(user, dict) and user.get("store_id") is not None:
        return str(user["store_id"]).strip()
    return None


def _fetch_zid_store_id_from_profile(access_token: str) -> Optional[str]:
    auth_bearer = (os.getenv("ZID_API_AUTHORIZATION") or "").strip()
    h: dict[str, str] = {
        "X-MANAGER-TOKEN": access_token,
        "Accept": "application/json",
        "Accept-Language": "en",
    }
    if auth_bearer:
        h["Authorization"] = f"Bearer {auth_bearer}"
    try:
        r = requests.get(ZID_PROFILE_API, headers=h, timeout=20)
    except requests.RequestException:
        return None
    if r.status_code // 100 != 2:
        return None
    j = r.json()
    if not isinstance(j, dict):
        return None
    for path in (
        ("data", "store", "id"),
        ("data", "store_id"),
        ("store", "id"),
        ("user", "store", "id"),
    ):
        cur: Any = j
        for p in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(p)
        if cur is not None and str(cur).strip():
            return str(cur).strip()
    return None


def save_or_update_store_from_token_response(data: dict[str, Any]) -> None:
    """يحفظ ‎access_token / refresh_token / انتهاء الصلاحية‎ دون تسجيل أسرار."""
    access = (data.get("access_token") or "").strip()
    if not access:
        return
    zid = _parse_zid_store_id_from_token(data) or _fetch_zid_store_id_from_profile(
        access
    )
    refresh: Optional[str] = None
    r = data.get("refresh_token")
    if r is not None and str(r).strip():
        refresh = str(r).strip()
    exp: Optional[datetime] = None
    ei = data.get("expires_in")
    if isinstance(ei, (int, float)):
        exp = datetime.now(timezone.utc) + timedelta(seconds=float(ei))

    if zid:
        row = db.session.query(Store).filter_by(zid_store_id=zid).first()
    else:
        row = (
            db.session.query(Store).filter(Store.zid_store_id.is_(None))  # type: ignore[union-attr]
            .order_by(Store.id.desc())
            .first()
        )
    if row is None:
        row = Store(
            zid_store_id=zid,
            access_token=access,
            refresh_token=refresh,
            token_expires_at=exp,
            is_active=True,
        )
        db.session.add(row)
    else:
        row.zid_store_id = zid or row.zid_store_id
        row.access_token = access
        if refresh is not None:
            row.refresh_token = refresh
        row.token_expires_at = exp
        row.is_active = True
    db.session.commit()


def _as_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return default


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v).strip()


# --- وصف عناصر السلة من ‎JSON‎ / Claude ---

def _line_items_to_summary(items: Any) -> str:
    # تجميع قائمة ‎line_items / items‎ إلى وصف نصي قصير
    if not isinstance(items, list) or not items:
        return ""
    parts: list[str] = []
    for it in items[:10]:
        if not isinstance(it, dict):
            parts.append(str(it)[:200])
            continue
        name = it.get("name") or it.get("title") or it.get("product_name") or "Item"
        qty = it.get("quantity") or it.get("qty") or 1
        parts.append(f"{name} (x{qty})")
    return ", ".join(parts)


def extract_cart_items_summary(payload: dict) -> str:
    # استخراج وصف عناصر السلة من هيكل ويبهوك زد (مستوٍ أو ‎data / cart‎)
    p = payload if isinstance(payload, dict) else {}
    data = p.get("data")
    if not isinstance(data, dict):
        data = p
    cart = data.get("cart") if isinstance(data.get("cart"), dict) else {}
    for key in ("line_items", "items", "products", "order_items"):
        s = _line_items_to_summary(data.get(key) or p.get(key))
        if s:
            return s
    s2 = _line_items_to_summary(cart.get("items") or cart.get("line_items"))
    if s2:
        return s2
    return "items in their cart"


def extract_cart_url(payload: dict) -> str:
    # رابط إعادة الاستكمال: من ‎Zid / الويبهوك‎
    p = payload if isinstance(payload, dict) else {}
    data = p.get("data")
    if not isinstance(data, dict):
        data = p
    cart = data.get("cart") if isinstance(data.get("cart"), dict) else {}
    u = _as_str(
        data.get("cart_url")
        or data.get("checkout_url")
        or data.get("abandoned_cart_url")
        or data.get("recovery_url")
        or p.get("cart_url")
        or p.get("checkout_url")
        or p.get("recovery_url")
        or cart.get("checkout_url")
        or cart.get("url")
    )
    return (u or "").strip()


def format_whatsapp_recipient_id(phone: str) -> str:
    # رقم ‎E.164‎ بلا ‎+‎ (ما يتطلبه ‎Graph API‎)
    d = (phone or "").replace("+", "").replace(" ", "").replace("-", "")
    for ch in d:
        if ch.isdigit():
            continue
        return ""
    if len(d) < 8:
        return ""
    return d


# --- واتساب (Meta / ‎WhatsApp Business Cloud)‎: رسالة تفاعلية + زر رابط (إكمال الشراء) ---

WHATSAPP_CTA_BUTTON_LABEL = "إكمال الشراء"  # نص الزر — يتطلبه ‎CTA URL‎ (حد أقصى ~20 حرفاً)

DEFAULT_RECOVERY_SMS = (
    "تذكير: سلتك بانتظارك. تقدر تكمل طلبك بلمسة من الزر أدناه."
)


def send_whatsapp_message(
    customer_phone: str, message_text: str, cart_url: str
) -> Tuple[bool, Optional[str], Any]:
    # إرسال رسالة ‎interactive / cta_url‎ عبر ‎requests.post‎ (جلسة مفتوحة: محتوى حر + زر)
    # يتطلب ‎token‎ و‎phone_number_id‎ من لوحة ‎Meta‎
    token = (os.getenv("WHATSAPP_API_TOKEN") or "").strip()
    phone_id = (os.getenv("WHATSAPP_PHONE_ID") or "").strip()
    base = (os.getenv("WHATSAPP_API_URL") or "https://graph.facebook.com/v17.0/").rstrip("/")
    if not token or token == "your_token":
        return False, "whatsapp_not_configured", None
    if not phone_id or phone_id == "your_id":
        return False, "whatsapp_not_configured", None

    to = format_whatsapp_recipient_id(customer_phone)
    if not to:
        return False, "invalid_phone", None

    fallback = (os.getenv("WHATSAPP_FALLBACK_CART_URL") or "https://example.com/cart").strip()
    target_url = (cart_url or "").strip() or fallback
    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        return False, "invalid_cart_url", None

    body_text = (message_text or "").strip() or DEFAULT_RECOVERY_SMS
    if len(body_text) > 1000:
        body_text = body_text[:997] + "..."

    # تنسيق ‎WhatsApp ‎CTA URL‎: زر "إكمال الشراء" يفتح ‎cart_url‎
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "body": {"text": body_text},
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": WHATSAPP_CTA_BUTTON_LABEL[:20],
                    "url": target_url,
                },
            },
        },
    }
    url = f"{base}/{phone_id}/messages"
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
    except requests.RequestException as e:
        return False, f"http_error: {e}", None

    try:
        rj: Any = resp.json()
    except Exception:  # noqa: BLE001
        rj = {"raw": resp.text}
    if resp.status_code // 100 == 2:
        return True, None, rj
    print("[WhatsApp API Error]", resp.status_code, rj)
    return False, f"api_error_{resp.status_code}", rj


# --- مولد رسالة الاسترجاع (Anthropic / Claude) ---

def generate_recovery_message(customer_name: str, cart_items: str, cart_value: float) -> str:
    # طلب نصي قصير لـ ‎Claude‎ حسب البرومبت المطلوب — بدون مفتاح نُرجع نصاً فارغاً
    key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key or key == "your_key_here":
        return ""

    name = (customer_name or "customer").strip() or "customer"
    items_desc = (cart_items or "items in their cart").strip() or "items in their cart"
    value_str = f"{float(cart_value or 0):.2f}"
    user_prompt = (
        f"You are a friendly Saudi marketing expert. Write a short, persuasive WhatsApp message for {name} "
        f"who left {items_desc} worth {value_str} SAR in their cart. "
        "Use a friendly Saudi dialect. Do NOT include a greeting like 'Hi', just the body of the message. "
        "Suggest they complete their order."
    )
    # عميل ‎Messages API‎
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=DEFAULT_CLAUDE_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": user_prompt}],
        )
        for block in msg.content:
            if getattr(block, "type", None) == "text" and hasattr(block, "text"):
                return (block.text or "").strip()
        if msg.content and hasattr(msg.content[0], "text"):
            return (getattr(msg.content[0], "text", None) or "").strip()
    except Exception:  # noqa: BLE001 — ويبهوك يبقى ناجحاً ويتم تسجيل الخطأ
        print("[Claude] generate_recovery_message error:\n" + traceback.format_exc())
    return ""


def normalize_zid_cart_fields(payload: dict) -> dict[str, Any]:
    # توحيد الحقول من ‎JSON‎ ويبهوك زد (مستوٍ، أو ‎data‎، أو ‎cart / customer‎ متداخِل)
    p = payload if isinstance(payload, dict) else {}
    data = p.get("data")
    if not isinstance(data, dict):
        data = p
    cart = data.get("cart") if isinstance(data.get("cart"), dict) else {}
    customer = data.get("customer") if isinstance(data.get("customer"), dict) else {}

    cart_id = _as_str(
        p.get("cart_id")
        or p.get("id")
        or data.get("cart_id")
        or data.get("id")
        or cart.get("id")
    )
    if not cart_id and data.get("abandoned_cart_id") is not None:
        cart_id = _as_str(data.get("abandoned_cart_id"))

    customer_name = _as_str(
        data.get("customer_name")
        or data.get("name")
        or p.get("customer_name")
        or customer.get("name")
        or customer.get("first_name")
    )
    if not customer_name and customer.get("last_name"):
        customer_name = f"{_as_str(customer.get('first_name'))} {_as_str(customer.get('last_name'))}".strip()

    customer_phone = _as_str(
        data.get("phone")
        or data.get("mobile")
        or p.get("customer_phone")
        or p.get("phone")
        or customer.get("phone")
        or customer.get("mobile")
    )

    cart_value = _as_float(
        data.get("total")
        or data.get("total_price")
        or data.get("subtotal")
        or data.get("amount")
        or p.get("cart_value")
        or p.get("total")
        or cart.get("total")
    )

    is_rec = data.get("is_recovered")
    st_raw = _as_str(p.get("status") or data.get("status")).lower()
    if isinstance(is_rec, bool) and is_rec:
        status = "recovered"
    elif st_raw in ("recovered", "completed", "paid", "success"):
        status = "recovered"
    elif st_raw in ("sent", "message_sent", "delivered"):
        status = "sent"
    else:
        status = "detected"

    cart_url = extract_cart_url(payload)

    return {
        "zid_cart_id": cart_id,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "cart_value": cart_value,
        "status": status,
        "cart_url": cart_url,
    }


def upsert_abandoned_cart_from_payload(payload: dict) -> Tuple[bool, str, Optional[AbandonedCart]]:
    # إدراج أو تحديث ‎AbandonedCart‎ حسب ‎zid_cart_id‎
    fields = normalize_zid_cart_fields(payload)
    if not fields["zid_cart_id"]:
        return False, "missing zid_cart_id", None
    row = db.session.query(AbandonedCart).filter_by(zid_cart_id=fields["zid_cart_id"]).first()
    if row is None:
        row = AbandonedCart(
            zid_cart_id=fields["zid_cart_id"],
            customer_name=fields["customer_name"],
            customer_phone=fields["customer_phone"],
            cart_value=fields["cart_value"],
            status=fields["status"],
            cart_url=fields.get("cart_url") or None,
        )
        AbandonedCart.set_raw(row, payload)
        db.session.add(row)
    else:
        row.customer_name = fields["customer_name"] or row.customer_name
        row.customer_phone = fields["customer_phone"] or row.customer_phone
        if fields["cart_value"] != 0.0 or row.cart_value is None or row.cart_value == 0.0:
            row.cart_value = fields["cart_value"]
        if fields.get("cart_url"):
            row.cart_url = fields["cart_url"]
        AbandonedCart.set_raw(row, payload)
        new = fields["status"]
        if new == "recovered":
            row.status = "recovered"
            row.recovered_at = datetime.now(timezone.utc)
        elif new == "sent":
            row.status = "sent"
        else:
            if row.status not in ("sent", "recovered"):
                row.status = new
    db.session.commit()
    return True, "ok", row


def _ensure_db_schema() -> None:
    # معطّل عمداً: لا ‎db.create_all()‎ ولا ترقية مخطط عند الإقلاع — حتى يعمل التطبيق بدون اتصال بقاعدة البيانات.
    # عند الحاجة، نفّذ إنشاء الجداول عبر سكربت ترحيل/يدوي، أو أعد تفعيل الكود أدناه داخل بيئة فيها ‎DB‎:
    #   db.create_all()
    #   insp = inspect(db.engine)
    #   ...
    return


# --- ويبهوك: إخفاء أسرار داخل ‎JSON‎ للتخزين الآمن ---

def _redact_secrets_for_log(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            kl = (k or "").lower()
            if any(
                x in kl
                for x in ("token", "secret", "password", "authorization", "bearer", "api_key")
            ):
                out[k] = "***"
            else:
                out[k] = _redact_secrets_for_log(v)
        return out
    if isinstance(obj, list):
        return [_redact_secrets_for_log(x) for x in obj[:80]]
    return obj


# --- المسارات ---

@app.get("/auth/callback")
def auth_callback(request: Request):
    # ‎OAuth 2.0‎: بدون ‎code‎ — تأكيد المسار؛ مع ‎code‎ — تبادل واستبدال الرموز دون إرجاع ‎access_token‎ للعميل
    code = (request.query_params.get("code") or "").strip()
    if not code:
        return j({"status": "callback route exists"})
    body, status = exchange_code_for_token(code)
    if 200 <= status < 300 and isinstance(body, dict) and (body.get("access_token") or "").strip():
        try:
            save_or_update_store_from_token_response(body)
        except SQLAlchemyError:
            db.session.rollback()
            return j({"ok": False, "error": "failed_to_persist_store"}, 500)
        return j({"ok": True, "message": "connected"}, 200)
    if 200 <= status < 300 and isinstance(body, dict):
        return j({"ok": False, "error": "no_access_token_in_response"}, status)
    if isinstance(body, dict):
        return j(body, status)
    return j({"error": "invalid_token_response_format"}, status)


_REASON_LABELS_AR: dict[str, str] = {
    "price": "السعر",
    "warranty": "الضمان",
    "shipping": "الشحن",
    "thinking": "التفكير",
    "quality": "الجودة",
    "other": "سبب آخر",
    "human_support": "دعم بشري",
}


def _format_reason_ts(dt: Optional[datetime]) -> str:
    if dt is None:
        return "—"
    d = dt
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.strftime("%Y-%m-%d %H:%M")


@app.get("/dashboard")
def dashboard(request: Request):
    """
    لوحة V1: أداء مالي (سلات مسترجعة) + أسباب تردد من ‎CartRecoveryReason‎ + بث مباشر.
    """
    use_mock = False
    total_carts = 0
    total_revenue = 0.0
    recovered = 0
    conversion_pct = 0.0
    reason_counts: dict[str, int] = {
        "price": 0,
        "warranty": 0,
        "shipping": 0,
        "thinking": 0,
    }
    live_rows: list[dict[str, Any]] = []
    try:
        db.create_all()
        total_carts = int(db.session.query(AbandonedCart).count() or 0)
        rev = (
            db.session.query(func.coalesce(func.sum(AbandonedCart.cart_value), 0.0))
            .filter(AbandonedCart.status == "recovered")
            .scalar()
        )
        total_revenue = float(rev) if rev is not None else 0.0
        recovered = int(
            db.session.query(AbandonedCart)
            .filter_by(status="recovered")
            .count()
        )
        if total_carts > 0:
            conversion_pct = round(100.0 * float(recovered) / float(total_carts), 1)
    except (SQLAlchemyError, OSError) as e:
        log.warning("dashboard: db read failed, using mock: %s", e)
        db.session.rollback()
        use_mock = True
    if not use_mock:
        try:
            # أسباب التردد — آخر اختيار لكل جلسة في ‎cart_recovery_reasons‎
            groups = (
                db.session.query(
                    CartRecoveryReason.reason,
                    func.count(CartRecoveryReason.id).label("c"),
                )
                .group_by(CartRecoveryReason.reason)
                .all()
            )
            for rkey, c in groups:
                k = (rkey or "").strip().lower()
                if k in reason_counts:
                    reason_counts[k] = int(c)
            q_live = (
                db.session.query(CartRecoveryReason)
                .order_by(CartRecoveryReason.updated_at.desc())
                .limit(12)
            )
            for r in q_live:
                k = (r.reason or "").strip().lower()
                label = _REASON_LABELS_AR.get(
                    k, (r.reason or "—")
                )
                product_hint = (r.custom_text or "").strip() or "—"
                if len(product_hint) > 48:
                    product_hint = product_hint[:45] + "…"
                live_rows.append(
                    {
                        "session_id": (r.session_id or "")[:32]
                        + ("…" if r.session_id and len(r.session_id) > 32 else ""),
                        "reason_key": k,
                        "reason_ar": label,
                        "product": product_hint,
                        "time_str": _format_reason_ts(r.updated_at),
                    }
                )
            crr_total = int(
                db.session.query(func.count(CartRecoveryReason.id)).scalar() or 0
            )
            if total_carts == 0 and crr_total == 0:
                use_mock = True
        except (SQLAlchemyError, OSError) as e2:
            log.warning("dashboard: crr read failed, using mock: %s", e2)
            db.session.rollback()
            use_mock = True
    if use_mock:
        total_carts = 48
        total_revenue = 12450.0
        recovered = 23
        conversion_pct = 47.9
        reason_counts = {
            "price": 12,
            "warranty": 5,
            "shipping": 3,
            "thinking": 7,
        }
        live_rows = [
            {
                "session_id": "dem…sess_01",
                "reason_key": "price",
                "reason_ar": "السعر",
                "product": "سماعة",
                "time_str": "2026-04-20 14:32",
            },
            {
                "session_id": "dem…sess_02",
                "reason_key": "warranty",
                "reason_ar": "الضمان",
                "product": "—",
                "time_str": "2026-04-20 13:10",
            },
            {
                "session_id": "dem…sess_03",
                "reason_key": "shipping",
                "reason_ar": "الشحن",
                "product": "أريد التوصيل لجدة",
                "time_str": "2026-04-20 11:00",
            },
        ]
    reason_bar = []
    rmax = max(reason_counts.values()) if reason_counts else 1
    if rmax < 1:
        rmax = 1
    for k in ("price", "warranty", "shipping", "thinking"):
        cnt = int(reason_counts.get(k, 0))
        reason_bar.append(
            {
                "key": k,
                "label": _REASON_LABELS_AR.get(k, k),
                "count": cnt,
                "width_pct": min(100.0, round(100.0 * float(cnt) / float(rmax), 1)),
            }
        )
    return templates.TemplateResponse(
        request,
        "dashboard_v1.html",
        {
            "request": request,
            "using_mock": use_mock,
            "total_carts": total_carts,
            "total_revenue": total_revenue,
            "recovered_carts": recovered,
            "conversion_pct": conversion_pct,
            "reason_bar": reason_bar,
            "live_feed": live_rows,
        },
    )


@app.get("/dashboard/recovery-settings")
def dashboard_recovery_settings(request: Request):
    """صفحة بسيطة لضبط ‎recovery_*‎ — تحمّل/تحفظ عبر ‎/api/recovery-settings‎."""
    # ‎Starlette:‎ المعامل الأول ‎Request‎ ثم اسم القالب (لا ‎(name, dict)‎ القديم).
    return templates.TemplateResponse(
        request,
        "recovery_settings.html",
        {
            "request": request,
        },
    )


@app.post("/api/carts/<int:row_id>/send")
def send_cart_manual(row_id: int):
    # إعادة إرسال يدوي للتجريب: نفس ‎send_whatsapp_message‎ ثم ‎Sent‎
    row = db.session.get(AbandonedCart, row_id)
    if row is None:
        return j({"ok": False, "error": "not_found"}, 404)
    if row.status == "recovered":
        return j({"ok": False, "error": "already_recovered"}, 400)
    cart_link = (row.cart_url or os.getenv("WHATSAPP_FALLBACK_CART_URL") or "https://example.com/cart").strip()
    msg = DEFAULT_RECOVERY_SMS
    ok, err, _r = send_whatsapp_message(row.customer_phone, msg, cart_link)
    if ok:
        if row.status != "recovered":
            row.status = "sent"
        db.session.commit()
    return j({"ok": ok, "error": err})


@app.post("/webhook/zid")
async def zid_webhook(request: Request):
    raw = await request.body()
    if not verify_webhook_signature(request, raw_body=raw):
        return j({"error": "unauthorized"}, 401)
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    log.info("zid_webhook received, top_keys=%s", list(payload.keys())[:32])
    out: dict[str, Any] = {"ok": True}
    try:
        rj = _redact_secrets_for_log(payload)
        pl: Optional[str] = None
        if rj is not None:
            pl = (json.dumps(rj, ensure_ascii=False))[:8000]
        ev = RecoveryEvent(
            store_id=None,
            abandoned_cart_id=None,
            event_type=(_as_str(payload.get("event") or "zid.webhook"))[:128] or "zid.webhook",
            payload=pl,
        )
        db.session.add(ev)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        log.warning("zid_webhook: could not log recovery event: %s", e)
    try:
        ok, err, _row = upsert_abandoned_cart_from_payload(payload)
        if not ok and err:
            out["cart_note"] = err
    except SQLAlchemyError:
        db.session.rollback()
        log.warning("zid_webhook: cart upsert failed", exc_info=True)
    return j(out, 200)


@app.get("/demo/cart")
@app.get("/demo/store")
@app.get("/demo/store/cart")
def demo_store(request: Request):
    """متجر وهمي للتجارب الداخلية (ويدجت / أحداث سلة — بدون منصات حقيقية)."""
    p = (request.url.path or "").rstrip("/") or "/"
    if p == "/demo/cart" or p.endswith("/store/cart"):
        title = "CartFlow — سلة (تجربة)"
        h1 = "واجهة سلة + استرجاع (تجربة داخلية)"
    else:
        title = "CartFlow — متجر تجريبي"
        h1 = "متجر وهمي — جاهز لعرض CartFlow"
    return templates.TemplateResponse(
        request,
        "demo_store.html",
        {
            "request": request,
            "demo_page_title": title,
            "demo_h1": h1,
        },
    )


@app.get("/demo/store2")
@app.get("/demo/store2/cart")
def demo_store2(request: Request):
    """نفس صفحة المتجر التجريبي مع ‎store_slug=demo2‎ لاختبار عزل الاسترجاع."""
    return templates.TemplateResponse(
        request,
        "demo_store.html",
        {
            "request": request,
            "demo_store_slug": "demo2",
            "demo_cart_key": "demo2_cart",
            "demo_page_title": "Demo store 2",
            "demo_h1": "Demo store 2 (isolation test)",
            "demo_data_store": "demo2",
        },
    )


@app.get("/dev/recovery-logs/{store_slug}")
def dev_recovery_logs(store_slug: str) -> Any:
    """آخر ‎20‎ سجل استرجاع لجلسة حسب ‎store_slug‎ (تجارب فقط، ‎ENV=development‎)."""
    try:
        db.create_all()
        slug = (store_slug or "").strip()
        rows = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.store_slug == slug)
            .order_by(CartRecoveryLog.created_at.desc())
            .limit(20)
            .all()
        )

        def _iso(dt: Optional[datetime]) -> Optional[str]:
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc).isoformat()
            return dt.isoformat()

        return j(
            {
                "ok": True,
                "store_slug": slug,
                "logs": [
                    {
                        "id": r.id,
                        "store_slug": r.store_slug,
                        "session_id": r.session_id,
                        "cart_id": r.cart_id,
                        "phone": r.phone,
                        "message": r.message,
                        "status": r.status,
                        "step": r.step,
                        "created_at": _iso(r.created_at),
                        "sent_at": _iso(r.sent_at),
                    }
                    for r in rows
                ],
            }
        )
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


@app.get("/")
def home(request: Request):
    # صفحة HTML للمراجعين/لوحة زد (بدون قاعدة بيانات)
    return templates.TemplateResponse("landing.html", {"request": request})


# لا نستدعي ‎_ensure_db_schema()‎ عند التحميل — يتجنب الاتصال بقاعدة البيانات عند الإقلاع (أي ‎ASGI server‎)

if __name__ == "__main__":
    import uvicorn

    _port = os.getenv("PORT") or os.getenv("FLASK_PORT", "5000")
    uvicorn.run(
        "main:app",
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(_port),
        reload=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
