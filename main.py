# -*- coding: utf-8 -*-
"""
CartFlow — تطبيق FastAPI الرئيسي لاستقبال الويبهوك ولوحة التاجر.
"""
import json
import logging
import os
import tempfile
import traceback
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import anthropic
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from extensions import db, init_database, remove_scoped_session
from integrations.zid_client import exchange_code_for_token, verify_webhook_signature
from json_response import UTF8JSONResponse, j
from sqlalchemy import func, inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

load_dotenv()

import models  # noqa: F401, E402
init_database()

# ASGI مُعطى ‎uvicorn / Railway‎: ‎uvicorn main:app --host 0.0.0.0 --port $PORT‎
app = FastAPI(
    default_response_class=UTF8JSONResponse,
    title="CartFlow",
)
app.state.secret_key = os.getenv("SECRET_KEY", "dev-only-change-in-production")
_ROOT = os.path.dirname(os.path.abspath(__file__))
# مسار مُطلَق: يعمل حتى اختلاف ‎working directory‎ على ‎Railway / Docker‎
templates = Jinja2Templates(directory=os.path.join(_ROOT, "templates"))
_static = os.path.join(_ROOT, "static")
if os.path.isdir(_static):
    app.mount("/static", StaticFiles(directory=_static), name="static")

from models import AbandonedCart, ObjectionTrack, Store, RecoveryEvent  # noqa: E402
from routes.ops import router as ops_router  # noqa: E402

app.include_router(ops_router)

from services.ai_message_builder import build_abandoned_cart_message  # noqa: E402
from services.whatsapp_recovery import build_whatsapp_recovery_message  # noqa: E402
from services.whatsapp_send import send_whatsapp, should_send_whatsapp  # noqa: E402

log = logging.getLogger("cartflow")


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
    """يُنفَّذ أوّل مسار؛ ‎404‎ لـ ‎/dev‎ و ‎/dev/*‎ عندما ‎ENV‎ ليس ‎development‎."""
    p = request.url.path
    if p == "/dev" or p.startswith("/dev/"):
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
_VALID_RECOVERY_UNITS = frozenset({"minutes", "hours", "days"})


def _dev_apply_recovery_settings_update(
    recovery_delay: Any, recovery_delay_unit: Any, recovery_attempts: Any
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
    row = db.session.query(Store).order_by(Store.id.desc()).first()
    if row is None:
        return {"ok": False, "error": "no_store"}, 404
    row.recovery_delay = rd_i
    row.recovery_delay_unit = unit
    row.recovery_attempts = ra_i
    db.session.commit()
    return {
        "ok": True,
        "recovery_delay": row.recovery_delay,
        "recovery_delay_unit": row.recovery_delay_unit,
        "recovery_attempts": row.recovery_attempts,
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
        data, code = _dev_apply_recovery_settings_update(
            body.get("recovery_delay"),
            body.get("recovery_delay_unit"),
            body.get("recovery_attempts"),
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
        data, code = _dev_apply_recovery_settings_update(
            body.get("recovery_delay"),
            body.get("recovery_delay_unit"),
            body.get("recovery_attempts"),
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
        db.create_all()
        row = db.session.query(Store).order_by(Store.id.desc()).first()
        if row is None:
            return j({"ok": False, "error": "no_store"}, 404)
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


@app.post("/api/cart-event")
async def api_cart_event(request: Request):
    """
    أحداث سلة من الواجهة (مثل ‎cart_abandoned‎) — للتتبع والتجارب فقط. بدون واتساب.
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
    if payload.get("event") == "cart_abandoned":
        log.info("cart abandoned received")
        recovery_message = "يبدو أنك نسيت سلتك 🛒 هل تحب أكمل لك الطلب؟"
        out["recovery_message"] = recovery_message
        log.info("recovery message created")
    return j(out, 200)


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


@app.get("/dashboard")
def dashboard(request: Request):
    # تجميع إحصائيات + آخر 5 سلات (حسب ‎created_at‎ تنازلياً)
    total_carts = db.session.query(AbandonedCart).count()
    rev = (
        db.session.query(func.coalesce(func.sum(AbandonedCart.cart_value), 0.0))
        .filter(AbandonedCart.status == "recovered")
        .scalar()
    )
    total_revenue = float(rev) if rev is not None else 0.0
    recovered = (
        db.session.query(AbandonedCart)
        .filter_by(status="recovered")
        .count()
    )
    recent_carts = (
        db.session.query(AbandonedCart)
        .order_by(AbandonedCart.last_seen_at.desc())
        .limit(5)
        .all()
    )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "total_carts": total_carts,
            "total_revenue": total_revenue,
            "recovered_carts": recovered,
            "recent_carts": recent_carts,
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


@app.get("/demo/store")
@app.get("/demo/store/cart")
def demo_store(request: Request):
    """متجر وهمي للتجارب الداخلية (ويدجت / أحداث سلة — بدون منصات حقيقية)."""
    return templates.TemplateResponse(
        request,
        "demo_store.html",
        {"request": request},
    )


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
