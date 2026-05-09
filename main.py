# -*- coding: utf-8 -*-
"""
CartFlow — تطبيق FastAPI الرئيسي لاستقبال الويبهوك ولوحة التاجر.
"""
import asyncio
import base64
import hashlib
import json
import logging
import os
import tempfile
import threading
import time
import uuid
import traceback
from collections import defaultdict
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import anthropic
import requests
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Body, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from starlette.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.trustedhost import TrustedHostMiddleware

from extensions import db, init_database, remove_scoped_session
from integrations.zid_client import exchange_code_for_token, verify_webhook_signature
from json_response import UTF8JSONResponse, j
from sqlalchemy import func, inspect, or_, text
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

    try:
        from services.whatsapp_positive_reply import (
            process_inbound_whatsapp_for_positive_intent,
        )

        process_inbound_behavioral_recovery(message, from_number)
        process_inbound_whatsapp_for_positive_intent(message, from_number)
    except Exception as inbound_err:  # noqa: BLE001
        logging.getLogger("cartflow").warning(
            "whatsapp_webhook positive intent: %s",
            inbound_err,
            exc_info=True,
        )

    return PlainTextResponse("OK")


@app.post("/dev/whatsapp-decision-test")
def whatsapp_decision_test(payload: dict = Body(...)) -> dict[str, Any]:
    """تجربة قرار الواتساب + إرسال مباشر (يسجَّل أيضاً خارج ‎ENV=development‎ لمطابقة ‎/decision-check‎).

    لا يُستخدم لتقييم تأخير الاسترجاع: الإرسال هنا يتخطّى مسار السلة و‎should_send_whatsapp‎.
    لاختبار التأخير والجدولة استخدم فقط ‎POST /api/cart-event‎ مع ‎event=cart_abandoned‎ والسبب من مسار الويدجت.
    """
    from decision_engine import decide_recovery_action
    from services.whatsapp_send import send_whatsapp, WA_TRACE_DELAY_UNSPECIFIED

    phone = payload.get("phone")
    reason_tag = payload.get("reason_tag")

    result = decide_recovery_action(reason_tag)
    message = result["message"]

    send_result = send_whatsapp(
        phone,
        message,
        reason_tag=reason_tag,
        wa_trace_path=__file__,
        wa_trace_delay_passed=WA_TRACE_DELAY_UNSPECIFIED,
    )
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
    MerchantFollowupAction,
    MessageLog,
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
    WA_TRACE_DELAY_UNSPECIFIED,
    _max_recovery_attempts,
    _naive_utc,
    _recovery_config,
    _recovery_delay_minutes_from_store,
    emit_recovery_wa_send_trace,
    recovery_uses_real_whatsapp,
    send_whatsapp,
    should_send_whatsapp,
)
from schema_widget import ensure_store_widget_schema
from services.cartflow_whatsapp_mock import REASON_CHOICES as CF_REASON_CHOICES
from services.recovery_decision import get_primary_recovery_reason
from services.store_template_control import (
    apply_exit_intent_template_control_from_body,
    apply_template_control_from_body,
    exit_intent_template_fields_for_api,
    template_control_fields_for_api,
)
from services.store_widget_customization import (
    apply_widget_customization_from_body,
    widget_customization_fields_for_api,
)
from services.store_reason_templates import (
    apply_reason_templates_from_body,
    reason_templates_fields_for_api,
)
from services.store_trigger_templates import (
    apply_trigger_templates_from_body,
    trigger_templates_fields_for_api,
)
from services.reason_template_recovery import (
    canonical_reason_template_key,
    reason_template_blocks_recovery_whatsapp,
    resolve_recovery_whatsapp_message_with_reason_templates,
)
from services.recovery_conversation_tracker import conversation_dashboard_extras
from services.recovery_multi_message import multi_message_slots_for_abandon
from services.cartflow_widget_recovery_gate import (
    apply_cartflow_widget_recovery_gate_from_body,
    cartflow_widget_recovery_gate_fields_for_api,
)
from services.vip_cart import (
    apply_vip_cart_threshold_from_body,
    apply_vip_offer_settings_from_body,
    is_vip_cart,
    vip_cart_threshold_fields_for_api,
    vip_offer_card_hint_ar,
    vip_offer_fields_for_api,
    vip_offer_manual_contact_whatsapp_body,
)
from services.normal_recovery_phone_persist import (
    commit_normal_recovery_phone_after_resolved,
    log_normal_recovery_phone_line,
)
from services.cf_test_phone_override import (
    cf_test_customer_phone_override_allowed,
    normalize_cf_test_customer_phone,
)
from services.smart_actions import get_cart_smart_action, smart_action_cta_target  # noqa: E402
from services.vip_merchant_alert import (
    build_vip_merchant_alert_body,
    resolve_merchant_whatsapp_phone,
    resolve_merchant_whatsapp_phone_with_default_env,
    try_send_vip_merchant_whatsapp_alert,
    vip_dashboard_review_link,
)
from services.whatsapp_positive_reply import (
    REASON_CUSTOMER_REPLIED_YES,
    STATUS_MERCHANT_FOLLOWUP_COMPLETED,
    STATUS_NEEDS_MERCHANT_FOLLOWUP,
)
from services.behavioral_recovery.inbound_whatsapp import (
    process_inbound_behavioral_recovery,
)
from services.behavioral_recovery.link_tracking import (
    apply_outbound_tracking_to_message,
    handle_recovery_link_click,
)
from services.recovery_blocker_display import (
    get_recovery_blocker_display_state,
    recovery_blocker_from_latest_log_status,
)
from services.recovery_message_strategy import get_recovery_message
from services.recovery_template_defaults import guided_defaults_for_api
from services.behavioral_recovery.state_store import (
    behavioral_dict_for_abandoned_cart,
    customer_replied_flagged_for_session,
)
from services.behavioral_recovery.user_return import (
    payload_indicates_user_returned_to_site,
    record_behavioral_user_return_from_payload,
)

log = logging.getLogger("cartflow")


def _dev_delay_test_minutes_for_reason(reason_tag: str) -> int:
    """مهلات اختبار معزولة فقط — لا تؤثر على الإنتاج أو محرك القرار."""
    tag = (reason_tag or "").strip().lower()
    if tag == "shipping":
        return 2
    if tag == "price" or tag.startswith("price"):
        return 5
    return 2


_DEV_DELAY_TEST_MAX_RECOVERY_ATTEMPTS = 1
_dev_delay_test_send_count: dict[str, int] = {}


def _dev_delay_test_attempt_key(phone: str, reason_tag: str) -> str:
    return f"{phone}:{reason_tag}"


async def _run_dev_cartflow_delay_test_send(
    delay_seconds: float,
    phone: str,
    reason_tag: str,
    simulate_user_return: bool,
    simulate_purchase: bool,
) -> None:
    await asyncio.sleep(delay_seconds)
    try:
        decision = decide_recovery_action(reason_tag)
        message = decision["message"]
    except Exception:  # noqa: BLE001 — تجربة عزل فقط
        message = ""

    # مطابقة منطق منع الإزعاج قبل الإرسال — مسار تجربة فقط (لا recovery_key إنتاجي).
    user_returned_to_site = bool(simulate_user_return)
    purchase_completed = bool(simulate_purchase)
    should_send = not (user_returned_to_site or purchase_completed)
    session_id_log = "(dev-delay-test)"
    print("[ANTI SPAM CHECK]")
    print("session_id=", session_id_log)
    print("user_returned_to_site=", user_returned_to_site)
    print("purchase_completed=", purchase_completed)
    print("should_send=", should_send)
    if not should_send:
        if purchase_completed:
            print("[DEV DELAY TEST] anti-spam blocked send (simulate_purchase)")
        else:
            print("[DEV DELAY TEST] anti-spam blocked send (simulate_user_return)")
        return

    attempt_key = _dev_delay_test_attempt_key(phone, reason_tag)
    max_recovery_attempts = _DEV_DELAY_TEST_MAX_RECOVERY_ATTEMPTS
    with _recovery_session_lock:
        sent_count = _dev_delay_test_send_count.get(attempt_key, 0)
    allowed = sent_count < max_recovery_attempts
    print("[ATTEMPT CONTROL]")
    print("key=", attempt_key)
    print("sent_count=", sent_count)
    print("max_recovery_attempts=", max_recovery_attempts)
    print("allowed=", allowed)
    if not allowed:
        print("[ATTEMPT BLOCKED]")
        print("[DEV DELAY TEST] attempt control blocked send")
        return

    result = send_whatsapp(
        phone,
        message,
        reason_tag=reason_tag,
        wa_trace_path=__file__,
        wa_trace_delay_passed=WA_TRACE_DELAY_UNSPECIFIED,
    )
    success = isinstance(result, dict) and result.get("ok") is True
    if success:
        with _recovery_session_lock:
            _dev_delay_test_send_count[attempt_key] = sent_count + 1
    sent_at = datetime.now(timezone.utc)
    print("[DEV DELAY TEST SEND]")
    print("sent_at=", sent_at.isoformat())
    print("phone=", phone)
    print("result=", result)


@app.post("/dev/cartflow-delay-test")
async def dev_cartflow_delay_test(
    background_tasks: BackgroundTasks,
    payload: Dict[str, Any] = Body(...),
) -> Any:
    """
    تجربة تأخير معزولة: جدولة إرسال واتساب بعد دقائق حسب ‎reason_tag‎ — لا يمس مسار السلة/الودجت.
    مسموح في الإنتاج تحققاً من الجدولة (نفس استثناء الميدلوير لـ ‎/dev/cartflow-delay-test‎).
    جسم اختياري: ‎simulate_user_return: true‎ لمحاكاة رجوع المستخدم؛ ‎simulate_purchase: true‎ لمحاكاة إتمام الشراء — اختبار منع الإزعاج دون تفاعل حقيقي.
    """
    phone = (payload.get("phone") or "").strip()
    reason_tag = (payload.get("reason_tag") or "").strip()
    simulate_user_return = payload.get("simulate_user_return") is True
    simulate_purchase = payload.get("simulate_purchase") is True
    if not phone:
        return j({"ok": False, "error": "phone_required"}, 400)
    if not reason_tag:
        return j({"ok": False, "error": "reason_tag_required"}, 400)
    delay_minutes = _dev_delay_test_minutes_for_reason(reason_tag)
    delay_seconds = float(delay_minutes * 60)
    scheduled_at = datetime.now(timezone.utc)
    send_after = scheduled_at + timedelta(seconds=delay_seconds)
    print("[DEV DELAY TEST]")
    print("reason_tag=", reason_tag)
    print("delay_minutes=", delay_minutes)
    print("scheduled_at=", scheduled_at.isoformat())
    print("send_after=", send_after.isoformat())
    print("simulate_user_return=", simulate_user_return)
    print("simulate_purchase=", simulate_purchase)
    background_tasks.add_task(
        _run_dev_cartflow_delay_test_send,
        delay_seconds,
        phone,
        reason_tag,
        simulate_user_return,
        simulate_purchase,
    )
    return j(
        {
            "ok": True,
            "reason_tag": reason_tag,
            "delay_minutes": delay_minutes,
            "delay_seconds": delay_seconds,
            "scheduled_at": scheduled_at.isoformat(),
            "send_after": send_after.isoformat(),
            "simulate_user_return": simulate_user_return,
            "simulate_purchase": simulate_purchase,
        },
        200,
    )


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


@app.get("/api/recover/r")
def api_recover_redirect(t: str = Query(..., min_length=6, max_length=2048)):
    """تتبع نقرة رابط الاسترجاع — يحدّث الحالة ثم يحوّل لصفحة السلة (لا يُسجّل كتحويل تلقائياً)."""
    return handle_recovery_link_click(t)


@app.on_event("startup")
async def _startup_whatsapp_queue() -> None:
    await start_whatsapp_queue_worker()


def _is_development_mode() -> bool:
    """
    ‎/dev/‎ يعمل فقط عند ‎ENV=development‎ صراحةً. غير ذلك = إنتاج (ويمكن ترك ‎ENV‎
    غير مضبوط). محلياً: أضف ‎ENV=development‎ إلى ‎.env‎.
    """
    return (os.getenv("ENV") or "").strip().lower() == "development"


# مسارات ‎/dev‎ مسموحة في الإنتاج رغم ‎ENV‎ (تحقق يدوي / مراقبة؛ باقي ‎/dev‎ محظور).
_DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT = frozenset(
    {
        "/dev/whatsapp-decision-test",
        "/dev/cartflow-delay-test",
        "/dev/vip-flow-verify",
        "/dev/create-vip-test-cart",
    }
)


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
    """يُنفَّذ أوّل مسار؛ ‎404‎ لـ ‎/dev‎ و ‎/dev/*‎ عندما ‎ENV‎ ليس ‎development‎ (استثناءات: ‎whatsapp-decision-test‎، ‎cartflow-delay-test‎، ‎vip-flow-verify‎، ‎create-vip-test-cart‎)."""
    p = request.url.path
    if p == "/dev" or (
        p.startswith("/dev/") and p not in _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT
    ):
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
# ‎demo‎ / ‎default‎ / المتجر الآلي — نفس صف لوحة ‎GET/POST /api/recovery-settings‎ (آخر ‎stores.id‎)، لا صف قديم ‎zid=demo‎ بلا ‎vip_cart_threshold‎.
_WIDGET_STORE_SLUGS_USE_DASHBOARD_LATEST = frozenset(
    {"demo", "default", CARTFLOW_DEFAULT_RECOVERY_STORE_ZID.casefold()}
)
_VALID_RECOVERY_UNITS = frozenset({"minutes", "hours", "days"})

_STORE_RECOVERY_TEMPLATE_KEYS: tuple[str, ...] = (
    "template_price",
    "template_shipping",
    "template_quality",
    "template_delivery",
    "template_warranty",
    "template_other",
)
_MAX_STORE_TEMPLATE_CHARS = 65535


def _coerce_store_template_column_value(raw: Any) -> Optional[str]:
    """‎NULL‎ أو فارغ بعد ‎strip‎ = لا قالب مخصص (العرض يستخدم الافتراضي المدمج)."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    return s[:_MAX_STORE_TEMPLATE_CHARS]


def _apply_recovery_template_fields_from_body(row: Any, body: Dict[str, Any]) -> None:
    """يحدّث حقول القالب على سطر المتجر فقط للمفاتيح الظاهرة في ‎body‎."""
    for key in _STORE_RECOVERY_TEMPLATE_KEYS:
        if key not in body:
            continue
        setattr(row, key, _coerce_store_template_column_value(body.get(key)))


def _recovery_template_fields_for_api(row: Any) -> Dict[str, str]:
    """قيم للوحة والـ ‎API‎ — سلسلة فارغة عند ‎NULL‎ لعرض ‎textarea‎."""
    out: Dict[str, str] = {}
    for key in _STORE_RECOVERY_TEMPLATE_KEYS:
        v = getattr(row, key, None)
        out[key] = v.strip() if isinstance(v, str) and v.strip() else ""
    return out


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


def _dashboard_recovery_store_row() -> Optional[Store]:
    """آخر ‎Store‎ بحسب ‎id‎ — نفس الصف الذي تقرأه وتحدّثه ‎GET/POST /api/recovery-settings‎."""
    try:
        return db.session.query(Store).order_by(Store.id.desc()).first()
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return None


def _merge_recovery_settings_post_body(body: Dict[str, Any]) -> Dict[str, Any]:
    """دمج حقول الاسترجاع مع آخر ‎Store‎ حتى تعمل التحديثات الجزئية."""
    out = dict(body)
    try:
        row = _dashboard_recovery_store_row()
    except (SQLAlchemyError, OSError):
        row = None
    if row is not None:
        if "recovery_delay" not in body:
            out["recovery_delay"] = row.recovery_delay
        if "recovery_delay_unit" not in body:
            out["recovery_delay_unit"] = row.recovery_delay_unit
        if "recovery_attempts" not in body:
            out["recovery_attempts"] = row.recovery_attempts
        if "second_attempt_delay_minutes" not in body:
            out["second_attempt_delay_minutes"] = getattr(
                row, "second_attempt_delay_minutes", None
            )
        if "store_whatsapp_number" not in body:
            out["store_whatsapp_number"] = getattr(row, "store_whatsapp_number", None)
        if "vip_cart_threshold" not in body:
            out["vip_cart_threshold"] = getattr(row, "vip_cart_threshold", None)
        if "vip_offer_enabled" not in body:
            out["vip_offer_enabled"] = bool(getattr(row, "vip_offer_enabled", False))
        if "vip_offer_type" not in body:
            out["vip_offer_type"] = getattr(row, "vip_offer_type", None)
        if "vip_offer_value" not in body:
            out["vip_offer_value"] = getattr(row, "vip_offer_value", None)
        if "cartflow_widget_enabled" not in body:
            out["cartflow_widget_enabled"] = bool(
                getattr(row, "cartflow_widget_enabled", True)
            )
        if "cartflow_widget_delay_value" not in body:
            dv_def = getattr(row, "cartflow_widget_delay_value", 0)
            try:
                out["cartflow_widget_delay_value"] = max(0, int(dv_def))
            except (TypeError, ValueError):
                out["cartflow_widget_delay_value"] = 0
        if "cartflow_widget_delay_unit" not in body:
            du_raw = getattr(row, "cartflow_widget_delay_unit", None)
            du_o = (
                str(du_raw).strip().lower()
                if isinstance(du_raw, str) and du_raw.strip()
                else "minutes"
            )
            out["cartflow_widget_delay_unit"] = (
                du_o if du_o in ("minutes", "hours", "days") else "minutes"
            )
    return out


def _dev_apply_recovery_settings_update(
    recovery_delay: Any,
    recovery_delay_unit: Any,
    recovery_attempts: Any,
    *,
    whatsapp_support_url: Any = None,
    update_whatsapp: bool = False,
    store_whatsapp_number: Any = None,
    update_store_whatsapp: bool = False,
    request_body: Optional[Dict[str, Any]] = None,
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
    row = _dashboard_recovery_store_row()
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
    if update_store_whatsapp:
        if store_whatsapp_number is None or (
            isinstance(store_whatsapp_number, str)
            and not (store_whatsapp_number or "").strip()
        ):
            row.store_whatsapp_number = None
        else:
            row.store_whatsapp_number = str(store_whatsapp_number).strip()[:64]
    if request_body is not None:
        if "second_attempt_delay_minutes" in request_body:
            raw_2 = request_body.get("second_attempt_delay_minutes")
            if raw_2 is None or raw_2 == "":
                row.second_attempt_delay_minutes = None
            else:
                try:
                    v2 = int(raw_2)
                except (TypeError, ValueError):
                    pass
                else:
                    row.second_attempt_delay_minutes = (
                        None if v2 < 1 else max(5, min(v2, 10080))
                    )
        _apply_recovery_template_fields_from_body(row, request_body)
        apply_trigger_templates_from_body(row, request_body)
        apply_reason_templates_from_body(row, request_body)
        apply_template_control_from_body(row, request_body)
        apply_exit_intent_template_control_from_body(row, request_body)
        apply_widget_customization_from_body(row, request_body)
        apply_vip_cart_threshold_from_body(row, request_body)
        apply_vip_offer_settings_from_body(row, request_body)
        apply_cartflow_widget_recovery_gate_from_body(row, request_body)
    db.session.commit()
    wa: Optional[str] = getattr(row, "whatsapp_support_url", None)
    if not (isinstance(wa, str) and wa.strip()):
        wa = None
    sw: Optional[str] = getattr(row, "store_whatsapp_number", None)
    if not (isinstance(sw, str) and sw.strip()):
        sw = None
    payload: Dict[str, Any] = {
        "ok": True,
        "recovery_delay": row.recovery_delay,
        "recovery_delay_unit": row.recovery_delay_unit,
        "recovery_attempts": row.recovery_attempts,
        "second_attempt_delay_minutes": getattr(
            row, "second_attempt_delay_minutes", None
        ),
        "whatsapp_support_url": wa,
        "store_whatsapp_number": sw,
    }
    payload.update(_recovery_template_fields_for_api(row))
    payload.update(trigger_templates_fields_for_api(row))
    payload.update(reason_templates_fields_for_api(row))
    payload.update(template_control_fields_for_api(row))
    payload.update(exit_intent_template_fields_for_api(row))
    payload.update(widget_customization_fields_for_api(row))
    payload.update(vip_cart_threshold_fields_for_api(row))
    payload.update(vip_offer_fields_for_api(row))
    payload.update(cartflow_widget_recovery_gate_fields_for_api(row))
    payload["guided_recovery_defaults"] = guided_defaults_for_api()
    return payload, 200

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


@app.get("/dev/store-delay")
def dev_store_delay():
    """قراءة ‎recovery_delay_minutes‎ من آخر ‎Store‎؛ ‎ENV=development‎ فقط."""
    if not _is_development_mode():
        return Response(status_code=404)
    row = db.session.query(Store).order_by(Store.id.desc()).first()
    if row is None:
        return {"delay": 2}
    raw = getattr(row, "recovery_delay_minutes", None)
    if raw is None:
        return {"delay": 2}
    try:
        v = max(0, int(raw))
    except (TypeError, ValueError):
        return {"delay": 2}
    eff = v if v > 0 else 2
    return {"delay": eff}


@app.get("/dev/normal-recovery-debug")
def dev_normal_recovery_debug(session_id: str = Query(...)) -> Any:
    """قراءة تشخيصية لمسار المحاولة الثانية — ‎ENV=development‎ فقط."""
    if not _is_development_mode():
        return Response(status_code=404)
    return j(_normal_recovery_debug_for_session(session_id))


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
        body = _merge_recovery_settings_post_body(body)
        uw = "whatsapp_support_url" in body
        us = "store_whatsapp_number" in body
        data, code = _dev_apply_recovery_settings_update(
            body.get("recovery_delay"),
            body.get("recovery_delay_unit"),
            body.get("recovery_attempts"),
            whatsapp_support_url=body.get("whatsapp_support_url") if uw else None,
            update_whatsapp=uw,
            store_whatsapp_number=body.get("store_whatsapp_number") if us else None,
            update_store_whatsapp=us,
            request_body=body,
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
        body = _merge_recovery_settings_post_body(body)
        uw = "whatsapp_support_url" in body
        us = "store_whatsapp_number" in body
        data, code = _dev_apply_recovery_settings_update(
            body.get("recovery_delay"),
            body.get("recovery_delay_unit"),
            body.get("recovery_attempts"),
            whatsapp_support_url=body.get("whatsapp_support_url") if uw else None,
            update_whatsapp=uw,
            store_whatsapp_number=body.get("store_whatsapp_number") if us else None,
            update_store_whatsapp=us,
            request_body=body,
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
        row = _dashboard_recovery_store_row()
        if row is None:
            return j({"ok": False, "error": "no_store"}, 500)
        wa: Optional[str] = getattr(row, "whatsapp_support_url", None)
        if not (isinstance(wa, str) and wa.strip()):
            wa = None
        sw: Optional[str] = getattr(row, "store_whatsapp_number", None)
        if not (isinstance(sw, str) and sw.strip()):
            sw = None
        payload = {
            "ok": True,
            "recovery_delay": row.recovery_delay,
            "recovery_delay_unit": row.recovery_delay_unit,
            "recovery_attempts": row.recovery_attempts,
            "second_attempt_delay_minutes": getattr(
                row, "second_attempt_delay_minutes", None
            ),
            "whatsapp_support_url": wa,
            "store_whatsapp_number": sw,
        }
        payload.update(_recovery_template_fields_for_api(row))
        payload.update(trigger_templates_fields_for_api(row))
        payload.update(reason_templates_fields_for_api(row))
        payload.update(template_control_fields_for_api(row))
        payload.update(exit_intent_template_fields_for_api(row))
        payload.update(widget_customization_fields_for_api(row))
        payload.update(vip_cart_threshold_fields_for_api(row))
        payload.update(vip_offer_fields_for_api(row))
        payload.update(cartflow_widget_recovery_gate_fields_for_api(row))
        payload["guided_recovery_defaults"] = guided_defaults_for_api()
        return j(payload)
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


# جلسة واحدة = تسلسل استرجاع + ‎sent‎ عند اكتمال الخطوات (لكل عملية ‎worker‎)
_session_recovery_started: dict[str, bool] = {}
_session_recovery_logged: dict[str, bool] = {}
_session_recovery_seq_logged: dict[str, bool] = {}
_session_recovery_followup_next_due_at: dict[str, str] = {}
_session_recovery_last_second_skip_reason: dict[str, str] = {}
_session_recovery_sent: dict[str, bool] = {}
_session_recovery_converted: dict[str, bool] = {}
_session_recovery_returned: dict[str, bool] = {}
_session_recovery_send_count: dict[str, int] = {}
_session_recovery_multi_logged: dict[str, bool] = {}
_session_recovery_multi_attempt_cap: dict[str, int] = {}
_session_recovery_multi_verified_indexes: dict[str, set[int]] = {}
_MAX_RECOVERY_ATTEMPTS = 1
_RECOVERY_REASON_POLL_INTERVAL_SEC = 0.15
_RECOVERY_REASON_POLL_MAX_ATTEMPTS = 67
_recovery_session_lock = threading.RLock()

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
    for key in ("store", "store_slug"):
        raw = payload.get(key)
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


def _ensure_cart_abandon_payload_has_cart_id(
    payload: dict[str, Any], recovery_key: str
) -> dict[str, Any]:
    """يملأ ‎cart_id‎ اصطناعياً عند الغياب حتى يُنشأ ‎AbandonedCart‎ ويُفعّل ‎VIP‎."""
    if _cart_id_str_from_payload(payload):
        return payload
    rk = (recovery_key or "").strip()
    if not rk:
        return payload
    h = hashlib.sha256(rk.encode("utf-8")).hexdigest()[:24]
    out = dict(payload)
    out["cart_id"] = f"cf_w_{h}"[:255]
    return out


def _synthetic_zid_cart_id_from_recovery_key(recovery_key: str) -> str:
    """نفس ‎cart_id‎ الاصطناعي ‎cf_w_*‎ المستخدم في ‎_ensure_cart_abandon_payload_has_cart_id‎."""
    rk = (recovery_key or "").strip()
    if not rk:
        return ""
    h = hashlib.sha256(rk.encode("utf-8")).hexdigest()[:24]
    return f"cf_w_{h}"[:255]


def _collect_abandoned_cart_rows_for_merge(
    *,
    cart_ids: list[str],
    session_id: Optional[str],
    recovery_key: str,
    store_row: Optional[Store],
) -> list[AbandonedCart]:
    """كل صفوف ‎AbandonedCart‎ المرشّحة لدمجها: ‎zid_cart_id‎، ‎recovery_session_id‎، ‎cf_w_*‎ من ‎recovery_key‎."""
    seen: set[int] = set()
    out: list[AbandonedCart] = []

    def take(r: Optional[AbandonedCart]) -> None:
        if r is None:
            return
        rid = int(r.id)
        if rid in seen:
            return
        seen.add(rid)
        out.append(r)

    for cid in cart_ids:
        cid_n = (cid or "").strip()[:255]
        if not cid_n:
            continue
        take(db.session.query(AbandonedCart).filter_by(zid_cart_id=cid_n).first())

    sid_n = (session_id or "").strip()[:512] if session_id else ""
    if sid_n:
        q = db.session.query(AbandonedCart).filter(AbandonedCart.recovery_session_id == sid_n)
        if store_row is not None and getattr(store_row, "id", None) is not None:
            sid_val = int(store_row.id)
            q = q.filter(
                (AbandonedCart.store_id == sid_val) | (AbandonedCart.store_id.is_(None))  # type: ignore[union-attr]
            )
        for r in q.all():
            take(r)

    syn = _synthetic_zid_cart_id_from_recovery_key(recovery_key)
    if syn:
        take(db.session.query(AbandonedCart).filter_by(zid_cart_id=syn).first())

    return out


def _pick_canonical_abandoned_cart_row(candidates: list[AbandonedCart]) -> Optional[AbandonedCart]:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    def sort_key(r: AbandonedCart) -> tuple:
        zid = (r.zid_cart_id or "").strip()
        is_syn = zid.startswith("cf_w_")
        ts = r.last_seen_at
        if ts is None:
            tsf = 0.0
        elif ts.tzinfo is None:
            tsf = ts.replace(tzinfo=timezone.utc).timestamp()
        else:
            tsf = ts.timestamp()
        return (0 if not is_syn else 1, -tsf, -int(r.id))

    return sorted(candidates, key=sort_key)[0]


def _delete_noncanonical_abandoned_merge_rows(
    *,
    keep: AbandonedCart,
    candidates: list[AbandonedCart],
) -> int:
    n = 0
    for c in candidates:
        if int(c.id) == int(keep.id):
            continue
        db.session.delete(c)
        n += 1
    return n


def _abandoned_cart_try_upgrade_synthetic_zid(row: AbandonedCart, new_zid: str) -> None:
    """إذا كان ‎zid_cart_id‎ اصطناعياً ‎cf_w_*‎ ووصلنا ‎cart_id‎ حقيقي، نحدّث دون الاصطدام بصف آخر."""
    nz = (new_zid or "").strip()[:255]
    if not nz or nz.startswith("cf_w_"):
        return
    cur = (row.zid_cart_id or "").strip()
    if not cur.startswith("cf_w_"):
        return
    if cur == nz:
        return
    other = db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == nz).first()
    if other is not None and int(other.id) != int(row.id):
        return
    row.zid_cart_id = nz


def _resolve_abandoned_cart_row_for_vip_live_sync(
    *,
    payload: dict[str, Any],
    merge_payload: dict[str, Any],
    payload_session: dict[str, Any],
    store_row: Optional[Store],
    cid_synth: str,
) -> Optional[AbandonedCart]:
    """
    دمج صفوف ‎AbandonedCart‎ قبل مزامنة ‎VIP‎ من أحداث السلة الحيّة:
    يفضّل ‎zid_cart_id‎ الحقيقي ثم الأحدث ‎last_seen_at‎، ويحذف المكررات.
    """
    rk = _recovery_key_from_payload(merge_payload)
    sid_raw = merge_payload.get("session_id") or payload_session.get("session_id")
    sid_s = sid_raw.strip()[:512] if isinstance(sid_raw, str) and sid_raw.strip() else ""
    real_cid = (_cart_id_str_from_payload(payload) or "").strip()[:255]
    cart_ids: list[str] = []
    for x in (real_cid, (cid_synth or "").strip()[:255]):
        if x and x not in cart_ids:
            cart_ids.append(x)
    cands = _collect_abandoned_cart_rows_for_merge(
        cart_ids=cart_ids,
        session_id=sid_s if sid_s else None,
        recovery_key=rk,
        store_row=store_row,
    )
    if not cands:
        return None
    keep = _pick_canonical_abandoned_cart_row(cands)
    if keep is None:
        return None
    _delete_noncanonical_abandoned_merge_rows(keep=keep, candidates=cands)
    return keep


def _cleanup_duplicate_vip_abandoned_rows(*, store_id_scope: Optional[int] = None) -> int:
    """
    ‎vip_mode‎ + ‎status=abandoned‎: لكل ‎(store_id, recovery_session_id)‎ يُبقى الأحدث ‎last_seen_at‎
    ويُحذف الباقي (تنظيف تاريخي).
    """
    deleted = 0
    try:
        _ensure_store_widget_schema()
        db.create_all()
        q = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.vip_mode.is_(True))
            .filter(AbandonedCart.status == "abandoned")
            .filter(AbandonedCart.recovery_session_id.isnot(None))
        )
        if store_id_scope is not None:
            vid = int(store_id_scope)
            q = q.filter(
                (AbandonedCart.store_id == vid) | (AbandonedCart.store_id.is_(None))  # type: ignore[union-attr]
            )
        rows = list(q.all())
        groups: dict[tuple[Optional[int], str], list[AbandonedCart]] = {}
        for ac in rows:
            sid = (ac.recovery_session_id or "").strip()[:512]
            if not sid:
                continue
            key = (ac.store_id, sid)
            groups.setdefault(key, []).append(ac)
        for grp in groups.values():
            if len(grp) <= 1:
                continue

            def _ts(r: AbandonedCart) -> datetime:
                t = r.last_seen_at
                if t is None:
                    return datetime.min.replace(tzinfo=timezone.utc)
                if t.tzinfo is None:
                    return t.replace(tzinfo=timezone.utc)
                return t.astimezone(timezone.utc)

            grp.sort(key=_ts, reverse=True)
            for dup in grp[1:]:
                db.session.delete(dup)
                deleted += 1
        if deleted:
            db.session.commit()
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        log.warning("[VIP DEDUPE] cleanup failed", exc_info=True)
    return deleted


def _recovery_message_for_step(step: int) -> str:
    for s, t in _RECOVERY_SEQUENCE_STEPS:
        if s == step:
            return t
    return _RECOVERY_SEQUENCE_STEPS[0][1]


def _default_recovery_message() -> str:
    """نص الخطوة ‎1‎ (للتوافق مع السجلات السابقة/التخطي)."""
    return _recovery_message_for_step(1)


def _cart_recovery_reason_latest_row(
    store_slug: str, session_id: str,
) -> Optional[CartRecoveryReason]:
    """آخر صف ‎CartRecoveryReason‎ لهذه الجلسة، أو ‎None‎."""
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    if not ss or not sid:
        return None
    try:
        from schema_widget import (
            ensure_cart_recovery_reason_phone_schema,
            ensure_cart_recovery_reason_rejection_schema,
        )

        ensure_cart_recovery_reason_phone_schema(db)
        ensure_cart_recovery_reason_rejection_schema(db)
        db.create_all()
        return (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == ss,
                CartRecoveryReason.session_id == sid,
            )
            .order_by(CartRecoveryReason.updated_at.desc())
            .first()
        )
    except Exception:  # noqa: BLE001
        db.session.rollback()
        return None


def _cart_recovery_reason_latest_row_any_store(
    session_id: str,
) -> Optional[CartRecoveryReason]:
    """آخر صف ‎CartRecoveryReason‎ لهذه ‎session_id‎ بأي ‎store_slug‎ (للاقتراحات الذكية فقط)."""
    sid = (session_id or "").strip()[:512]
    if not sid:
        return None
    try:
        from schema_widget import (
            ensure_cart_recovery_reason_phone_schema,
            ensure_cart_recovery_reason_rejection_schema,
        )

        ensure_cart_recovery_reason_phone_schema(db)
        ensure_cart_recovery_reason_rejection_schema(db)
        db.create_all()
        return (
            db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.session_id == sid)
            .order_by(CartRecoveryReason.updated_at.desc())
            .first()
        )
    except Exception:  # noqa: BLE001
        db.session.rollback()
        return None


def _recovery_row_user_rejected_help(row: Optional[CartRecoveryReason]) -> bool:
    if row is None:
        return False
    try:
        return row.user_rejected_help is True
    except Exception:  # noqa: BLE001
        return getattr(row, "user_rejected_help", False) is True


def _clear_user_rejected_help_for_session(store_slug: str, session_id: str) -> None:
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    if not ss or not sid:
        return
    try:
        from schema_widget import ensure_cart_recovery_reason_rejection_schema

        ensure_cart_recovery_reason_rejection_schema(db)
        db.create_all()
        row = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == ss,
                CartRecoveryReason.session_id == sid,
            )
            .first()
        )
        if row is None:
            return
        row.user_rejected_help = False
        row.rejection_timestamp = None
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()


def _recovery_should_skip_whatsapp_for_session(
    store_slug: str, session_id: str,
) -> bool:
    row = _cart_recovery_reason_latest_row(store_slug, session_id)
    return _recovery_row_user_rejected_help(row)


def _reason_tag_for_session(store_slug: str, session_id: str) -> Optional[str]:
    """آخر ‎reason_tag‎ محفوظ في ‎cart_recovery_reasons‎ لهذه الجلسة، أو ‎None‎."""
    row = _cart_recovery_reason_latest_row(store_slug, session_id)
    if row is None:
        return None
    tag = (row.reason or "").strip()
    return tag if tag else None


def _store_slug_for_cart_recovery_reason(ac: AbandonedCart) -> Optional[str]:
    sid = getattr(ac, "store_id", None)
    if sid is not None:
        try:
            row = db.session.get(Store, int(sid))
        except (SQLAlchemyError, OSError, TypeError, ValueError):
            db.session.rollback()
            row = None
        zs = getattr(row, "zid_store_id", None) if row is not None else None
        if zs and str(zs).strip():
            return str(zs).strip()[:255]
    dash = _dashboard_recovery_store_row()
    z2 = getattr(dash, "zid_store_id", None) if dash is not None else None
    if z2 and str(z2).strip():
        return str(z2).strip()[:255]
    return None


def _reason_tag_for_abandoned_cart(ac: AbandonedCart) -> Optional[str]:
    """
    مصدر ‎reason_tag‎ لاقتراح «الإجراء المقترح» فقط.

    الأولوية: ‎reason_tag‎ من ‎raw_payload‎ → آخر ‎CartRecoveryReason‎
    لنفس ‎(store_slug, session_id)‎ → آخر صف لنفس ‎session_id‎ بأي متجر.
    """
    tag = _vip_reason_tag_from_abandoned_cart(ac)
    if tag:
        return tag
    sess = (getattr(ac, "recovery_session_id", None) or "").strip()
    if not sess:
        return None
    ss = _store_slug_for_cart_recovery_reason(ac)
    row: Optional[CartRecoveryReason] = None
    if ss:
        row = _cart_recovery_reason_latest_row(ss, sess)
    if row is None:
        row = _cart_recovery_reason_latest_row_any_store(sess)
    if row is None:
        return None
    out = (row.reason or "").strip()
    return out if out else None


_NORMAL_RECOVERY_PHASE_ORDER: list[tuple[str, str]] = [
    ("pending_send", "بانتظار الإرسال"),
    ("first_message_sent", "تم إرسال الرسالة الأولى"),
    ("pending_second_attempt", "بانتظار المحاولة الثانية"),
    ("reminder_sent", "تم إرسال الرسالة الثانية"),
    ("behavioral_link_clicked", "عاد لصفحة الدفع"),
    ("behavioral_replied", "العميل تفاعل مع الرسالة"),
    ("customer_returned", "عاد للموقع — تم إيقاف التسلسل"),
    ("ignored", "متجاهل"),
    ("stopped_manual", "تم الإيقاف"),
    ("stopped_purchase", "تم التحويل"),
    ("recovery_complete", "اكتمل الاسترجاع"),
]

# Phases where overlaying a «missing phone» banner would duplicate or confuse the primary story.
_NORMAL_RECOVERY_PHASE_NO_MISSING_PHONE_OVERLAY = frozenset(
    {
        "customer_returned",
        "behavioral_replied",
        "behavioral_link_clicked",
        "recovery_complete",
        "stopped_purchase",
        "stopped_manual",
        "ignored",
    }
)

# ‎CartRecoveryLog.status‎ values that mean a WhatsApp recovery message was delivered
# (includes ‎mock_sent‎ from delayed automation and ‎sent_real‎ from the queue / VIP paths).
_NORMAL_RECOVERY_SENT_LOG_STATUSES = frozenset({"sent_real", "mock_sent"})

_DEFAULT_SECOND_ATTEMPT_GAP_MINUTES = 120


def _second_attempt_delay_minutes_from_store(store: Optional[Any]) -> int:
    """دقائق الانتظار بعد نجاح الإرسال الأول قبل المحاولة الثانية (‎NULL‎ = افتراضي آمن)."""
    raw = getattr(store, "second_attempt_delay_minutes", None) if store is not None else None
    if raw is None:
        return int(_DEFAULT_SECOND_ATTEMPT_GAP_MINUTES)
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return int(_DEFAULT_SECOND_ATTEMPT_GAP_MINUTES)
    if v < 1:
        return int(_DEFAULT_SECOND_ATTEMPT_GAP_MINUTES)
    return max(5, min(v, 10080))


def _log_second_recovery_line(tag: str, **fields: Any) -> None:
    parts = " ".join(f"{k}={fields[k]}" for k in sorted(fields.keys()))
    msg = f"{tag} {parts}".strip()
    try:
        log.info(msg)
        print(msg, flush=True)
    except OSError:
        pass


_SECOND_RECOVERY_SKIPPED_PUBLIC = frozenset(
    {
        "missing_phone",
        "missing_reason",
        "max_attempts_reached",
        "purchase_completed",
        "user_returned",
        "customer_replied",
        "already_sent",
        "automation_disabled",
    }
)


def _second_recovery_public_skip_reason(internal: str) -> str:
    """Maps engine/internal reasons to the fixed [SECOND RECOVERY SKIPPED] reason= enum."""
    s = (internal or "").strip().lower()
    if s in (
        "purchase_completed",
        "stopped_converted",
    ):
        return "purchase_completed"
    if s in ("no_verified_phone", "skipped_no_verified_phone"):
        return "missing_phone"
    if s in ("customer_phone_equals_merchant_phone",):
        return "missing_phone"
    if s in (
        "missing_reason_tag",
        "missing_last_activity",
        "skipped_missing_reason_tag",
        "skipped_missing_last_activity",
    ):
        return "missing_reason"
    if s in ("delay_not_elapsed",):
        return "automation_disabled"
    if s in (
        "attempt_limit",
        "skipped_attempt_limit",
        "max_attempts_reached",
    ):
        return "max_attempts_reached"
    if s in ("customer_returned", "skipped_anti_spam", "user_returned"):
        return "user_returned"
    if s in (
        "customer_positive_reply",
        "skipped_followup_customer_replied",
        "user_rejected_help",
    ):
        return "customer_replied"
    if s in ("already_sent",):
        return "already_sent"
    if s in (
        "reason_template_disabled",
        "skipped_reason_template_disabled",
        "skipped_delay_gate",
        "automation_disabled",
        "whatsapp_failed",
        "delay_or_attempt_gate",
    ):
        return "automation_disabled"
    return "automation_disabled"


def _log_second_recovery_skipped(
    *,
    reason: str,
    gate_detail: str = "",
    recovery_key: Optional[str] = None,
    **fields: Any,
) -> None:
    pub = _second_recovery_public_skip_reason(reason)
    if pub not in _SECOND_RECOVERY_SKIPPED_PUBLIC:
        pub = "automation_disabled"
    extra = dict(fields)
    if gate_detail:
        extra["gate_detail"] = gate_detail
    _log_second_recovery_line("[SECOND RECOVERY SKIPPED]", reason=pub, **extra)
    if recovery_key:
        with _recovery_session_lock:
            _session_recovery_last_second_skip_reason[recovery_key] = pub


def _second_recovery_diagnose_should_send(
    last_activity_time: Optional[datetime],
    *,
    user_returned_to_site: bool,
    now: datetime,
    store: Any,
    sent_count: int,
    configured_message_count: Optional[int] = None,
) -> Tuple[bool, str]:
    """Mirror of should_send_whatsapp (read-only) — returns (allowed, reason_tag)."""
    if user_returned_to_site:
        return False, "user_returned"
    cfg = _recovery_config(store)
    if not cfg.get("whatsapp_recovery_enabled", True):
        return False, "automation_disabled"
    try:
        sc = int(sent_count)
    except (TypeError, ValueError):
        sc = 0
    sc = max(0, sc)
    if configured_message_count is not None:
        try:
            max_a = max(1, int(configured_message_count))
        except (TypeError, ValueError):
            max_a = _max_recovery_attempts(store)
    else:
        max_a = _max_recovery_attempts(store)
    if max_a < 1:
        return False, "automation_disabled"
    if sc >= max_a:
        return False, "max_attempts_reached"
    if last_activity_time is None:
        return True, "allowed"
    recovery_delay_minutes = _recovery_delay_minutes_from_store(store)
    t = _naive_utc(now)
    last_activity = _naive_utc(last_activity_time)
    delay_passed = t >= last_activity + timedelta(minutes=recovery_delay_minutes)
    if not delay_passed:
        return False, "delay_not_elapsed"
    return True, "allowed"


def _normal_recovery_configured_message_count_from_runtime(
    recovery_key: str,
    store_obj: Any,
) -> int:
    """عدد رسائل التسلسل المفعّل: ‎multi_message‎ من القوالب أو ‎Store.recovery_attempts‎."""
    with _recovery_session_lock:
        multi_cap = _session_recovery_multi_attempt_cap.get(recovery_key)
    if multi_cap is not None:
        try:
            return max(1, int(multi_cap))
        except (TypeError, ValueError):
            return max(1, int(_max_recovery_attempts(store_obj)))
    return max(1, int(_max_recovery_attempts(store_obj)))


def _normal_recovery_configured_message_count_for_abandoned_cart(
    ac: AbandonedCart,
    store_ac: Optional[Any],
) -> int:
    if store_ac is None:
        return 1
    rt = _reason_tag_for_abandoned_cart(ac)
    slots = multi_message_slots_for_abandon(rt, store_ac)
    if slots is not None:
        return max(1, len(slots))
    return max(1, int(_max_recovery_attempts(store_ac)))


def _log_normal_recovery_sequence_config(
    *,
    configured_message_count: int,
    sent_count: int,
    attempt_index: int,
    recovery_key: str,
) -> None:
    _log_second_recovery_line(
        "[NORMAL RECOVERY SEQUENCE CONFIG]",
        configured_message_count=str(int(configured_message_count)),
        sent_count=str(int(sent_count)),
        attempt_index=str(int(attempt_index)),
        recovery_key=recovery_key,
    )


def _log_normal_recovery_attempt_decision(
    *,
    attempt_index: int,
    allowed: bool,
    reason: str,
) -> None:
    _log_second_recovery_line(
        "[NORMAL RECOVERY ATTEMPT DECISION]",
        attempt_index=str(int(attempt_index)),
        allowed="true" if allowed else "false",
        reason=(reason or "").strip()[:120],
    )


def _log_normal_recovery_attempt_sent(
    *,
    attempt_index: int,
    sid: str,
) -> None:
    _log_second_recovery_line(
        "[NORMAL RECOVERY ATTEMPT SENT]",
        attempt_index=str(int(attempt_index)),
        sid=(sid or "").strip()[:80],
    )


def _log_normal_recovery_attempt_skipped(
    *,
    attempt_index: int,
    reason: str,
) -> None:
    _log_second_recovery_line(
        "[NORMAL RECOVERY ATTEMPT SKIPPED]",
        attempt_index=str(int(attempt_index)),
        reason=(reason or "").strip()[:120],
    )


def _log_second_recovery_check(
    *,
    session_id: str,
    cart_id: Optional[str],
    sent_count: int,
    max_attempts: int,
    customer_phone: Optional[str],
    reason_tag: Optional[str],
    purchase_completed: bool,
    user_returned_to_site: bool,
    customer_replied: bool,
    allowed: bool,
) -> None:
    if not (session_id or "").strip():
        return
    cp = (customer_phone or "").strip()
    rt = (reason_tag or "").strip()
    _log_second_recovery_line(
        "[SECOND RECOVERY CHECK]",
        session_id=(session_id or "").strip(),
        cart_id=(cart_id or "") or "",
        sent_count=int(sent_count),
        max_attempts=int(max_attempts),
        customer_phone=cp,
        reason_tag=rt,
        purchase_completed=bool(purchase_completed),
        user_returned_to_site=bool(user_returned_to_site),
        customer_replied=bool(customer_replied),
        allowed=bool(allowed),
    )


def _last_sent_phone_from_recovery_logs(
    session_id: str, cart_id: Optional[str]
) -> Optional[str]:
    conds: list[Any] = []
    sid = (session_id or "").strip()[:512]
    cid = (cart_id or "").strip()[:255]
    if sid:
        conds.append(CartRecoveryLog.session_id == sid)
    if cid:
        conds.append(CartRecoveryLog.cart_id == cid)
    if not conds:
        return None
    try:
        db.create_all()
        row = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.status.in_(_NORMAL_RECOVERY_SENT_LOG_STATUSES))
            .filter(or_(*conds))
            .order_by(CartRecoveryLog.sent_at.desc(), CartRecoveryLog.id.desc())
            .first()
        )
        if row is None:
            return None
        p = getattr(row, "phone", None)
        ps = str(p).strip() if p else ""
        return ps if ps else None
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return None


def _cart_recovery_log_has_successful_send_for_step(
    session_id: str, cart_id: Optional[str], step: int
) -> bool:
    conds: list[Any] = []
    sid = (session_id or "").strip()[:512]
    cid = (cart_id or "").strip()[:255] if cart_id else ""
    if sid:
        conds.append(CartRecoveryLog.session_id == sid)
    if cid:
        conds.append(CartRecoveryLog.cart_id == cid)
    if not conds:
        return False
    try:
        db.create_all()
        n = (
            db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.step == int(step),
                CartRecoveryLog.status.in_(_NORMAL_RECOVERY_SENT_LOG_STATUSES),
                or_(*conds),
            )
            .count()
        )
        return int(n or 0) > 0
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return False


def _normal_recovery_followup_skip_hint_ar_from_log_status(status: str) -> Optional[str]:
    s = (status or "").strip().lower()
    ar_map = {
        "skipped_no_verified_phone": "توقفت: لا يوجد رقم",
        "skipped_anti_spam": "توقفت: العميل عاد للموقع",
        "skipped_attempt_limit": "توقفت: تجاوز عدد المحاولات",
        "skipped_followup_customer_replied": "توقفت: رد العميل",
        "skipped_missing_reason_tag": "توقفت: لا يوجد سبب",
        "skipped_missing_last_activity": "توقفت: لا يوجد نشاط",
        "skipped_delay_gate": "توقفت: لم تكتمل مهلة السكون",
        "skipped_reason_template_disabled": "توقفت: الأتمتة معطّلة",
        "whatsapp_failed": "توقفت: فشل الإرسال",
        "stopped_converted": "توقفت: اكتمال الشراء",
    }
    return ar_map.get(s)


def _normal_recovery_latest_followup_diagnostic_row(
    ac: AbandonedCart,
) -> Optional[CartRecoveryLog]:
    conds = _cart_recovery_log_filters_for_abandoned_cart(ac)
    if not conds:
        return None
    try:
        db.create_all()
        return (
            db.session.query(CartRecoveryLog)
            .filter(or_(*conds))
            .filter(CartRecoveryLog.step >= 2)
            .order_by(CartRecoveryLog.id.desc())
            .first()
        )
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return None


def _normal_recovery_latest_blocker_event_row(ac: AbandonedCart) -> Optional[CartRecoveryLog]:
    """
    أحدث سجل استرجاع لهذه السلة/الجلسة إذا كان آخر حدثاً ليس إرسالاً ناجحاً ولا ‎queued‎.
    يستخدم لعرض سبب التوقف للتاجر دون المساس بمسار الجدولة.
    """
    conds = _cart_recovery_log_filters_for_abandoned_cart(ac)
    if not conds:
        return None
    try:
        db.create_all()
        row = (
            db.session.query(CartRecoveryLog)
            .filter(or_(*conds))
            .order_by(CartRecoveryLog.id.desc())
            .first()
        )
        if row is None:
            return None
        st = (getattr(row, "status", None) or "").strip().lower()
        if st in _NORMAL_RECOVERY_SENT_LOG_STATUSES or st == "queued":
            return None
        return row
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return None


def _normal_recovery_latest_skipped_no_verified_phone_row(
    ac: AbandonedCart,
) -> Optional[CartRecoveryLog]:
    """أحدث ‎skipped_no_verified_phone‎ لهذه السلة — للعرض حتى لو كان السجل الأحدث ‎queued‎."""
    conds = _cart_recovery_log_filters_for_abandoned_cart(ac)
    if not conds:
        return None
    try:
        db.create_all()
        return (
            db.session.query(CartRecoveryLog)
            .filter(or_(*conds))
            .filter(CartRecoveryLog.status == "skipped_no_verified_phone")
            .order_by(CartRecoveryLog.id.desc())
            .first()
        )
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return None


def _normal_recovery_debug_for_session(session_id: str) -> dict[str, Any]:
    """تجميع قراءة فقط للتشخيص المحلي — ‎GET /dev/normal-recovery-debug‎."""
    sid = (session_id or "").strip()[:512]
    out: dict[str, Any] = {
        "ok": bool(sid),
        "session_id": sid,
        "current_stage": None,
        "sent_count": 0,
        "customer_phone": "",
        "reason_tag": None,
        "next_attempt_due_at": None,
        "last_skip_reason": None,
        "can_send_second_attempt": False,
    }
    if not sid:
        return out
    try:
        db.create_all()
        ac = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == sid)
            .order_by(AbandonedCart.last_seen_at.desc())
            .first()
        )
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        ac = None
    slug_guess = "demo"
    r_any = _cart_recovery_reason_latest_row_any_store(sid)
    if r_any is not None and (getattr(r_any, "store_slug", None) or "").strip():
        slug_guess = str(r_any.store_slug).strip()[:255]
    rk = _recovery_key_from_store_and_session(slug_guess, sid)
    with _recovery_session_lock:
        out["next_attempt_due_at"] = _session_recovery_followup_next_due_at.get(rk)
        out["last_skip_reason"] = _session_recovery_last_second_skip_reason.get(rk)
    out["reason_tag"] = _reason_tag_for_session(slug_guess, sid)
    if ac is None:
        return out
    out["current_stage"] = _normal_recovery_dashboard_phase_key(ac)
    out["sent_count"] = _cart_recovery_sent_real_count_for_abandoned(ac)
    ds = _dashboard_recovery_store_row()
    out["customer_phone"] = _normal_recovery_dashboard_resolve_customer_phone_raw(ac, ds)
    rt_ac = _reason_tag_for_abandoned_cart(ac)
    if rt_ac:
        out["reason_tag"] = rt_ac
    store_ac = _store_row_for_abandoned_cart(ac)
    try:
        max_a = max(0, int(_max_recovery_attempts(store_ac)))
    except (TypeError, ValueError):
        max_a = 1
    sent_n = int(out["sent_count"])
    can = max_a >= 2 and sent_n < max_a
    lr = _normal_recovery_latest_followup_diagnostic_row(ac)
    if lr is not None:
        st = (getattr(lr, "status", None) or "").strip().lower()
        if st and st not in _NORMAL_RECOVERY_SENT_LOG_STATUSES and st != "queued":
            can = False
    out["can_send_second_attempt"] = bool(can and sent_n < 2)
    return out


def _maybe_log_second_recovery_stopped(
    seq_attempt: Optional[int],
    *,
    scheduled_step: Optional[int] = None,
    reason: str,
    recovery_key: Optional[str] = None,
    gate_detail: str = "",
    **fields: Any,
) -> None:
    try:
        sa = int(seq_attempt) if seq_attempt is not None else 0
    except (TypeError, ValueError):
        sa = 0
    try:
        st = int(scheduled_step) if scheduled_step is not None else 0
    except (TypeError, ValueError):
        st = 0
    if max(sa, st) >= 2:
        _log_second_recovery_skipped(
            reason=reason,
            gate_detail=gate_detail,
            recovery_key=recovery_key,
            **fields,
        )


def _latest_sent_recovery_message_for_followup(
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
) -> str:
    """آخر نص إرسال ناجح لهذه الجلسة لتفادي تكرار نفس الجملة في المتابعة."""
    _ = store_slug
    conds: list[Any] = []
    sid = (session_id or "").strip()[:512]
    cid = (cart_id or "").strip()[:255]
    if sid:
        conds.append(CartRecoveryLog.session_id == sid)
    if cid:
        conds.append(CartRecoveryLog.cart_id == cid)
    if not conds:
        return ""
    try:
        db.create_all()
        row = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.status.in_(_NORMAL_RECOVERY_SENT_LOG_STATUSES))
            .filter(or_(*conds))
            .order_by(CartRecoveryLog.sent_at.desc(), CartRecoveryLog.id.desc())
            .first()
        )
        if row is None:
            return ""
        return str(getattr(row, "message", None) or "").strip()
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return ""


def _normal_recovery_positive_reply_blocks_followup(
    *,
    session_id: str,
    cart_id: Optional[str],
) -> bool:
    """رد إيجابي مسجّل (‎MerchantFollowupAction‎) يوقف المتابعة التلقائية."""
    sid = (session_id or "").strip()[:512]
    cid = (cart_id or "").strip()[:255]
    if not sid and not cid:
        return False
    try:
        db.create_all()
        cand_ids: list[int] = []
        if cid:
            ac = (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.zid_cart_id == cid)
                .first()
            )
            if ac is not None and getattr(ac, "id", None) is not None:
                cand_ids.append(int(ac.id))
        if sid:
            for ac in (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.recovery_session_id == sid)
                .limit(8)
                .all()
            ):
                aid = getattr(ac, "id", None)
                if aid is not None and int(aid) not in cand_ids:
                    cand_ids.append(int(aid))
        for aid in cand_ids:
            hit = (
                db.session.query(MerchantFollowupAction)
                .filter(
                    MerchantFollowupAction.abandoned_cart_id == aid,
                    MerchantFollowupAction.reason == REASON_CUSTOMER_REPLIED_YES,
                )
                .first()
            )
            if hit is not None:
                return True
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
    return customer_replied_flagged_for_session(sid, cid or None)


def _cart_recovery_log_filters_for_abandoned_cart(ac: AbandonedCart) -> list[Any]:
    sess = (getattr(ac, "recovery_session_id", None) or "").strip()[:512]
    zid = (getattr(ac, "zid_cart_id", None) or "").strip()[:255]
    conds: list[Any] = []
    if sess:
        conds.append(CartRecoveryLog.session_id == sess)
    if zid:
        conds.append(CartRecoveryLog.cart_id == zid)
    return conds


def _cart_recovery_sent_real_count_for_abandoned(ac: AbandonedCart) -> int:
    """عدد إرسالات واتساب الاسترجاع الناجحة من ‎CartRecoveryLog‎ (‎sent_real‎ و ‎mock_sent‎)."""
    conds = _cart_recovery_log_filters_for_abandoned_cart(ac)
    if not conds:
        return 0
    try:
        db.create_all()
        n = (
            db.session.query(func.count(CartRecoveryLog.id))
            .filter(CartRecoveryLog.status.in_(_NORMAL_RECOVERY_SENT_LOG_STATUSES))
            .filter(or_(*conds))
            .scalar()
        )
        return int(n or 0)
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return 0


def _normal_recovery_coarse_status(phase_key: str) -> str:
    """
    حالة البطاقة للاسترجاع العادي — توسعة لـ ‎replied‎ لاحقاً.
    ‎pending‎ / ‎sent‎ / ‎replied‎ / ‎converted‎ / ‎stopped‎ / ‎returned‎ / ‎ignored‎
    """
    pk = (phase_key or "").strip()
    if pk in ("first_message_sent", "reminder_sent"):
        return "sent"
    if pk == "pending_second_attempt":
        return "pending"
    if pk == "behavioral_replied":
        return "replied"
    if pk == "behavioral_link_clicked":
        return "clicked"
    if pk == "customer_returned":
        return "returned"
    if pk == "ignored":
        return "ignored"
    if pk == "recovery_complete":
        return "converted"
    if pk in ("stopped_manual", "stopped_purchase"):
        return "stopped"
    if pk == "pending_send":
        return "pending"
    return "pending"


def _store_row_for_abandoned_cart(ac: AbandonedCart) -> Optional[Store]:
    """صف ‎Store‎ لحساب ‎max_recovery_attempts‎ لبطاقة الاسترجاع العادي."""
    sid_raw = getattr(ac, "store_id", None)
    try:
        if sid_raw is not None:
            db.create_all()
            row = db.session.query(Store).filter_by(id=int(sid_raw)).first()
            if row is not None:
                return row
    except (TypeError, ValueError, SQLAlchemyError, OSError):
        db.session.rollback()
    return _dashboard_recovery_store_row()


def _log_normal_recovery_auto_start(
    *,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    mode: str,
) -> None:
    cid = (cart_id or "").strip() or "-"
    sid = (session_id or "").strip() or "-"
    try:
        log.info(
            "[NORMAL RECOVERY AUTO START] store_slug=%s session_id=%s cart_id=%s mode=%s",
            store_slug,
            sid,
            cid,
            mode,
        )
        print(
            f"[NORMAL RECOVERY AUTO START] session_id={sid} cart_id={cid} mode={mode}",
            flush=True,
        )
    except OSError:
        pass


def _latest_cart_recovery_log_row_for_abandoned(
    ac: AbandonedCart,
) -> Optional[CartRecoveryLog]:
    conds = _cart_recovery_log_filters_for_abandoned_cart(ac)
    if not conds:
        return None
    try:
        db.create_all()
        row = (
            db.session.query(CartRecoveryLog)
            .filter(or_(*conds))
            .order_by(CartRecoveryLog.created_at.desc())
            .first()
        )
        return row
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return None


def _normal_recovery_dashboard_phase_key(ac: AbandonedCart) -> str:
    """مفتاح مرحلة واجهة الاسترجاع العادي — قراءة فقط؛ للعرض ولتوسعة المحرك لاحقاً."""
    st = (getattr(ac, "status", None) or "").strip().lower()
    if st == "recovered":
        return "recovery_complete"
    bh = behavioral_dict_for_abandoned_cart(ac)
    if bh.get("customer_replied") is True:
        return "behavioral_replied"
    if bh.get("recovery_link_clicked") is True:
        return "behavioral_link_clicked"
    if bh.get("user_returned_to_site") is True:
        return "customer_returned"
    sess = (getattr(ac, "recovery_session_id", None) or "").strip()[:512]
    if sess:
        r_any = _cart_recovery_reason_latest_row_any_store(sess)
        if _recovery_row_user_rejected_help(r_any):
            return "stopped_manual"
    sent_n = _cart_recovery_sent_real_count_for_abandoned(ac)
    log_last = _latest_cart_recovery_log_row_for_abandoned(ac)
    if log_last is not None:
        ls = (getattr(log_last, "status", None) or "").strip().lower()
        if ls == "stopped_converted":
            return "stopped_purchase"
        if ls == "skipped_anti_spam":
            return "customer_returned"
        if ls == "skipped_user_rejected_help":
            return "ignored"
        if ls == "skipped_missing_reason_tag" and sent_n < 1:
            return "ignored"
    store_ac = _store_row_for_abandoned_cart(ac)
    try:
        max_a = int(_normal_recovery_configured_message_count_for_abandoned_cart(ac, store_ac))
    except (TypeError, ValueError):
        max_a = 1
    max_a = max(0, max_a)
    if sent_n >= max_a >= 1:
        if max_a == 1:
            return "first_message_sent"
        return "reminder_sent"
    if sent_n >= 2:
        return "reminder_sent"
    if sent_n == 1 and max_a >= 2:
        return "pending_second_attempt"
    if sent_n == 1:
        return "first_message_sent"
    return "pending_send"


def _normal_recovery_identity_trust_surface(ac: AbandonedCart) -> Optional[str]:
    """رسالة تشغيلية آمنة عند تعارض الهوية؛ لا تكشف تفاصيل تقنية."""
    from services.cartflow_identity import (
        IDENTITY_TRUST_FAILED_KEY,
        MERCHANT_IDENTITY_TRUST_AR,
        detect_abandoned_cart_identity_anomaly,
        log_cartflow_identity_warning,
    )

    bh = behavioral_dict_for_abandoned_cart(ac)
    if bh.get(IDENTITY_TRUST_FAILED_KEY) is True:
        return str(bh.get("identity_trust_message_ar") or MERCHANT_IDENTITY_TRUST_AR)
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    zid = (getattr(ac, "zid_cart_id", None) or "").strip()
    bad, rsn = detect_abandoned_cart_identity_anomaly(sid, zid or None)
    if bad:
        slug_guess = (_store_slug_for_cart_recovery_reason(ac) or "").strip()[:255]
        log_cartflow_identity_warning(
            store_slug=slug_guess or "-",
            resolved_store_id=str(getattr(ac, "store_id", "") or "") or "-",
            expected_store_id="-",
            session_id=sid,
            cart_id=zid,
            reason=f"dashboard_identity_anomaly:{rsn}",
        )
        return MERCHANT_IDENTITY_TRUST_AR
    return None


def _normal_recovery_phase_steps_payload(ac: AbandonedCart) -> dict[str, Any]:
    order = _NORMAL_RECOVERY_PHASE_ORDER
    current_key = _normal_recovery_dashboard_phase_key(ac)
    key_to_index = {k: i for i, (k, _) in enumerate(order)}
    if current_key not in key_to_index:
        current_key = "pending_send"
    curr_idx = key_to_index[current_key]
    label_ar = order[curr_idx][1]
    coarse = _normal_recovery_coarse_status(current_key)
    try:
        log.info(
            "[NORMAL RECOVERY STATUS UPDATE] status=%s phase_key=%s abandoned_cart_id=%s",
            coarse,
            current_key,
            getattr(ac, "id", None),
        )
        if coarse != "pending":
            print(
                f"[NORMAL RECOVERY STATUS UPDATE] status={coarse}",
                flush=True,
            )
    except OSError:
        pass
    except (TypeError, ValueError):
        pass
    steps_out: list[dict[str, Any]] = []
    for i, (k, lbl) in enumerate(order):
        steps_out.append(
            {
                "key": k,
                "label_ar": lbl,
                "done": i < curr_idx,
                "current": i == curr_idx,
                "upcoming": i > curr_idx,
            }
        )
    store_ac = _store_row_for_abandoned_cart(ac)
    try:
        max_disp = max(1, int(_normal_recovery_configured_message_count_for_abandoned_cart(ac, store_ac)))
    except (TypeError, ValueError):
        max_disp = 1
    sent_ct = _cart_recovery_sent_real_count_for_abandoned(ac)
    seq_label_ar: Optional[str] = None
    if sent_ct >= max_disp >= 1:
        seq_label_ar = "اكتمل تسلسل الاسترجاع"
    elif sent_ct >= 2:
        seq_label_ar = "تم إرسال الرسالة الثانية"
    elif sent_ct >= 1:
        seq_label_ar = "تم إرسال الرسالة الأولى"
    cust_raw = _normal_recovery_dashboard_resolve_customer_phone_raw(ac, store_ac)
    cust_phone_display_ar = cust_raw if cust_raw else "لا يوجد رقم عميل"
    behavioral_pre = behavioral_dict_for_abandoned_cart(ac)
    blocker_row = _normal_recovery_latest_blocker_event_row(ac)
    blocker_bundle: Optional[dict[str, Any]] = None
    blocker_key_out: Optional[str] = None
    latest_log_status: Optional[str] = None
    if blocker_row is not None:
        latest_log_status = str(getattr(blocker_row, "status", None) or "") or None
        blocker_bundle = recovery_blocker_from_latest_log_status(
            getattr(blocker_row, "status", None)
        )
        if isinstance(blocker_bundle, dict) and blocker_bundle.get("key"):
            blocker_key_out = str(blocker_bundle.get("key"))
    if blocker_bundle is None:
        cr_fb = (cust_raw or "").strip()
        if (
            not cr_fb
            and sent_ct == 0
            and current_key not in _NORMAL_RECOVERY_PHASE_NO_MISSING_PHONE_OVERLAY
        ):
            if _normal_recovery_latest_skipped_no_verified_phone_row(ac) is not None:
                blocker_bundle = recovery_blocker_from_latest_log_status(
                    "skipped_no_verified_phone"
                )
                blocker_key_out = "missing_customer_phone"
                latest_log_status = "skipped_no_verified_phone"
            else:
                blocker_bundle = dict(
                    get_recovery_blocker_display_state("missing_customer_phone")
                )
                blocker_key_out = "missing_customer_phone"
    _lc_notes: list[str] = []
    _lc_hint_override: Optional[str] = None
    try:
        from services.cartflow_lifecycle_guard import reconcile_normal_recovery_dashboard_hints

        _slug_lc = str(_store_slug_for_cart_recovery_reason(ac) or "").strip()[:255] or "default"
        _recon = reconcile_normal_recovery_dashboard_hints(
            store_slug=_slug_lc,
            session_id=str(getattr(ac, "recovery_session_id", None) or ""),
            cart_id=str(getattr(ac, "zid_cart_id", None) or ""),
            phase_key=current_key,
            sent_ct=int(sent_ct),
            latest_log_status=latest_log_status,
            behavioral=behavioral_pre,
            blocker_key=blocker_key_out,
            blocker_bundle=blocker_bundle,
            seq_label_ar=seq_label_ar,
            operational_hint_ar=None,
        )
        blocker_bundle = _recon.get("blocker_bundle")
        blocker_key_out = _recon.get("blocker_key")
        seq_label_ar = _recon.get("sequence_label_ar")
        _lc_hint_override = _recon.get("operational_hint_ar")
        _raw_notes = _recon.get("lifecycle_notes")
        if isinstance(_raw_notes, list):
            _lc_notes = [str(x) for x in _raw_notes]
    except Exception:
        _lc_hint_override = None
    hint_ar: Optional[str] = None
    last_skip_pub: Optional[str] = None
    op_hint_ar: Optional[str] = None
    if isinstance(blocker_bundle, dict) and blocker_bundle:
        hint_ar = str(blocker_bundle.get("label_ar") or "") or None
        last_skip_pub = blocker_key_out
        op_hint_ar = str(blocker_bundle.get("operational_hint_ar") or "").strip() or None
    if isinstance(_lc_hint_override, str) and _lc_hint_override.strip():
        op_hint_ar = _lc_hint_override.strip()
    try:
        from services.cartflow_identity import IDENTITY_TRUST_FAILED_KEY
        from services.cartflow_observability_runtime import (
            detect_recovery_runtime_conflicts,
            log_runtime_conflicts,
        )

        trust_failed = behavioral_pre.get(IDENTITY_TRUST_FAILED_KEY) is True
        log_s = (latest_log_status or "").strip().lower()
        sent_ok = log_s in ("mock_sent", "sent_real")
        _conflicts = detect_recovery_runtime_conflicts(
            abandoned_status=str(getattr(ac, "status", "") or ""),
            behavioral=behavioral_pre,
            latest_log_status=latest_log_status,
            identity_trust_failed=trust_failed,
            sent_ok_latest_log=sent_ok,
        )
        if _conflicts:
            log_runtime_conflicts(
                _conflicts,
                session_id=(getattr(ac, "recovery_session_id", None) or ""),
                cart_id=(getattr(ac, "zid_cart_id", None) or ""),
            )
            try:
                from services.cartflow_duplicate_guard import (
                    note_dashboard_payload_state_conflict,
                )

                for _cfc in _conflicts:
                    note_dashboard_payload_state_conflict(
                        reason_code=str(_cfc),
                        session_id=str(
                            getattr(ac, "recovery_session_id", None) or ""
                        ),
                        cart_id=str(getattr(ac, "zid_cart_id", None) or ""),
                    )
            except Exception:
                pass
    except Exception:
        pass
    out_nr: dict[str, Any] = {
        "normal_recovery_phase_key": current_key,
        "normal_recovery_phase_label_ar": label_ar,
        "normal_recovery_status": coarse,
        "normal_recovery_phase_index": curr_idx + 1,
        "normal_recovery_phase_total": len(order),
        "normal_recovery_phase_steps": steps_out,
        "normal_recovery_attempt_cap": max_disp,
        "normal_recovery_attempt_sent": sent_ct,
        "normal_recovery_sequence_label_ar": seq_label_ar,
        "normal_recovery_followup_hint_ar": hint_ar,
        "normal_recovery_operational_hint_ar": op_hint_ar,
        "normal_recovery_last_skip_reason": last_skip_pub,
        "normal_recovery_customer_phone_display_ar": cust_phone_display_ar,
        "normal_recovery_blocker": blocker_bundle,
        "normal_recovery_blocker_key": blocker_key_out,
    }
    if _lc_notes:
        out_nr["normal_recovery_lifecycle_notes"] = _lc_notes
    out_nr.update(conversation_dashboard_extras(ac))
    trust_ar = _normal_recovery_identity_trust_surface(ac)
    if trust_ar:
        out_nr["normal_recovery_identity_trust_ar"] = trust_ar
    return out_nr


def _last_activity_utc_from_recovery_row(
    row: Optional[CartRecoveryReason],
) -> Optional[datetime]:
    """‎updated_at‎ من صف السبب كـ ‎UTC‎ (منطق السكون لـ ‎should_send_whatsapp‎)."""
    if row is None or row.updated_at is None:
        return None
    dt = row.updated_at
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_store_row_for_recovery(store_slug: Optional[str] = None) -> Optional[Store]:
    """صف ‎Store‎ للاسترجاع و‎VIP‎: ‎zid_store_id‎ يطابق ‎store‎ من الحمولة؛ ‎demo/default‎ → نفس صف لوحة الإعدادات (آخر ‎id‎)؛ وإلا آخر سطر."""
    try:
        db.create_all()
        _ensure_store_widget_schema()
        _ensure_default_store_for_recovery()
        latest = _dashboard_recovery_store_row()
        ss_full = (store_slug or "").strip()
        ss_key = ss_full.casefold()
        if not ss_key:
            return latest
        if ss_key in _WIDGET_STORE_SLUGS_USE_DASHBOARD_LATEST:
            return latest
        row = db.session.query(Store).filter_by(zid_store_id=ss_full).first()
        if row is None:
            return latest
        return row
    except Exception:  # noqa: BLE001
        db.session.rollback()
        return None


def _load_latest_store_for_recovery() -> Optional[Store]:
    return _load_store_row_for_recovery(None)


def _abandoned_cart_cart_value_for_recovery(cart_id: Optional[str]) -> Optional[float]:
    """قيمة ‎cart_value‎ من ‎abandoned_carts‎ إن وُجدت، لاستخدام ‎VIP check‎ فقط."""
    cid = (str(cart_id).strip()[:255] if cart_id is not None else "") or ""
    if not cid:
        return None
    try:
        row = (
            db.session.query(AbandonedCart.cart_value)
            .filter(AbandonedCart.zid_cart_id == cid)
            .order_by(AbandonedCart.last_seen_at.desc())
            .first()
        )
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return None
    if row is None or row[0] is None:
        return None
    try:
        return float(row[0])
    except (TypeError, ValueError):
        return None


def _cart_total_from_abandon_payload(payload: dict[str, Any]) -> Optional[float]:
    """مجموع السلة من حمولة ‎cart_abandoned‎ (قيم عليا أو أسطر ‎cart‎) لمسار ‎VIP‎."""
    if not isinstance(payload, dict):
        return None
    for key in ("cart_total", "cart_value", "total", "total_price", "amount", "subtotal"):
        if key not in payload:
            continue
        raw = payload.get(key)
        if raw is None:
            continue
        try:
            if isinstance(raw, str):
                raw = str(raw).strip().replace(",", "")
            v = float(raw)
        except (TypeError, ValueError):
            continue
        if v == v and v >= 0:  # not NaN
            return v
    cart = payload.get("cart")
    if isinstance(cart, list) and cart:
        total = 0.0
        found = False
        for it in cart:
            if not isinstance(it, dict):
                continue
            pr = it.get("price") or it.get("unit_price") or it.get("amount") or it.get("total")
            if pr is None:
                continue
            try:
                p = float(pr)
            except (TypeError, ValueError):
                continue
            q_raw = it.get("quantity") or it.get("qty") or 1
            try:
                q = float(q_raw) if q_raw is not None else 1.0
            except (TypeError, ValueError):
                q = 1.0
            total += p * max(q, 0.0)
            found = True
        if found and total > 0:
            return total
    return None


def _persist_cart_value_from_abandon_for_vip(cart_id: Optional[str], payload: dict[str, Any]) -> None:
    """يحدّث ‎AbandonedCart.cart_value‎ من حمولة الترك عند وجود السطر — لمسارات التأخير/المتعددة لاحقاً."""
    pay = _cart_total_from_abandon_payload(payload)
    cid = (str(cart_id).strip()[:255] if cart_id else "") or ""
    if not cid or pay is None:
        return
    try:
        row = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        if row is None:
            return
        cur = float(row.cart_value or 0.0)
        new_v = max(cur, float(pay))
        if new_v != cur or row.cart_value is None:
            row.cart_value = new_v
            db.session.commit()
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()


def _cart_total_for_vip_recovery(
    cart_id: Optional[str], payload: Optional[dict[str, Any]]
) -> Optional[float]:
    pl = payload if isinstance(payload, dict) else {}
    _persist_cart_value_from_abandon_for_vip(cart_id, pl)
    dbv = _abandoned_cart_cart_value_for_recovery(cart_id)
    payv = _cart_total_from_abandon_payload(pl)
    if dbv is not None and payv is not None:
        return max(dbv, payv)
    return dbv if dbv is not None else payv


def _vip_log_check(cart_total: Optional[float], threshold: Any, is_vip: bool) -> None:
    ct = "none" if cart_total is None else str(cart_total)
    th = "none" if threshold is None else str(threshold)
    vip_s = "true" if is_vip else "false"
    log.info("[VIP CHECK]\ncart_total=%s\nthreshold=%s\nis_vip=%s", ct, th, vip_s)


def _log_vip_cart_saved(ac: Optional[AbandonedCart]) -> None:
    """بعد حفظ صف ‎AbandonedCart‎ لمسار ‎VIP‎ (ويدجت / مزامنة)."""
    if ac is None:
        return
    cid = (str(getattr(ac, "zid_cart_id", "") or "").strip())
    sid_raw = getattr(ac, "store_id", None)
    sid_s = "none" if sid_raw is None else str(sid_raw)
    cv = getattr(ac, "cart_value", None)
    cv_s = "" if cv is None else str(cv)
    vm_s = str(bool(getattr(ac, "vip_mode", False))).lower()
    st = (str(ac.status or "").strip() or "—")[:50]
    log.info(
        "[VIP CART SAVED]\ncart_id=%s\nstore_id=%s\ncart_value=%s\nvip_mode=%s\nstatus=%s",
        cid,
        sid_s,
        cv_s,
        vm_s,
        st,
    )
    print(
        f"[VIP CART SAVED] cart_id={cid!r} store_id={sid_s} cart_value={cv_s} vip_mode={vm_s} status={st}"
    )


def _log_vip_cart_upsert(
    mode: str,
    *,
    cart_id: str,
    session_id: str,
    store_id: Optional[int],
) -> None:
    m = "created" if mode == "created" else "updated"
    cid = (cart_id or "").strip()[:255] or "-"
    sid = (session_id or "").strip()[:512] or "-"
    st_s = "none" if store_id is None else str(store_id)
    log.info("[VIP CART UPSERT]\nmode=%s\ncart_id=%s\nsession_id=%s\nstore_id=%s", m, cid, sid, st_s)
    print(f"[VIP CART UPSERT] mode={m} cart_id={cid} session_id={sid} store_id={st_s}")


def _normalize_customer_phone_for_wa_me(raw: Optional[str]) -> str:
    """أرقام فقط لـ ‎wa.me‎ (مثلاً ‎9665xxxxxxxx‎)."""
    if raw is None or not str(raw).strip():
        return ""
    d = "".join(c for c in str(raw) if c.isdigit())
    if not d:
        return ""
    if len(d) == 9 and d.startswith("5"):
        return "966" + d
    if len(d) == 10 and d.startswith("05"):
        return "966" + d[1:]
    if d.startswith("966") and len(d) >= 11:
        return d
    return d


def _vip_customer_contact_whatsapp_message(ac: AbandonedCart) -> str:
    cv = float(ac.cart_value or 0.0)
    if cv == int(cv):
        vs = str(int(cv))
    else:
        vs = f"{cv:.2f}".rstrip("0").rstrip(".")
    return (
        f"السلام عليكم، نتواصل معكم بخصوص سلة بقيمة {vs} ريال. "
        f"نود مساعدتكم في إتمام الطلب."
    )


def _send_vip_merchant_auto_alert(
    store_obj: Optional[Any],
    *,
    cart_total: float,
    cart_id: str,
    reason_tag: Optional[str] = None,
) -> None:
    """تنبيه واتساب للتاجر عند أول دخول السلة VIP — لا ينتظر الزر في لوحة الإعدادات."""
    try:
        phone, src = resolve_merchant_whatsapp_phone(store_obj)
        if not phone:
            log.info(
                "[VIP MERCHANT AUTO ALERT SKIPPED] reason=no_merchant_phone source=%s",
                src,
            )
            print("[VIP MERCHANT AUTO ALERT SKIPPED] reason=no_merchant_phone")
            return
        mbody = build_vip_merchant_alert_body(
            float(cart_total),
            reason_tag=reason_tag,
            dashboard_link=vip_dashboard_review_link(),
        )
        out = try_send_vip_merchant_whatsapp_alert(store_obj, message=mbody)
        sto_log = "none"
        if store_obj is not None and getattr(store_obj, "id", None) is not None:
            try:
                sto_log = str(int(store_obj.id))
            except (TypeError, ValueError):
                sto_log = "none"
        cid_log = (cart_id or "").strip()[:255] or "-"
        cv_log = str(cart_total)
        if isinstance(out, dict) and out.get("ok") is True:
            log.info(
                "[VIP MERCHANT AUTO ALERT SENT] cart_id=%s store_id=%s cart_total=%s",
                cid_log,
                sto_log,
                cv_log,
            )
            print(
                f"[VIP MERCHANT AUTO ALERT SENT] cart_id={cid_log} store_id={sto_log} cart_total={cv_log}"
            )
    except Exception as e:  # noqa: BLE001
        log.warning("VIP merchant auto alert failed (non-fatal): %s", e, exc_info=True)


def _vip_merchant_auto_alert_if_newly_entering(
    ac: AbandonedCart,
    store_for_alert: Optional[Any],
    store_slug: str,
    session_id: str,
    *,
    was_vip_before: bool,
) -> None:
    if was_vip_before:
        return
    if not bool(getattr(ac, "vip_mode", False)):
        return
    if str(getattr(ac, "status", "") or "").strip() != "abandoned":
        return
    rtag = _vip_reason_tag_from_abandoned_cart(ac)
    if not rtag:
        rtag = _reason_tag_for_session(store_slug, session_id)
    _send_vip_merchant_auto_alert(
        store_for_alert,
        cart_total=float(ac.cart_value or 0.0),
        cart_id=str(getattr(ac, "zid_cart_id", "") or ""),
        reason_tag=rtag,
    )


# مسار الويدجت الحقيقي (‎POST /api/cart-event‎)؛ خطوة ‎0‎ = طبقة ‎VIP‎ خارج ‎step 1‎–‎3‎ في ‎CartRecoveryLog‎.
VIP_WIDGET_ACTIVATION_SOURCE = "real_widget_cart_event"
VIP_WIDGET_RECOVERY_LOG_MESSAGE = "VIP cart detected from real widget flow"
VIP_WIDGET_RECOVERY_LOG_STEP = 0


def _try_send_vip_neutral_customer_recovery_whatsapp(
    *,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    store_obj: Optional[Any],
    recovery_key: str,
    abandon_event_phone: Optional[str],
    reason_tag: Optional[str],
) -> None:
    """رسالة عميل وحيدة لمسار VIP — خارج قوالب السعر والبدائل (محرّك القرار يفرض النص)."""
    try:
        vip_decision = decide_recovery_action(
            (reason_tag or "").strip() or None,
            store=store_obj,
            is_vip_cart_flag=True,
        )
        text = str(vip_decision.get("message") or "").strip()
        if not vip_decision.get("send_customer") or not text:
            return
        reason_row_v = _cart_recovery_reason_latest_row(store_slug, session_id)
        if reason_row_v is not None and _recovery_row_user_rejected_help(reason_row_v):
            return
        if _is_user_converted(recovery_key):
            return
        now = datetime.now(timezone.utc)
        last_act = _last_activity_utc_from_recovery_row(reason_row_v)
        last_eff = last_act if last_act is not None else now
        delay_minutes_f = float(_recovery_delay_minutes_from_store(store_obj))
        if not should_send_whatsapp(
            last_eff,
            user_returned_to_site=_is_user_returned(recovery_key),
            now=now,
            store=store_obj,
            sent_count=0,
        ):
            return
        phone, src, allowed = _resolve_cartflow_recovery_phone(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            store_obj=store_obj,
            abandon_event_phone=abandon_event_phone,
            recovery_key=recovery_key,
            reason_row=reason_row_v,
        )
        store_id_label = _recovery_store_id_label(store_obj, store_slug)
        _log_phone_resolution(
            store_id=store_id_label,
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            source=src,
            phone=phone,
            allowed_to_send=allowed,
        )
        if not phone or not allowed:
            return
        _assert_forbidden_stale_recovery_phone(phone)
        wa_result = send_whatsapp(
            phone,
            text,
            reason_tag="vip_neutral_followup",
            wa_trace_path=__file__,
            wa_trace_session_id=session_id,
            wa_trace_store_slug=store_slug,
            wa_trace_last_activity=last_eff,
            wa_trace_recovery_delay_minutes=delay_minutes_f,
            wa_trace_delay_passed=True,
        )
        wa_dict = wa_result if isinstance(wa_result, dict) else {}
        ok_flag = wa_dict.get("ok") is True
        st_out = str(wa_dict.get("status") or "").strip()[:50] or (
            "sent_real" if ok_flag else "whatsapp_failed"
        )
        if ok_flag:
            with _recovery_session_lock:
                sc = _session_recovery_send_count.get(recovery_key, 0)
                _session_recovery_send_count[recovery_key] = sc + 1
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=phone if ok_flag else None,
            message=text,
            status=st_out if ok_flag else "whatsapp_failed",
            step=1,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("VIP neutral customer WA (non-fatal): %s", exc, exc_info=True)


def _vip_recovery_decision_layer(
    reason_tag: Optional[str], store_obj: Optional[Any]
) -> dict[str, Any]:
    """استدعاء طبقة القرار مع ‎VIP‎ — نص عميل حيادي دون قوالب التردّد العادية."""
    return decide_recovery_action(
        (reason_tag or "").strip() or None,
        store=store_obj,
        is_vip_cart_flag=True,
    )


def _mark_vip_customer_recovery_closed(recovery_key: str) -> None:
    """يمنع أي جدولة أو إرسال مستقبل للعميل لهذه الجلسة بعد كشف VIP."""
    with _recovery_session_lock:
        _session_recovery_sent[recovery_key] = True


def _activate_vip_manual_cart_handling(
    *,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    cart_total: float,
    store_obj: Optional[Any],
    recovery_key: str,
    reason_tag: Optional[str],
    recovery_log_message: Optional[str] = None,
    recovery_log_step: Optional[int] = None,
    vip_activation_source: Optional[str] = None,
    abandon_event_phone: Optional[str] = None,
) -> bool:
    """
    تفعيل VIP: تعليم السلة، سجل لوحة، تنبيه تاجر، رسالة عميل حيادية (خارج قوالب السعر/البدائل)، ومنع مسار الاسترجاع الآلي العادي.
    آمن عند التكرار: لا يعيد التنبيه للتاجر إذا كانت ‎vip_mode‎ مفعّلة مسبقاً.
    يُرجع ‎False‎ عند فشل حرج (للسقوط إلى المسار العادي دون تعديل محرك القرار).
    """
    _ensure_store_widget_schema()
    cid = (str(cart_id).strip()[:255] if cart_id else "") or ""
    already = False
    try:
        if cid:
            ac = db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == cid).first()
            already = ac is not None and bool(getattr(ac, "vip_mode", False))
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        already = False

    now = datetime.now(timezone.utc)
    time_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    rt_disp = (reason_tag or "").strip() or "—"
    ar_map = {
        "price": "السعر",
        "warranty": "الضمان",
        "shipping": "الشحن",
        "thinking": "التفكير",
        "quality": "الجودة",
        "other": "سبب آخر",
        "human_support": "دعم بشري",
    }
    reason_ar = ar_map.get(rt_disp.lower(), rt_disp)
    if cart_total == int(cart_total):
        val_s = str(int(cart_total))
    else:
        val_s = f"{cart_total:.2f}".rstrip("0").rstrip(".")

    if already:
        log.info("[VIP CUSTOMER RECOVERY SKIPPED] reason=vip_manual_handling")
        if cid:
            try:
                ac_sync = db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == cid).first()
                if ac_sync is not None and str(ac_sync.status or "").strip() != "recovered":
                    ac_sync.status = "abandoned"
                    db.session.commit()
            except (SQLAlchemyError, OSError) as e:
                db.session.rollback()
                log.warning("[VIP SYNC STATUS] cart_id=%s err=%s", cid, e)
        with _recovery_session_lock:
            _session_recovery_sent[recovery_key] = True
        return True

    if vip_activation_source:
        log.info(
            "[VIP MODE ACTIVATED] source=%s session_id=%s cart_total=%s",
            vip_activation_source,
            session_id,
            cart_total,
        )
    else:
        log.info("[VIP MODE ACTIVATED] session_id=%s cart_total=%s", session_id, cart_total)
    try:
        if cid:
            ac2 = db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == cid).first()
            if ac2 is not None:
                ac2.vip_mode = True
                if str(ac2.status or "").strip() != "recovered":
                    ac2.status = "abandoned"
                db.session.commit()
                _log_vip_cart_saved(ac2)
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.exception("[VIP ACTIVATION FAILED] session_id=%s db_vip_mark err=%s", session_id, e)
        return False

    try:
        msg_full = "\n".join(
            [
                "سلة عالية القيمة تحتاج متابعة يدوية",
                f"القيمة: {val_s} ريال",
                f"سبب التردد: {reason_ar}",
                f"session_id: {session_id}",
                f"الوقت: {time_str}",
            ]
        )
        rtlm = (recovery_log_message or "").strip()
        if rtlm:
            msg_for_log = rtlm
            step_for_log = recovery_log_step
        else:
            msg_for_log = msg_full
            step_for_log = None
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=msg_for_log,
            status="vip_manual_handling",
            step=step_for_log,
        )
    except Exception as e:  # noqa: BLE001
        log.exception("[VIP ACTIVATION FAILED] session_id=%s persist_log err=%s", session_id, e)
        return False

    try:
        ac_send: Optional[AbandonedCart] = None
        if cid:
            ac_send = db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == cid).first()
        if ac_send is not None:
            store_alert = _resolve_store_for_vip_merchant_alert(ac_send)
            _vip_merchant_auto_alert_if_newly_entering(
                ac_send,
                store_alert,
                store_slug,
                session_id,
                was_vip_before=already,
            )
        else:
            rta = (reason_tag or "").strip() or None
            if not rta:
                rta = _reason_tag_for_session(store_slug, session_id)
            _send_vip_merchant_auto_alert(
                store_obj,
                cart_total=float(cart_total),
                cart_id=cid or "-",
                reason_tag=rta,
            )
    except Exception as e:  # noqa: BLE001
        log.warning("VIP merchant alert failed (non-fatal): %s", e, exc_info=True)

    try:
        _try_send_vip_neutral_customer_recovery_whatsapp(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cid or None,
            store_obj=store_obj,
            recovery_key=recovery_key,
            abandon_event_phone=abandon_event_phone,
            reason_tag=(reason_tag or "").strip() or None,
        )
    except Exception as exc2:  # noqa: BLE001
        log.warning("VIP neutral customer send error: %s", exc2, exc_info=True)

    log.info("[VIP ACTIVATION HANDOFF COMPLETE]")
    with _recovery_session_lock:
        _session_recovery_sent[recovery_key] = True
    return True


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


def _is_user_returned(recovery_key: str) -> bool:
    with _recovery_session_lock:
        return bool(_session_recovery_returned.get(recovery_key))


def _mark_user_returned_for_payload(payload: dict[str, Any]) -> None:
    key = _recovery_key_from_payload(payload)
    with _recovery_session_lock:
        _session_recovery_returned[key] = True
    log.info("user_returned_to_site recorded for recovery_key=%s", key)


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
        try:
            from services.cartflow_observability_runtime import (
                trace_recovery_lifecycle_from_log_status,
            )

            trace_recovery_lifecycle_from_log_status(
                status=status,
                session_id=session_id,
                cart_id=cart_id,
                store_slug=store_slug,
            )
        except Exception:
            pass
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


_VERIFIED_WA_RECOVERY_PHONE_SOURCES = frozenset(
    {"customer_profile", "abandoned_cart", "cf_test_phone"}
)

_NORMAL_RECOVERY_EXTENDED_PHONE_SOURCES = frozenset(
    {
        "abandoned_cart_zid",
        "cart_recovery_reason_session",
        "cart_recovery_reason_any_store",
        "cart_recovery_log_sent",
        "message_log_whatsapp",
        "abandoned_cart_session_peer",
    }
)

_FORBIDDEN_STALE_RECOVERY_E164 = "966501234567"


def _strip_recovery_phone(raw: Optional[Any]) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    return s[:100] if s else ""


def _vip_phone_from_abandoned_cart_raw_payload(ac: AbandonedCart) -> str:
    """استخراج جوال العميل من ‎AbandonedCart.raw_payload‎ فقط."""
    rp = getattr(ac, "raw_payload", None)
    if isinstance(rp, str) and rp.strip():
        try:
            d = json.loads(rp)
        except (json.JSONDecodeError, TypeError, ValueError):
            d = None
        if isinstance(d, dict):
            cust = d.get("customer") if isinstance(d.get("customer"), dict) else {}
            for key in ("phone", "mobile", "customer_phone"):
                v = d.get(key)
                if v is None and isinstance(cust, dict):
                    v = cust.get(key)
                got = _strip_recovery_phone(v)
                if got:
                    return got
    return ""


def _vip_store_slug_from_latest_cart_recovery_reason(session_id: str) -> str:
    """أحدث ‎store_slug‎ لصف ‎CartRecoveryReason‎ لهذه الجلسة (يملأ رقم العميل مفضلاً)."""
    sid = (session_id or "").strip()[:512]
    if not sid:
        return ""
    try:
        row = (
            db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.session_id == sid)
            .filter(CartRecoveryReason.customer_phone.isnot(None))
            .order_by(CartRecoveryReason.created_at.desc())
            .first()
        )
        if row is None:
            return ""
        return (getattr(row, "store_slug", None) or "").strip()[:255]
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return ""


def _vip_latest_crr_customer_phone_any_store_slug(session_id: str) -> str:
    """أحدث ‎customer_phone‎ لأي ‎store_slug‎ بنفس ‎session_id‎ (‎ORDER BY created_at DESC‎)."""
    sid = (session_id or "").strip()[:512]
    if not sid:
        return ""
    try:
        from schema_widget import (
            ensure_cart_recovery_reason_phone_schema,
            ensure_cart_recovery_reason_rejection_schema,
        )

        ensure_cart_recovery_reason_phone_schema(db)
        ensure_cart_recovery_reason_rejection_schema(db)
        db.create_all()
        rows = (
            db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.session_id == sid)
            .order_by(CartRecoveryReason.created_at.desc())
            .limit(32)
            .all()
        )
        for row in rows:
            p = _strip_recovery_phone(getattr(row, "customer_phone", None))
            if p:
                return p
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return ""
    return ""


def _vip_candidate_store_slugs_for_dashboard(
    dashboard_store: Optional[Any],
    ac: AbandonedCart,
) -> list[str]:
    """سلاسل ‎store_slug‎ المحتملة لمطابقة ‎CartRecoveryReason‎ وجلسة الذاكرة."""
    out: list[str] = []
    if dashboard_store is not None:
        zid = getattr(dashboard_store, "zid_store_id", None)
        if isinstance(zid, str) and zid.strip():
            zs = zid.strip()[:255]
            if zs:
                out.append(zs)
    sto_raw = getattr(ac, "store_id", None)
    if sto_raw is not None:
        try:
            st = db.session.get(Store, int(sto_raw))
            if st is not None:
                zz = getattr(st, "zid_store_id", None)
                if isinstance(zz, str) and zz.strip():
                    zs2 = zz.strip()[:255]
                    if zs2 and zs2 not in out:
                        out.append(zs2)
        except (SQLAlchemyError, TypeError, ValueError):
            db.session.rollback()
    return out


def _vip_latest_cart_recovery_reason_customer_phone(
    store_slug: str, session_id: str,
) -> str:
    """أحدث ‎customer_phone‎ غير فارغ في ‎CartRecoveryReason‎ لنفس ‎store_slug‎ و‎session_id‎."""
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    if not ss or not sid:
        return ""
    try:
        from schema_widget import (
            ensure_cart_recovery_reason_phone_schema,
            ensure_cart_recovery_reason_rejection_schema,
        )

        ensure_cart_recovery_reason_phone_schema(db)
        ensure_cart_recovery_reason_rejection_schema(db)
        db.create_all()
        rows = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == ss,
                CartRecoveryReason.session_id == sid,
            )
            .order_by(
                CartRecoveryReason.created_at.desc(),
                CartRecoveryReason.updated_at.desc(),
            )
            .limit(32)
            .all()
        )
        for row in rows:
            p = _strip_recovery_phone(getattr(row, "customer_phone", None))
            if p:
                return p
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return ""
    return ""


def _vip_dashboard_customer_phone_raw(
    ac: AbandonedCart,
    dashboard_store: Optional[Any],
    *,
    prefer_persisted_cart_column_before_memory: bool = False,
) -> str:
    """
    جوال عميل لوحة VIP: ‎CartRecoveryReason‎ (سلاسل ‎slug‎ للوحة ومن آخر سبب للجلسة)،
    ذاكرة الجلسة، ‎AbandonedCart.customer_phone‎، ثم ‎CartRecoveryReason‎ لأي ‎slug‎ بنفس الجلسة، ثم ‎raw_payload‎.
    عند ‎prefer_persisted_cart_column_before_memory‎ (بطاقات الاسترجاع العادي): عمود السلة قبل ذاكرة الجلسة المؤقتة.
    """
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    slugs = list(_vip_candidate_store_slugs_for_dashboard(dashboard_store, ac))
    if sid:
        extra_slug = _vip_store_slug_from_latest_cart_recovery_reason(sid)
        if extra_slug and extra_slug not in slugs:
            slugs.insert(0, extra_slug)

    if sid and slugs:
        for ss in slugs:
            got_crr = _vip_latest_cart_recovery_reason_customer_phone(ss, sid)
            if got_crr:
                return got_crr
        if prefer_persisted_cart_column_before_memory:
            col_early = _strip_recovery_phone(getattr(ac, "customer_phone", None))
            if col_early:
                return col_early
        try:
            from services.recovery_session_phone import get_recovery_customer_phone

            for ss in slugs:
                rk = _recovery_key_from_store_and_session(ss, sid)
                got_mem = _strip_recovery_phone(get_recovery_customer_phone(rk))
                if got_mem:
                    return got_mem
        except Exception:  # noqa: BLE001
            pass

    col = _strip_recovery_phone(getattr(ac, "customer_phone", None))
    if col:
        return col

    if sid:
        got_any = _vip_latest_crr_customer_phone_any_store_slug(sid)
        if got_any:
            return got_any

    slug0 = slugs[0] if slugs else ""
    if not slug0 and dashboard_store is not None:
        slug0 = (getattr(dashboard_store, "zid_store_id", None) or "").strip()[:255]
    if not slug0:
        slug0 = "demo"
    zid_ac = (getattr(ac, "zid_cart_id", None) or "").strip() or None
    ext_p, _ext_s = _normal_recovery_extended_phone_lookup(
        store_slug=slug0,
        session_id=sid,
        cart_id=zid_ac,
        store_obj=dashboard_store if isinstance(dashboard_store, Store) else None,
        emit_log=False,
    )
    if ext_p:
        return _strip_recovery_phone(ext_p)

    return _vip_phone_from_abandoned_cart_raw_payload(ac)


def _recovery_digits_normalized_sa(raw: str) -> str:
    """توحيد أشكال جوال سعودي شائعة لاكتشاف الرقم المحظور القديم."""
    d = "".join(c for c in (raw or "") if c.isdigit())
    if not d:
        return ""
    while d.startswith("00"):
        d = d[2:]
    if len(d) == 10 and d.startswith("0"):
        return "966" + d[1:]
    if len(d) == 9 and d.startswith("5"):
        return "966" + d
    return d


def _cartflow_demo_test_phone() -> str:
    raw = (os.getenv("CARTFLOW_DEMO_TEST_PHONE") or "").strip()
    return (raw if raw else "966579706669")[:100]


def _is_demo_store_slug(store_slug: str) -> bool:
    return (store_slug or "").strip().lower() == "demo"


def _recovery_store_id_label(store_obj: Optional[Any], store_slug: str) -> str:
    if store_obj is not None:
        zid = getattr(store_obj, "zid_store_id", None)
        if isinstance(zid, str) and zid.strip():
            return zid.strip()[:255]
        sid = getattr(store_obj, "id", None)
        if sid is not None:
            return str(sid)
    return (store_slug or "").strip() or ""


def _map_verified_recovery_phone_from_session(
    *,
    abandon_event_phone: Optional[str],
    recovery_key: str,
    reason_row: Optional[CartRecoveryReason],
) -> Tuple[Optional[str], str]:
    from services.recovery_session_phone import (
        get_recovery_customer_phone,
        get_recovery_phone_resolution_source,
    )

    ep = _strip_recovery_phone(abandon_event_phone)
    if ep:
        return ep, "abandoned_cart"
    mem = _strip_recovery_phone(get_recovery_customer_phone(recovery_key))
    if mem:
        return mem, get_recovery_phone_resolution_source(recovery_key)
    if reason_row is not None:
        dbp = _strip_recovery_phone(getattr(reason_row, "customer_phone", None))
        if dbp:
            return dbp, "customer_profile"
    return None, "none"


def _abandoned_cart_db_ids_for_recovery_scope(
    session_id: str, cart_zid: Optional[str]
) -> list[int]:
    """معرّفات ‎AbandonedCart‎ المرتبطة بجلسة أو ‎cart zid‎ (لـ ‎MessageLog‎)."""
    sid = (session_id or "").strip()[:512]
    cz = (cart_zid or "").strip()[:255]
    if not sid and not cz:
        return []
    try:
        db.create_all()
        conds: list[Any] = []
        if sid:
            conds.append(AbandonedCart.recovery_session_id == sid)
        if cz:
            conds.append(AbandonedCart.zid_cart_id == cz)
        rows = db.session.query(AbandonedCart.id).filter(or_(*conds)).limit(48).all()
        out: list[int] = []
        for r in rows:
            if r.id is not None and int(r.id) not in out:
                out.append(int(r.id))
        return out
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return []


def _log_normal_recovery_phone_resolution(
    tag: str, source: str, customer_phone: str
) -> None:
    cp = (customer_phone or "").strip()[:100]
    sp = (source or "").strip()[:80]
    try:
        line = f"{tag} source={sp} customer_phone={cp}"
        log.info(line)
        print(line, flush=True)
    except OSError:
        pass


def _log_normal_recovery_phone_missing_customer(
    session_id: str, cart_id: Optional[str]
) -> None:
    sid = (session_id or "").strip() or "-"
    cid = ((cart_id or "").strip()[:255] or "-") if cart_id else "-"
    try:
        line = (
            "[NORMAL RECOVERY PHONE MISSING] reason=missing_customer_phone "
            f"session_id={sid} cart_id={cid}"
        )
        log.info(line)
        print(line, flush=True)
    except OSError:
        pass


def _normal_recovery_merchant_normalized_digits(store_obj: Optional[Any]) -> frozenset[str]:
    """قيم ‎E.164‎ المجرّدة للأرقام التي تُعد ‎merchant/sender‎ — ممنوع إرسال استرجاع عميل إليها."""
    out: set[str] = set()

    def _add_raw(raw: Optional[Any]) -> None:
        p = _strip_recovery_phone(str(raw) if raw is not None else "")
        if not p:
            return
        d = _recovery_digits_normalized_sa(p)
        if d and len(d) >= 8:
            out.add(d)

    try:
        if store_obj is not None:
            mp, _ = resolve_merchant_whatsapp_phone_with_default_env(store_obj)
            _add_raw(mp)
            mp2, _ = resolve_merchant_whatsapp_phone(store_obj)
            _add_raw(mp2)
        env_m = (os.getenv("DEFAULT_MERCHANT_PHONE") or "").strip()
        _add_raw(env_m)
        tw = (os.getenv("TWILIO_WHATSAPP_FROM") or "").strip()
        if tw:
            if tw.lower().startswith("whatsapp:"):
                tw = tw.split(":", 1)[-1].strip()
            _add_raw(tw)
        demo_env = (os.getenv("CARTFLOW_DEMO_TEST_PHONE") or "").strip()
        if demo_env:
            _add_raw(demo_env)
        else:
            _add_raw("966579706669")
    except (TypeError, ValueError, OSError):
        pass
    return frozenset(out)


def _normal_recovery_phone_normalized_equals_merchant(
    phone: Optional[str], merchant_digits: frozenset[str]
) -> bool:
    if not phone or not merchant_digits:
        return False
    d = _recovery_digits_normalized_sa(_strip_recovery_phone(phone))
    return bool(d) and d in merchant_digits


def _log_normal_recovery_blocked_merchant_match(
    session_id: str, cart_id: Optional[str]
) -> None:
    sid = (session_id or "").strip() or "-"
    cid = ((cart_id or "").strip()[:255] or "-") if cart_id else "-"
    try:
        line = (
            "[NORMAL RECOVERY BLOCKED] reason=customer_phone_equals_merchant_phone "
            f"session_id={sid} cart_id={cid}"
        )
        log.info(line)
        print(line, flush=True)
    except OSError:
        pass


def _normal_recovery_dashboard_resolve_customer_phone_raw(
    ac: AbandonedCart,
    dash_store: Optional[Store],
) -> str:
    """رقم عميل للعرض فقط — مصادر مسموحة كما في ‎_resolve_cartflow_recovery_phone‎ دون رقم التاجر."""
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    zid = (getattr(ac, "zid_cart_id", None) or "").strip() or None
    if not sid:
        return ""
    slug = _store_slug_for_cart_recovery_reason(ac)
    if not slug:
        z = getattr(dash_store, "zid_store_id", None) if dash_store is not None else None
        slug = (str(z).strip()[:255] if z and str(z).strip() else "") or "demo"
    rk = _recovery_key_from_store_and_session(slug, sid)
    reason_row = _cart_recovery_reason_latest_row(slug, sid)
    col_phone = _strip_recovery_phone(getattr(ac, "customer_phone", None)) or None
    phone, _src, ok = _resolve_cartflow_recovery_phone(
        store_slug=slug,
        session_id=sid,
        cart_id=zid,
        store_obj=dash_store,
        abandon_event_phone=col_phone,
        recovery_key=rk,
        reason_row=reason_row,
    )
    if not ok or not phone:
        return ""
    return phone.strip()


def _normal_recovery_extended_phone_lookup(
    *,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    store_obj: Optional[Any],
    emit_log: bool = True,
) -> tuple[Optional[str], str]:
    """
    مصادر إضافية لرقم العميل بعد فشل خريطة الجلسة السريعة (محاولات لاحقة، لوحة، إلخ).
    الترتيب: سلّة حالية، ‎CartRecoveryReason‎، سجل إرسال ناجح، ‎MessageLog‎، سلال بنفس الجلسة.
    """
    sid = (session_id or "").strip()[:512]
    cz = (cart_id or "").strip()[:255]
    ss = (store_slug or "").strip()[:255] or "demo"
    merchant_digits = _normal_recovery_merchant_normalized_digits(store_obj)

    def _hit(ph: Optional[str], src: str) -> tuple[Optional[str], str]:
        got = _strip_recovery_phone(ph)
        if not got:
            return None, "none"
        if _normal_recovery_phone_normalized_equals_merchant(got, merchant_digits):
            return None, "none"
        if emit_log:
            _log_normal_recovery_phone_resolution(
                "[NORMAL RECOVERY PHONE RESOLVED]", src, got
            )
        return got, src

    try:
        db.create_all()
        if cz:
            ac_z = (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.zid_cart_id == cz)
                .first()
            )
            if ac_z is not None:
                out = _hit(getattr(ac_z, "customer_phone", None), "abandoned_cart_zid")
                if out[0]:
                    return out

        if sid and ss:
            crr_sl = _vip_latest_cart_recovery_reason_customer_phone(ss, sid)
            out = _hit(crr_sl, "cart_recovery_reason_session")
            if out[0]:
                return out

        if sid:
            crr_any = _vip_latest_crr_customer_phone_any_store_slug(sid)
            out = _hit(crr_any, "cart_recovery_reason_any_store")
            if out[0]:
                return out

        log_conds: list[Any] = []
        if sid:
            log_conds.append(CartRecoveryLog.session_id == sid)
        if cz:
            log_conds.append(CartRecoveryLog.cart_id == cz)
        if log_conds:
            cr_row = (
                db.session.query(CartRecoveryLog)
                .filter(or_(*log_conds))
                .filter(CartRecoveryLog.status.in_(_NORMAL_RECOVERY_SENT_LOG_STATUSES))
                .filter(CartRecoveryLog.phone.isnot(None))
                .filter(CartRecoveryLog.phone != "")
                .order_by(
                    CartRecoveryLog.sent_at.desc().nullslast(),
                    CartRecoveryLog.id.desc(),
                )
                .first()
            )
            if cr_row is not None:
                out = _hit(getattr(cr_row, "phone", None), "cart_recovery_log_sent")
                if out[0]:
                    return out

        ac_ids = _abandoned_cart_db_ids_for_recovery_scope(sid, cz if cz else None)
        if ac_ids:
            qml = db.session.query(MessageLog).filter(
                MessageLog.abandoned_cart_id.in_(ac_ids),
                MessageLog.channel == "whatsapp",
                MessageLog.phone != "",
            )
            st_id = getattr(store_obj, "id", None)
            if st_id is not None:
                try:
                    qml = qml.filter(MessageLog.store_id == int(st_id))
                except (TypeError, ValueError):
                    pass
            ml_row = qml.order_by(MessageLog.created_at.desc()).first()
            if ml_row is not None:
                out = _hit(getattr(ml_row, "phone", None), "message_log_whatsapp")
                if out[0]:
                    return out

        if sid:
            pq = db.session.query(AbandonedCart).filter(
                AbandonedCart.recovery_session_id == sid
            )
            st_id = getattr(store_obj, "id", None)
            if st_id is not None:
                vid = int(st_id)
                pq = pq.filter(
                    (AbandonedCart.store_id == vid) | (AbandonedCart.store_id.is_(None))
                )
            peers = pq.limit(48).all()
            for peer in peers:
                out = _hit(getattr(peer, "customer_phone", None), "abandoned_cart_session_peer")
                if out[0]:
                    return out
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()

    return None, "none"


def _resolve_cartflow_recovery_phone(
    *,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    store_obj: Optional[Store],
    abandon_event_phone: Optional[str],
    recovery_key: str,
    reason_row: Optional[CartRecoveryReason],
) -> Tuple[Optional[str], str, bool]:
    """رقم ‎العميل‎ فقط لواتساب الاسترجاع العادي — دون رقم التاجر أو مرسل ‎Twilio‎."""
    merchant_digits = _normal_recovery_merchant_normalized_digits(store_obj)
    phone, source = _map_verified_recovery_phone_from_session(
        abandon_event_phone=abandon_event_phone,
        recovery_key=recovery_key,
        reason_row=reason_row,
    )
    if phone and _normal_recovery_phone_normalized_equals_merchant(phone, merchant_digits):
        phone, source = None, "none"

    if phone is None:
        ext_p, ext_s = _normal_recovery_extended_phone_lookup(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            store_obj=store_obj,
            emit_log=True,
        )
        if ext_p:
            phone, source = ext_p, ext_s

    if phone and _normal_recovery_phone_normalized_equals_merchant(phone, merchant_digits):
        phone, source = None, "none"

    if not phone:
        _log_normal_recovery_phone_missing_customer(session_id, cart_id)
        return None, "none", False

    allowed = bool(
        source in (
            _VERIFIED_WA_RECOVERY_PHONE_SOURCES | _NORMAL_RECOVERY_EXTENDED_PHONE_SOURCES
        )
    )
    return phone, source, allowed


def _log_phone_resolution(
    *,
    store_id: str,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    source: str,
    phone: Optional[str],
    allowed_to_send: bool,
) -> None:
    print("[PHONE RESOLUTION]")
    print("store_id=", store_id)
    print("store=", store_slug)
    print("session_id=", session_id)
    print("cart_id=", cart_id if cart_id is not None else "")
    print("source=", source)
    print("phone=", phone if phone else "")
    print("allowed_to_send=", allowed_to_send)


def _assert_forbidden_stale_recovery_phone(phone: str) -> None:
    if phone == _FORBIDDEN_STALE_RECOVERY_E164:
        raise RuntimeError("Forbidden stale test phone")
    norm_p = _recovery_digits_normalized_sa(phone)
    norm_f = _recovery_digits_normalized_sa(_FORBIDDEN_STALE_RECOVERY_E164)
    if norm_p and norm_f and norm_p == norm_f:
        raise RuntimeError("Forbidden stale test phone")


def resolve_whatsapp_sender(store: Any) -> str:
    """يحسم وضع مرسل واتساب مستقبلياً بدون تغيير مسار الإرسال الحالي."""
    raw = getattr(store, "store_whatsapp_number", None) if store is not None else None
    mode = "store_number_future" if isinstance(raw, str) and raw.strip() else "twilio_default"
    log.info("[WA SENDER MODE] mode=%s", mode)
    return mode


async def _run_recovery_sequence_after_cart_abandoned_impl(
    recovery_key: str,
    delay_seconds: float,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    abandon_event_phone: Optional[str] = None,
    *,
    multi_slot_index: Optional[int] = None,
    multi_message_text: Optional[str] = None,
    sequential_attempt_index: Optional[int] = None,
) -> None:
    """
    ينتظر ‎delay_seconds‎ ثم يطبّق ‎should_send_whatsapp‎ على آخر نشاط السبب؛ عند السماح فقط يرسل عبر ‎send_whatsapp‎.
    نص الرسالة من محرّك القراءة حسب ‎reason_tag‎ المحفوظ، أو رسالة احتياطية.
    """
    store_pre = _load_store_row_for_recovery(store_slug)
    cart_total_pre = _abandoned_cart_cart_value_for_recovery(cart_id)
    if cart_total_pre is not None and is_vip_cart(cart_total_pre, store_pre):
        reason_row_pre = _cart_recovery_reason_latest_row(store_slug, session_id)
        rt_pre = (reason_row_pre.reason or "").strip() if reason_row_pre else ""
        _vip_recovery_decision_layer(rt_pre or None, store_pre)
        ok_vip = _activate_vip_manual_cart_handling(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            cart_total=float(cart_total_pre),
            store_obj=store_pre,
            recovery_key=recovery_key,
            reason_tag=rt_pre or None,
            abandon_event_phone=abandon_event_phone,
        )
        if not ok_vip:
            log.warning(
                "[VIP ACTIVATION FAILED] session_id=%s recovery_key=%s — pre_delay_task_blocked",
                session_id,
                recovery_key,
            )
        _mark_vip_customer_recovery_closed(recovery_key)
        return

    scheduled_recovery_delay_minutes = delay_seconds / 60.0
    print("[DELAY STARTED]", scheduled_recovery_delay_minutes)
    print("[DELAY WAITING]")
    try:
        await asyncio.sleep(delay_seconds)
    except asyncio.CancelledError:
        raise
    print("[DELAY FINISHED]")
    seq_attempt = sequential_attempt_index
    step_num = (
        int(seq_attempt)
        if seq_attempt is not None
        else (int(multi_slot_index) if multi_slot_index is not None else 1)
    )
    if step_num > 1:
        _log_second_recovery_line(
            "[SECOND RECOVERY DELAY PASSED]",
            session_id=(session_id or "").strip(),
            cart_id=(cart_id or "").strip(),
            scheduled_step=str(step_num),
            recovery_key=recovery_key,
        )
    seq_done_key: Optional[str] = None
    if multi_slot_index is not None:
        slot_sk = f"{recovery_key}:multi:{multi_slot_index}"
        with _recovery_session_lock:
            if _session_recovery_multi_logged.get(slot_sk):
                from services.cartflow_duplicate_guard import (
                    note_sequential_recovery_slot_duplicate,
                )

                note_sequential_recovery_slot_duplicate(
                    recovery_key=recovery_key,
                    slot_kind="multi_slot",
                    slot_detail=str(multi_slot_index),
                )
                return
            _session_recovery_multi_logged[slot_sk] = True
    elif seq_attempt is not None and int(seq_attempt) > 1:
        seq_done_key = f"{recovery_key}:seq:{int(seq_attempt)}"
        if _cart_recovery_log_has_successful_send_for_step(
            session_id, cart_id, int(seq_attempt)
        ):
            from services.cartflow_duplicate_guard import note_send_duplicate_blocked

            note_send_duplicate_blocked(
                store_slug=store_slug,
                session_id=session_id,
                cart_id=cart_id or "",
                attempt_index=int(seq_attempt),
                reason="sequential_already_sent_log",
                recovery_key=recovery_key,
            )
            _log_second_recovery_skipped(
                reason="already_sent",
                recovery_key=recovery_key,
                session_id=session_id,
                cart_id=cart_id or "",
            )
            return
        with _recovery_session_lock:
            if _session_recovery_seq_logged.get(seq_done_key):
                from services.cartflow_duplicate_guard import (
                    note_sequential_recovery_slot_duplicate,
                )

                note_sequential_recovery_slot_duplicate(
                    recovery_key=recovery_key,
                    slot_kind="sequential_step",
                    slot_detail=str(seq_done_key),
                )
                _log_second_recovery_skipped(
                    reason="already_sent",
                    recovery_key=recovery_key,
                    session_id=session_id,
                    cart_id=cart_id or "",
                )
                return
    else:
        with _recovery_session_lock:
            if _session_recovery_logged.get(recovery_key):
                from services.cartflow_duplicate_guard import (
                    note_sequential_recovery_slot_duplicate,
                )

                note_sequential_recovery_slot_duplicate(
                    recovery_key=recovery_key,
                    slot_kind="single_session_delay",
                    slot_detail="recovery_dispatch_duplicate",
                )
                return
            _session_recovery_logged[recovery_key] = True
    seq_follow = (
        multi_slot_index is None
        and seq_attempt is not None
        and int(seq_attempt) > 1
    )
    if multi_slot_index is None and not (
        seq_attempt is not None and int(seq_attempt) > 1
    ):
        print("recovery triggered after delay (single message, decision engine)")
    elif seq_attempt is not None and int(seq_attempt) > 1:
        print(
            "recovery triggered after delay (sequential follow-up step=%s)"
            % int(seq_attempt)
        )

    def _consume_seq_slot_if_needed() -> None:
        if seq_done_key is None:
            return
        with _recovery_session_lock:
            _session_recovery_seq_logged[seq_done_key] = True

    def _seq2_skip(reason: str, *, gate_detail: str = "", **kw: Any) -> None:
        _maybe_log_second_recovery_stopped(
            seq_attempt,
            scheduled_step=step_num,
            reason=reason,
            recovery_key=recovery_key,
            gate_detail=gate_detail,
            **kw,
        )

    if step_num >= 2 and _normal_recovery_positive_reply_blocks_followup(
        session_id=session_id, cart_id=cart_id
    ):
        try:
            print("[RECOVERY AUTOMATION STOPPED] reason=customer_replied", flush=True)
            log.info(
                "[RECOVERY AUTOMATION STOPPED] reason=customer_replied session_id=%s step=%s",
                session_id,
                step_num,
            )
        except OSError:
            pass
        skip_early = _default_recovery_message()
        _seq2_skip("customer_replied", session_id=session_id)
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=skip_early,
            status="skipped_followup_customer_replied",
            step=step_num,
        )
        print("[RECOVERY TASK EXIT CLEANLY]")
        print("reason=customer_replied_followup_suppressed")
        _consume_seq_slot_if_needed()
        return

    effective_abandon_phone = abandon_event_phone
    if seq_follow or step_num > 1:
        if not (effective_abandon_phone and str(effective_abandon_phone).strip()):
            lp = _last_sent_phone_from_recovery_logs(session_id, cart_id)
            if lp:
                effective_abandon_phone = lp
            else:
                try:
                    from services.recovery_session_phone import (
                        get_recovery_customer_phone,
                    )

                    mp = _strip_recovery_phone(get_recovery_customer_phone(recovery_key))
                    if mp:
                        effective_abandon_phone = mp
                except Exception:  # noqa: BLE001
                    pass
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
            step=step_num,
        )
        _seq2_skip("purchase_completed", session_id=session_id)
        _consume_seq_slot_if_needed()
        return

    reason_row = _cart_recovery_reason_latest_row(store_slug, session_id)
    if _recovery_row_user_rejected_help(reason_row):
        print("[SKIP WA - USER REJECTED HELP]")
        skip_msg = _default_recovery_message()
        _seq2_skip("user_rejected_help", session_id=session_id)
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=skip_msg,
            status="skipped_user_rejected_help",
            step=step_num,
        )
        print("[RECOVERY TASK EXIT CLEANLY]")
        print("reason=user_rejected_help")
        _consume_seq_slot_if_needed()
        return None
    rt_raw = (reason_row.reason or "").strip() if reason_row else ""
    store_obj = _load_store_row_for_recovery(store_slug)
    cart_total_vip = _abandoned_cart_cart_value_for_recovery(cart_id)
    th_raw = getattr(store_obj, "vip_cart_threshold", None) if store_obj is not None else None
    is_vip_eff = cart_total_vip is not None and is_vip_cart(cart_total_vip, store_obj)
    _vip_log_check(cart_total_vip, th_raw, is_vip_eff)
    if is_vip_eff:
        _vip_recovery_decision_layer(rt_raw or None, store_obj)
        ok_vip2 = _activate_vip_manual_cart_handling(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            cart_total=float(cart_total_vip),
            store_obj=store_obj,
            recovery_key=recovery_key,
            reason_tag=rt_raw or None,
            abandon_event_phone=abandon_event_phone,
        )
        if not ok_vip2:
            log.warning(
                "[VIP ACTIVATION FAILED] session_id=%s recovery_key=%s — post_delay_blocked_no_customer_send",
                session_id,
                recovery_key,
            )
        _mark_vip_customer_recovery_closed(recovery_key)
        _consume_seq_slot_if_needed()
        return None
    if seq_follow or step_num > 1:
        if _normal_recovery_positive_reply_blocks_followup(
            session_id=session_id, cart_id=cart_id
        ):
            _seq2_skip("customer_positive_reply", session_id=session_id)
            skip_msg = _default_recovery_message()
            _persist_cart_recovery_log(
                store_slug=store_slug,
                session_id=session_id,
                cart_id=cart_id,
                phone=None,
                message=skip_msg,
                status="skipped_followup_customer_replied",
                step=step_num,
            )
            print("[RECOVERY TASK EXIT CLEANLY]")
            print("reason=followup_blocked_customer_replied")
            _consume_seq_slot_if_needed()
            return None
    resolve_whatsapp_sender(store_obj)
    if step_num > 1:
        _log_second_recovery_line(
            "[SECOND RECOVERY START]",
            session_id=session_id,
            recovery_key=recovery_key,
            scheduled_step=str(step_num),
        )
    if multi_slot_index is not None:
        if not rt_raw:
            reason_tag = None
            text = _DEFAULT_DECISION_FALLBACK_MESSAGE
            _persist_cart_recovery_log(
                store_slug=store_slug,
                session_id=session_id,
                cart_id=cart_id,
                phone=None,
                message=text,
                status="skipped_missing_reason_tag",
                step=step_num,
            )
            return None
        reason_tag = rt_raw
        if reason_template_blocks_recovery_whatsapp(reason_tag, store_obj):
            skip_tpl_msg = _default_recovery_message()
            _persist_cart_recovery_log(
                store_slug=store_slug,
                session_id=session_id,
                cart_id=cart_id,
                phone=None,
                message=skip_tpl_msg,
                status="skipped_reason_template_disabled",
                step=step_num,
            )
            print("[RECOVERY TASK EXIT CLEANLY]")
            print("reason=reason_template_disabled")
            return None
        text = (multi_message_text or "").strip()
        if not text:
            text = get_recovery_message(reason_tag, int(step_num), store_obj)
    elif seq_follow:
        if not rt_raw:
            reason_tag = None
            text = _DEFAULT_DECISION_FALLBACK_MESSAGE
            _persist_cart_recovery_log(
                store_slug=store_slug,
                session_id=session_id,
                cart_id=cart_id,
                phone=None,
                message=text,
                status="skipped_missing_reason_tag",
                step=step_num,
            )
            _seq2_skip(
                "missing_reason_tag",
                session_id=session_id,
            )
            _consume_seq_slot_if_needed()
            return None
        reason_tag = rt_raw
        if reason_template_blocks_recovery_whatsapp(reason_tag, store_obj):
            skip_tpl_msg = _default_recovery_message()
            _persist_cart_recovery_log(
                store_slug=store_slug,
                session_id=session_id,
                cart_id=cart_id,
                phone=None,
                message=skip_tpl_msg,
                status="skipped_reason_template_disabled",
                step=step_num,
            )
            _seq2_skip(
                "reason_template_disabled",
                session_id=session_id,
            )
            print("[RECOVERY TASK EXIT CLEANLY]")
            print("reason=reason_template_disabled")
            _consume_seq_slot_if_needed()
            return None
        text = (multi_message_text or "").strip()
        if not text:
            text = get_recovery_message(reason_tag, int(step_num), store_obj)
    elif rt_raw:
        reason_tag = rt_raw
        if reason_template_blocks_recovery_whatsapp(reason_tag, store_obj):
            skip_tpl_msg = _default_recovery_message()
            _persist_cart_recovery_log(
                store_slug=store_slug,
                session_id=session_id,
                cart_id=cart_id,
                phone=None,
                message=skip_tpl_msg,
                status="skipped_reason_template_disabled",
                step=step_num,
            )
            print("[RECOVERY TASK EXIT CLEANLY]")
            print("reason=reason_template_disabled")
            return None
        text = resolve_recovery_whatsapp_message_with_reason_templates(
            reason_tag, store=store_obj
        )
    else:
        reason_tag = None
        text = _DEFAULT_DECISION_FALLBACK_MESSAGE

    configured_message_count = _normal_recovery_configured_message_count_from_runtime(
        recovery_key, store_obj
    )
    with _recovery_session_lock:
        gate_sent_count = _session_recovery_send_count.get(recovery_key, 0)
    _log_normal_recovery_sequence_config(
        configured_message_count=configured_message_count,
        sent_count=gate_sent_count,
        attempt_index=step_num,
        recovery_key=recovery_key,
    )

    if _cart_recovery_log_has_successful_send_for_step(session_id, cart_id, step_num):
        from services.cartflow_duplicate_guard import note_send_duplicate_blocked

        note_send_duplicate_blocked(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id or "",
            attempt_index=step_num,
            reason="already_sent_log",
            recovery_key=recovery_key,
        )
        _log_normal_recovery_attempt_decision(
            attempt_index=step_num,
            allowed=False,
            reason="already_sent",
        )
        _log_normal_recovery_attempt_skipped(
            attempt_index=step_num,
            reason="already_sent",
        )
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status="skipped_duplicate",
            step=step_num,
        )
        _consume_seq_slot_if_needed()
        return None

    if step_num > configured_message_count or gate_sent_count >= configured_message_count:
        _log_normal_recovery_attempt_decision(
            attempt_index=step_num,
            allowed=False,
            reason="sequence_completed",
        )
        _log_normal_recovery_attempt_skipped(
            attempt_index=step_num,
            reason="sequence_completed",
        )
        _seq2_skip("attempt_limit", session_id=session_id)
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status="skipped_attempt_limit",
            step=step_num,
        )
        _consume_seq_slot_if_needed()
        return None

    last_activity = _last_activity_utc_from_recovery_row(reason_row)
    now = datetime.now(timezone.utc)
    delay_minutes = _recovery_delay_minutes_from_store(store_obj)
    delay_gate_activity = (
        None
        if multi_slot_index is not None
        or seq_follow
        or step_num > 1
        else last_activity
    )
    should_send = should_send_whatsapp(
        delay_gate_activity,
        user_returned_to_site=_is_user_returned(recovery_key),
        now=now,
        store=store_obj,
        sent_count=gate_sent_count,
        configured_message_count=configured_message_count,
    )
    if should_send:
        _log_normal_recovery_attempt_decision(
            attempt_index=step_num, allowed=True, reason="allowed"
        )
        _ds_tag = "allowed"
    else:
        _, _ds_tag = _second_recovery_diagnose_should_send(
            delay_gate_activity,
            user_returned_to_site=_is_user_returned(recovery_key),
            now=now,
            store=store_obj,
            sent_count=gate_sent_count,
            configured_message_count=configured_message_count,
        )
        _log_normal_recovery_attempt_decision(
            attempt_index=step_num, allowed=False, reason=_ds_tag
        )
    print("[CARTFLOW DELAY CHECK]")
    print("reason_tag=", reason_tag)
    print("last_activity=", last_activity)
    print("now=", now)
    print("delay_minutes=", delay_minutes)
    print("should_send=", should_send)

    if not should_send:
        print("[DELAY BLOCKED] skipping send")
        nr_skip_reason = _ds_tag
        if _ds_tag == "max_attempts_reached":
            nr_skip_reason = "sequence_completed"
        elif _ds_tag == "delay_not_elapsed":
            nr_skip_reason = "automation_disabled"
        elif _ds_tag == "user_returned":
            nr_skip_reason = "user_returned"
        elif _ds_tag == "automation_disabled":
            nr_skip_reason = "automation_disabled"
        _log_normal_recovery_attempt_skipped(
            attempt_index=step_num,
            reason=nr_skip_reason,
        )
        try:
            max_a_chk = max(0, int(configured_message_count))
        except (TypeError, ValueError):
            max_a_chk = 1
        crep_ds = False
        if seq_follow or step_num > 1:
            crep_ds = _normal_recovery_positive_reply_blocks_followup(
                session_id=session_id, cart_id=cart_id
            )
        if step_num > 1:
            rt_chk = (reason_tag or "") if reason_tag else ""
            _log_second_recovery_check(
                session_id=session_id,
                cart_id=cart_id,
                sent_count=int(gate_sent_count),
                max_attempts=max_a_chk,
                customer_phone="",
                reason_tag=rt_chk,
                purchase_completed=_is_user_converted(recovery_key),
                user_returned_to_site=_is_user_returned(recovery_key),
                customer_replied=crep_ds,
                allowed=False,
            )
        _seq2_skip(_ds_tag, session_id=session_id)
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status="skipped_delay_gate",
            step=step_num,
        )
        _consume_seq_slot_if_needed()
        return

    phone, phone_source, allowed_to_send = _resolve_cartflow_recovery_phone(
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        store_obj=store_obj,
        abandon_event_phone=effective_abandon_phone,
        recovery_key=recovery_key,
        reason_row=reason_row,
    )
    store_id_label = _recovery_store_id_label(store_obj, store_slug)
    _log_phone_resolution(
        store_id=store_id_label,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        source=phone_source,
        phone=phone,
        allowed_to_send=allowed_to_send,
    )
    if (
        phone
        and allowed_to_send
        and _normal_recovery_phone_normalized_equals_merchant(
            phone, _normal_recovery_merchant_normalized_digits(store_obj)
        )
    ):
        _log_normal_recovery_blocked_merchant_match(session_id, cart_id)
        phone = None
        allowed_to_send = False
    rt_for_log = reason_tag if reason_tag else (rt_raw or None)
    if rt_for_log is not None and isinstance(rt_for_log, str) and not rt_for_log.strip():
        rt_for_log = None
    log_normal_recovery_phone_line(
        session_id=session_id,
        cart_id=cart_id,
        reason_tag=rt_for_log,
        phone=phone,
    )
    if phone:
        commit_normal_recovery_phone_after_resolved(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=phone,
            reason_tag=rt_for_log,
        )

    if not phone or not allowed_to_send:
        print("[NO VERIFIED PHONE] skipping send")
        _log_normal_recovery_attempt_skipped(
            attempt_index=step_num,
            reason="missing_customer_phone",
        )
        _seq2_skip(
            "no_verified_phone",
            session_id=session_id,
        )
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status="skipped_no_verified_phone",
            step=step_num,
        )
        _consume_seq_slot_if_needed()
        return
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
        _log_normal_recovery_attempt_skipped(
            attempt_index=step_num,
            reason="purchase_completed",
        )
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status="stopped_converted",
            step=step_num,
        )
        _seq2_skip("purchase_completed", session_id=session_id)
        _consume_seq_slot_if_needed()
        return

    user_returned_to_site = _is_user_returned(recovery_key)
    purchase_completed = _is_user_converted(recovery_key)
    should_send_anti_spam = (not user_returned_to_site) and (not purchase_completed)
    print("[ANTI SPAM CHECK]")
    print("session_id=", session_id)
    print("user_returned_to_site=", user_returned_to_site)
    print("purchase_completed=", purchase_completed)
    print("should_send=", should_send_anti_spam)
    if not should_send_anti_spam:
        _log_normal_recovery_attempt_skipped(
            attempt_index=step_num,
            reason="purchase_completed" if purchase_completed else "user_returned",
        )
        if not purchase_completed:
            _seq2_skip(
                "customer_returned",
                session_id=session_id,
            )
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status=(
                "stopped_converted" if purchase_completed else "skipped_anti_spam"
            ),
            step=step_num,
        )
        _consume_seq_slot_if_needed()
        return

    with _recovery_session_lock:
        sent_count = _session_recovery_send_count.get(recovery_key, 0)
    max_recovery_attempts = int(configured_message_count)
    allowed = sent_count < max_recovery_attempts
    print("[ATTEMPT CONTROL]")
    print("session_id=", session_id)
    print("sent_count=", sent_count)
    print("max_recovery_attempts=", max_recovery_attempts)
    print("allowed=", allowed)
    if not allowed:
        print("[ATTEMPT BLOCKED]")
        _log_normal_recovery_attempt_skipped(
            attempt_index=step_num,
            reason="sequence_completed",
        )
        _seq2_skip(
            "attempt_limit",
            session_id=session_id,
        )
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status="skipped_attempt_limit",
            step=step_num,
        )
        _consume_seq_slot_if_needed()
        return

    user_returned_to_site = _is_user_returned(recovery_key)
    purchase_completed = _is_user_converted(recovery_key)
    pro_allowed = (not user_returned_to_site) and (not purchase_completed)
    print("[CARTFLOW PRO LOGIC]")
    print("session_id=", session_id)
    print("reason_tag=", reason_tag)
    print("delay_minutes=", scheduled_recovery_delay_minutes)
    print("delay_passed=", True)
    print("user_returned_to_site=", user_returned_to_site)
    print("purchase_completed=", purchase_completed)
    print("sent_count=", sent_count)
    print("allowed=", pro_allowed)
    if not pro_allowed:
        print("[CARTFLOW PRO LOGIC] blocked before send")
        if purchase_completed:
            pro_st = "stopped_converted"
        elif user_returned_to_site:
            pro_st = "skipped_anti_spam"
        else:
            pro_st = "skipped_attempt_limit"
        _seq2_skip(
            pro_st,
            session_id=session_id,
        )
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status=pro_st,
            step=step_num,
        )
        _consume_seq_slot_if_needed()
        return

    reason_row_send = _cart_recovery_reason_latest_row(store_slug, session_id)
    if _recovery_row_user_rejected_help(reason_row_send):
        print("[SKIP WA - USER REJECTED HELP]")
        _seq2_skip(
            "user_rejected_help",
            session_id=session_id,
        )
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status="skipped_user_rejected_help",
            step=step_num,
        )
        print("[RECOVERY TASK EXIT CLEANLY]")
        print("reason=user_rejected_help")
        _consume_seq_slot_if_needed()
        return None

    if not reason_tag:
        print("[SKIP WA - MISSING REASON_TAG]")
        _log_normal_recovery_attempt_skipped(
            attempt_index=step_num,
            reason="missing_reason",
        )
        _seq2_skip("missing_reason_tag", session_id=session_id)
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status="skipped_missing_reason_tag",
            step=step_num,
        )
        _consume_seq_slot_if_needed()
        return None

    if not last_activity and not seq_follow:
        print("[SKIP WA - MISSING LAST_ACTIVITY]")
        _seq2_skip(
            "missing_last_activity",
            session_id=session_id,
        )
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=None,
            message=text,
            status="skipped_missing_last_activity",
            step=step_num,
        )
        _consume_seq_slot_if_needed()
        return None

    if multi_slot_index is not None:
        reason_attempt_log = canonical_reason_template_key(reason_tag) or reason_tag or ""
        try:
            print("[MULTI WA SEND ATTEMPT]")
            print("reason=", reason_attempt_log)
            print("index=", int(multi_slot_index))
            print("text=", text)
        except Exception:  # noqa: BLE001
            pass

    if step_num > 1:
        crep_send = _normal_recovery_positive_reply_blocks_followup(
            session_id=session_id, cart_id=cart_id
        )
        try:
            max_a_send = max(0, int(configured_message_count))
        except (TypeError, ValueError):
            max_a_send = 1
        rt_send = (reason_tag or "") if reason_tag else ""
        _log_second_recovery_check(
            session_id=session_id,
            cart_id=cart_id,
            sent_count=int(sent_count),
            max_attempts=max_a_send,
            customer_phone=phone,
            reason_tag=rt_send,
            purchase_completed=_is_user_converted(recovery_key),
            user_returned_to_site=_is_user_returned(recovery_key),
            customer_replied=crep_send,
            allowed=True,
        )

    if step_num > 1:
        _log_second_recovery_line(
            "[SECOND RECOVERY SEND ATTEMPT]",
            session_id=(session_id or "").strip(),
            cart_id=(cart_id or "").strip(),
            step=str(step_num),
            recovery_key=recovery_key,
        )

    _assert_forbidden_stale_recovery_phone(phone)
    text = apply_outbound_tracking_to_message(
        text,
        cart_id=cart_id,
        session_id=session_id,
    )
    from services.cartflow_duplicate_guard import (
        log_lifecycle_conflict_pattern,
        release_outbound_whatsapp_inflight,
        try_begin_outbound_whatsapp_inflight,
    )
    from services.cartflow_runtime_health import (
        ANOMALY_IMPOSSIBLE_STATE_TRANSITION,
        ANOMALY_SEND_AFTER_CONVERSION,
        ANOMALY_SEND_AFTER_RETURN,
        record_runtime_anomaly,
    )

    _diag_converted = _is_user_converted(recovery_key)
    _diag_returned = _is_user_returned(recovery_key)
    _diag_replied = _normal_recovery_positive_reply_blocks_followup(
        session_id=session_id, cart_id=cart_id
    )
    if _diag_converted:
        log_lifecycle_conflict_pattern(
            "send_after_conversion",
            recovery_key=recovery_key,
            session_id=session_id,
            cart_id=cart_id or "",
            step=step_num,
            detail="pre_provider_diag",
        )
        record_runtime_anomaly(
            ANOMALY_SEND_AFTER_CONVERSION,
            source="duplicate_guard",
            detail="pre_send_diag",
        )
    if _diag_returned:
        log_lifecycle_conflict_pattern(
            "send_after_return",
            recovery_key=recovery_key,
            session_id=session_id,
            cart_id=cart_id or "",
            step=step_num,
            detail="pre_provider_diag",
        )
        record_runtime_anomaly(
            ANOMALY_SEND_AFTER_RETURN,
            source="duplicate_guard",
            detail="pre_send_diag",
        )
    if _diag_replied:
        log_lifecycle_conflict_pattern(
            "send_after_reply",
            recovery_key=recovery_key,
            session_id=session_id,
            cart_id=cart_id or "",
            step=step_num,
            detail="pre_provider_diag",
        )
        record_runtime_anomaly(
            ANOMALY_IMPOSSIBLE_STATE_TRANSITION,
            source="duplicate_guard",
            detail="send_after_reply_diag",
        )

    if not try_begin_outbound_whatsapp_inflight(recovery_key, step_num):
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=phone,
            message=text,
            status="skipped_duplicate",
            step=step_num,
        )
        _consume_seq_slot_if_needed()
        return None
    try:
        wa_result = send_whatsapp(
            phone,
            text,
            reason_tag=reason_tag,
            wa_trace_path=__file__,
            wa_trace_session_id=session_id,
            wa_trace_store_slug=store_slug,
            wa_trace_last_activity=last_activity,
            wa_trace_recovery_delay_minutes=delay_minutes,
            wa_trace_delay_passed=True,
        )
    finally:
        release_outbound_whatsapp_inflight(recovery_key, step_num)
    wa_dict = wa_result if isinstance(wa_result, dict) else {}
    ok_flag = wa_dict.get("ok") is True
    sid_str = str(wa_dict.get("sid") or "").strip()
    status_raw = wa_dict.get("status")

    if multi_slot_index is not None:
        try:
            print("[MULTI WA SEND RESULT]")
            print("index=", int(multi_slot_index))
            print("ok=", ok_flag)
            print("sid=", sid_str)
            print("status=", status_raw if status_raw is not None else "")
        except Exception:  # noqa: BLE001
            pass

    if multi_slot_index is None:
        success = ok_flag
    else:
        success = ok_flag and bool(sid_str)
        if not success:
            try:
                if ok_flag and not sid_str:
                    err_out = "missing_sid"
                else:
                    e = wa_dict.get("error")
                    err_out = str(e) if e is not None else "send_failed"
                print("[MULTI MESSAGE FAILED]")
                print("index=", int(multi_slot_index))
                print("error=", err_out)
            except Exception:  # noqa: BLE001
                pass

    if success:
        print("[DELAY SEND EXECUTED]")
        mt_ok: Optional[int] = None
        with _recovery_session_lock:
            _session_recovery_send_count[recovery_key] = sent_count + 1
            if multi_slot_index is not None:
                _session_recovery_multi_verified_indexes.setdefault(
                    recovery_key, set()
                ).add(int(multi_slot_index))
                mc = _session_recovery_multi_attempt_cap.get(recovery_key)
                mt_ok = int(mc) if mc is not None else None
        if multi_slot_index is not None and mt_ok is not None:
            try:
                print("[MULTI MESSAGE SENT]")
                print("index=", int(multi_slot_index))
                print("total=", mt_ok)
            except Exception:  # noqa: BLE001
                pass
        _log_normal_recovery_attempt_sent(
            attempt_index=step_num,
            sid=sid_str,
        )
        if step_num > 1:
            _log_second_recovery_line(
                "[SECOND RECOVERY SENT]",
                sid=sid_str,
                session_id=session_id,
                customer_phone=(phone or "")[:40],
                step=str(step_num),
            )

    if not success:
        if wa_dict.get("error") == "user_rejected_help":
            print("skipped_user_rejected_help = True")
            _seq2_skip(
                "user_rejected_help",
                session_id=session_id,
            )
            _persist_cart_recovery_log(
                store_slug=store_slug,
                session_id=session_id,
                cart_id=cart_id,
                phone=None,
                message=text,
                status="skipped_user_rejected_help",
                step=step_num,
            )
            print("[RECOVERY TASK EXIT CLEANLY]")
            print("reason=user_rejected_help_send_guard")
            _consume_seq_slot_if_needed()
            return
        _seq2_skip(
            "whatsapp_failed",
            session_id=session_id,
        )
        _persist_cart_recovery_log(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=phone,
            message=text,
            status="whatsapp_failed",
            step=step_num,
        )
        print("recovery NOT marked as sent due to failure")
        _consume_seq_slot_if_needed()
        return

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
    _consume_seq_slot_if_needed()
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
        multi_total = _session_recovery_multi_attempt_cap.get(recovery_key)

    if multi_slot_index is not None and multi_total is not None:
        with _recovery_session_lock:
            verified_n = len(
                _session_recovery_multi_verified_indexes.get(recovery_key, set())
            )
        if verified_n >= int(multi_total):
            with _recovery_session_lock:
                _session_recovery_sent[recovery_key] = True
                _session_recovery_multi_attempt_cap.pop(recovery_key, None)
                _session_recovery_multi_verified_indexes.pop(recovery_key, None)
            print("[RECOVERY FULLY COMPLETED]")
        return

    with _recovery_session_lock:
        cur_sent = _session_recovery_send_count.get(recovery_key, 0)
    cfg_seq = _normal_recovery_configured_message_count_from_runtime(recovery_key, store_obj)
    if cur_sent < cfg_seq:
        gap_sec = float(_second_attempt_delay_minutes_from_store(store_obj)) * 60.0
        next_idx = int(cur_sent) + 1
        follow_phone = phone or effective_abandon_phone or abandon_event_phone
        gap_min = int(_second_attempt_delay_minutes_from_store(store_obj))
        due_dt = datetime.now(timezone.utc) + timedelta(seconds=gap_sec)
        with _recovery_session_lock:
            _session_recovery_followup_next_due_at[recovery_key] = due_dt.isoformat()
        if int(next_idx) == 2:
            _log_second_recovery_line(
                "[SECOND RECOVERY SCHEDULED]",
                session_id=session_id,
                cart_id=cart_id or "",
                customer_phone=(str(follow_phone or "").strip())[:40],
                next_delay_minutes=gap_min,
            )
        try:
            print(
                "[SEQUENTIAL RECOVERY SCHEDULED] next_index=%s delay_s=%s"
                % (next_idx, gap_sec)
            )
        except OSError:
            pass
        asyncio.create_task(
            _run_recovery_sequence_after_cart_abandoned(
                recovery_key,
                gap_sec,
                store_slug,
                session_id,
                cart_id,
                follow_phone,
                sequential_attempt_index=next_idx,
                multi_message_text=None,
            )
        )
    with _recovery_session_lock:
        _session_recovery_sent[recovery_key] = True
    print("recovery marked as sent")


async def _run_recovery_sequence_after_cart_abandoned(
    recovery_key: str,
    delay_seconds: float,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    abandon_event_phone: Optional[str] = None,
    *,
    multi_slot_index: Optional[int] = None,
    multi_message_text: Optional[str] = None,
    sequential_attempt_index: Optional[int] = None,
) -> None:
    """مدخل آمن: أي خطأ داخل المهمة المؤجّلة لا يصعد إلى ‎TaskGroup‎ / وسيط الطلب."""
    try:
        await _run_recovery_sequence_after_cart_abandoned_impl(
            recovery_key,
            delay_seconds,
            store_slug,
            session_id,
            cart_id,
            abandon_event_phone,
            multi_slot_index=multi_slot_index,
            multi_message_text=multi_message_text,
            sequential_attempt_index=sequential_attempt_index,
        )
    except asyncio.CancelledError:
        raise
    except SystemExit:
        raise
    except KeyboardInterrupt:
        raise
    except BaseException as e:
        if sequential_attempt_index is not None and int(sequential_attempt_index) > 1:
            sk_err = f"{recovery_key}:seq:{int(sequential_attempt_index)}"
            with _recovery_session_lock:
                _session_recovery_seq_logged.pop(sk_err, None)
        print("[RECOVERY TASK CAUGHT ERROR]", str(e))
    print("[RECOVERY TASK COMPLETED SAFELY]")


def _schedule_recovery_multi_slots(
    recovery_key: str,
    slots: list[dict[str, Any]],
    *,
    elapsed_seconds: float,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    abandon_event_phone: Optional[str],
) -> None:
    es = float(elapsed_seconds)
    try:
        print("[MULTI MESSAGE MODE ACTIVATED]")
        print("reason=", slots[0]["canon"])
        print("count=", len(slots))
    except Exception:  # noqa: BLE001
        pass
    with _recovery_session_lock:
        _session_recovery_multi_verified_indexes.pop(recovery_key, None)
        _session_recovery_multi_attempt_cap[recovery_key] = len(slots)
    for s in slots:
        try:
            print(f"[MULTI MESSAGE SCHEDULED] index={s['index']}")
        except Exception:  # noqa: BLE001
            pass
        remain = max(0.0, float(s["delay_seconds"]) - es)
        asyncio.create_task(
            _run_recovery_sequence_after_cart_abandoned(
                recovery_key,
                remain,
                store_slug,
                session_id,
                cart_id,
                abandon_event_phone,
                multi_slot_index=int(s["index"]),
                multi_message_text=str(s.get("text") or ""),
            )
        )


async def _run_recovery_dispatch_cart_abandoned_impl(
    recovery_key: str,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    abandon_event_phone: Optional[str],
    abandon_monotonic: float,
) -> None:
    store_row0 = _load_store_row_for_recovery(store_slug)
    cart_tot0 = _abandoned_cart_cart_value_for_recovery(cart_id)
    th0 = getattr(store_row0, "vip_cart_threshold", None) if store_row0 else None
    is_vip0 = cart_tot0 is not None and is_vip_cart(cart_tot0, store_row0)
    _vip_log_check(cart_tot0, th0, is_vip0)
    if is_vip0:
        rt0 = _reason_tag_for_session(store_slug, session_id) or None
        _vip_recovery_decision_layer(rt0, store_row0)
        ok_vip = _activate_vip_manual_cart_handling(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            cart_total=float(cart_tot0),
            store_obj=store_row0,
            recovery_key=recovery_key,
            reason_tag=rt0,
            abandon_event_phone=abandon_event_phone,
        )
        if not ok_vip:
            log.warning(
                "[VIP ACTIVATION FAILED] session_id=%s recovery_key=%s — dispatch_blocked_no_fallback",
                session_id,
                recovery_key,
            )
        _mark_vip_customer_recovery_closed(recovery_key)
        return
    reason_tag: Optional[str] = None
    store_row: Optional[Any] = None
    for _ in range(_RECOVERY_REASON_POLL_MAX_ATTEMPTS):
        store_row = _load_store_row_for_recovery(store_slug)
        reason_tag = _reason_tag_for_session(store_slug, session_id)
        slots_try = multi_message_slots_for_abandon(reason_tag, store_row)
        if slots_try is not None:
            elapsed = time.monotonic() - abandon_monotonic
            _schedule_recovery_multi_slots(
                recovery_key,
                slots_try,
                elapsed_seconds=elapsed,
                store_slug=store_slug,
                session_id=session_id,
                cart_id=cart_id,
                abandon_event_phone=abandon_event_phone,
            )
            return
        if reason_tag:
            break
        await asyncio.sleep(_RECOVERY_REASON_POLL_INTERVAL_SEC)

    elapsed = time.monotonic() - abandon_monotonic
    store_row = _load_store_row_for_recovery(store_slug)
    reason_tag = _reason_tag_for_session(store_slug, session_id)
    slots_final = multi_message_slots_for_abandon(reason_tag, store_row)
    if slots_final is not None:
        _schedule_recovery_multi_slots(
            recovery_key,
            slots_final,
            elapsed_seconds=elapsed,
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            abandon_event_phone=abandon_event_phone,
        )
        return

    config = None
    delay_s = float(get_recovery_delay(reason_tag, store_config=config))
    remain = max(0.0, delay_s - elapsed)
    print("starting delay task")
    asyncio.create_task(
        _run_recovery_sequence_after_cart_abandoned(
            recovery_key,
            remain,
            store_slug,
            session_id,
            cart_id,
            abandon_event_phone,
        )
    )


async def _run_recovery_dispatch_cart_abandoned(
    recovery_key: str,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    abandon_event_phone: Optional[str],
    abandon_monotonic: float,
) -> None:
    try:
        await _run_recovery_dispatch_cart_abandoned_impl(
            recovery_key,
            store_slug,
            session_id,
            cart_id,
            abandon_event_phone,
            abandon_monotonic,
        )
    except asyncio.CancelledError:
        raise
    except SystemExit:
        raise
    except KeyboardInterrupt:
        raise
    except BaseException as e:
        print("[RECOVERY DISPATCH CAUGHT ERROR]", str(e))
    print("[RECOVERY DISPATCH COMPLETED SAFELY]")


def _inject_cf_test_customer_phone_into_abandon_payload(payload: dict[str, Any]) -> None:
    """‎cf_test_phone‎ → ‎phone‎ when dev/demo-only override is allowed (normal recovery QA)."""
    if not isinstance(payload, dict):
        return
    store_slug = _normalize_store_slug(payload)
    if not cf_test_customer_phone_override_allowed(store_slug):
        return
    raw = payload.get("cf_test_phone")
    if raw is None or not str(raw).strip():
        return
    norm = normalize_cf_test_customer_phone(raw)
    if not norm:
        return
    sid = _session_part_from_payload(payload)
    cid = (_cart_id_str_from_payload(payload) or "").strip() or "-"
    print("[DEMO TEST PHONE CAPTURED]", flush=True)
    print("phone=", norm, flush=True)
    print("session_id=", sid or "", flush=True)
    print("cart_id=", cid, flush=True)
    payload["phone"] = norm
    try:
        payload["_recovery_phone_inject_source"] = "cf_test_phone"
    except (AttributeError, TypeError, ValueError):
        pass


async def handle_cart_abandoned(
    _background_tasks: BackgroundTasks, payload: dict[str, Any]
) -> dict[str, Any]:
    log.info("[HANDLE CART ABANDONED ENTERED]")
    print("[HANDLE CART ABANDONED ENTERED]")
    store_slug = _normalize_store_slug(payload)
    print("store:", store_slug)
    recovery_key = _recovery_key_from_payload(payload)
    payload = _ensure_cart_abandon_payload_has_cart_id(payload, recovery_key)
    print("recovery key:", recovery_key)
    session_id_log = _session_part_from_payload(payload)
    print("[SESSION]", session_id_log)
    cart_id_log = _cart_id_str_from_payload(payload)
    _inject_cf_test_customer_phone_into_abandon_payload(payload)
    abandon_evt_phone: Optional[str] = None
    raw_phone = payload.get("phone")
    if isinstance(raw_phone, str) and raw_phone.strip():
        abandon_evt_phone = raw_phone.strip()[:100]
    if abandon_evt_phone:
        from services.recovery_session_phone import record_recovery_customer_phone

        inj = str(payload.get("_recovery_phone_inject_source") or "").strip()
        record_recovery_customer_phone(
            recovery_key,
            abandon_evt_phone,
            source=inj if inj == "cf_test_phone" else None,
        )
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
    try:
        db.create_all()
        _ensure_store_widget_schema()
        _ensure_default_store_for_recovery()
        store_row = _load_store_row_for_recovery(store_slug)
    except Exception:  # noqa: BLE001
        db.session.rollback()
        store_row = None
    vip_row_id = getattr(store_row, "id", None) if store_row else None
    vip_th_disp = getattr(store_row, "vip_cart_threshold", None) if store_row else None
    vip_th_log = "none" if vip_th_disp is None else str(vip_th_disp)
    log.info(
        "[VIP STORE SETTINGS]\nstore_slug=%s\nstore_id=%s\nvip_cart_threshold=%s",
        store_slug,
        vip_row_id,
        vip_th_log,
    )
    print(
        f"[VIP STORE SETTINGS] store_slug={store_slug!r} store_id={vip_row_id} vip_cart_threshold={vip_th_log}"
    )
    print("store settings loaded")
    try:
        ok_u, err_u, _urow = upsert_abandoned_cart_from_payload(payload, store=store_row)
        if not ok_u and err_u:
            log.warning("[ABANDON UPSERT] %s", err_u)
    except SQLAlchemyError:
        db.session.rollback()
        log.warning("[ABANDON UPSERT FAILED]", exc_info=True)
    cart_total_chk = _cart_total_for_vip_recovery(cart_id_log, payload)
    th_chk = getattr(store_row, "vip_cart_threshold", None) if store_row else None
    ct_chk_s = "none" if cart_total_chk is None else str(cart_total_chk)
    th_chk_s = "none" if th_chk is None else str(th_chk)
    log.info("[VIP CHECK START]\ncart_total=%s\nthreshold=%s", ct_chk_s, th_chk_s)
    print(f"[VIP CHECK START] cart_total={ct_chk_s} threshold={th_chk_s}")
    is_vip_chk = cart_total_chk is not None and is_vip_cart(cart_total_chk, store_row)
    _vip_log_check(cart_total_chk, th_chk, is_vip_chk)
    if is_vip_chk:
        with _recovery_session_lock:
            _session_recovery_started[recovery_key] = True
        reason_vip = _reason_tag_for_session(store_slug, session_id_log) or None
        _vip_recovery_decision_layer(reason_vip, store_row)
        ok_vip = _activate_vip_manual_cart_handling(
            store_slug=store_slug,
            session_id=session_id_log,
            cart_id=cart_id_log,
            cart_total=float(cart_total_chk),
            store_obj=store_row,
            recovery_key=recovery_key,
            reason_tag=reason_vip,
            recovery_log_message=VIP_WIDGET_RECOVERY_LOG_MESSAGE,
            recovery_log_step=int(VIP_WIDGET_RECOVERY_LOG_STEP),
            vip_activation_source=VIP_WIDGET_ACTIVATION_SOURCE,
            abandon_event_phone=abandon_evt_phone,
        )
        if not ok_vip:
            log.warning(
                "[VIP ACTIVATION FAILED] session_id=%s recovery_key=%s — customer_recovery_blocked_no_fallback",
                session_id_log,
                recovery_key,
            )
        _mark_vip_customer_recovery_closed(recovery_key)
        return {
            "recovery_scheduled": False,
            "recovery_vip_manual": True,
            "recovery_skipped": True,
            "customer_recovery_skipped": True,
            "recovery_state": "vip_manual_handling",
        }
    if abandon_evt_phone:
        reason_tag_ab = _reason_tag_for_session(store_slug, session_id_log)
        commit_normal_recovery_phone_after_resolved(
            store_slug=store_slug,
            session_id=session_id_log,
            cart_id=cart_id_log,
            phone=abandon_evt_phone,
            reason_tag=reason_tag_ab,
        )
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
        from services.cartflow_duplicate_guard import note_recovery_schedule_duplicate

        note_recovery_schedule_duplicate(
            store_slug=store_slug,
            session_id=session_id_log,
            cart_id=cart_id_log or "",
            recovery_key=recovery_key,
        )
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
    print("entered recovery handler")
    log.info("cart abandoned received")
    reason_tag_sync = _reason_tag_for_session(store_slug, session_id_log)
    slots_sync = multi_message_slots_for_abandon(reason_tag_sync, store_row)
    if slots_sync:
        _schedule_recovery_multi_slots(
            recovery_key,
            slots_sync,
            elapsed_seconds=0.0,
            store_slug=store_slug,
            session_id=session_id_log,
            cart_id=cart_id_log,
            abandon_event_phone=abandon_evt_phone,
        )
        _log_normal_recovery_auto_start(
            store_slug=store_slug,
            session_id=session_id_log,
            cart_id=cart_id_log,
            mode="multi_message",
        )
        return {
            "recovery_scheduled": True,
            "recovery_multi_message": True,
            "recovery_multi_count": len(slots_sync),
            "recovery_delay_seconds": float(slots_sync[0]["delay_seconds"]),
            "recovery_state": "scheduled",
        }

    abandon_mono = time.monotonic()
    _log_normal_recovery_auto_start(
        store_slug=store_slug,
        session_id=session_id_log,
        cart_id=cart_id_log,
        mode="delay_poll",
    )
    asyncio.create_task(
        _run_recovery_dispatch_cart_abandoned(
            recovery_key,
            store_slug,
            session_id_log,
            cart_id_log,
            abandon_evt_phone,
            abandon_mono,
        )
    )
    return {
        "recovery_scheduled": True,
        "recovery_state": "scheduled",
        "recovery_delay_seconds": None,
    }


@app.api_route("/dev/create-vip-test-cart", methods=["GET", "POST"])
def dev_create_vip_test_cart() -> Any:
    """
    ينشئ ‎AbandonedCart‎ + ‎CartRecoveryReason‎ حقيقيين و‎CartRecoveryLog.status=vip_manual_handling‎
    لاختبار لوحة VIP (أولوية؛ زر إرسال يدوي فعّال — ‎interactive‎ لصف DB).
    ‎GET‎ للتفعيل السريع من المتصفح؛ ‎POST‎ متوافق مع الاختبارات.
    """
    _VIP_TEST_ZID = "vip-codegen-test-cart-1"
    _VIP_TEST_SESSION = "test_vip_session"
    try:
        db.create_all()
        _ensure_store_widget_schema()
        _ensure_default_store_for_recovery()
        st = _load_latest_store_for_recovery()
        if st is None:
            return j({"ok": False, "error": "no_store"}, 500)
        slug = (getattr(st, "zid_store_id", None) or "").strip() or CARTFLOW_DEFAULT_RECOVERY_STORE_ZID
        if getattr(st, "vip_cart_threshold", None) is None:
            st.vip_cart_threshold = 500
        db.session.add(st)
        db.session.commit()

        ac_old = db.session.query(AbandonedCart).filter_by(zid_cart_id=_VIP_TEST_ZID).first()
        if ac_old is not None:
            db.session.delete(ac_old)
            db.session.commit()

        db.session.query(CartRecoveryReason).filter(
            CartRecoveryReason.store_slug == slug,
            CartRecoveryReason.session_id == _VIP_TEST_SESSION,
        ).delete(synchronize_session=False)

        db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.store_slug == slug,
            CartRecoveryLog.cart_id == _VIP_TEST_ZID,
        ).delete(synchronize_session=False)

        db.session.commit()

        now = datetime.now(timezone.utc)
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=_VIP_TEST_ZID,
            customer_phone="+966501112233",
            cart_value=float(1200.0),
            cart_url=(os.getenv("WHATSAPP_FALLBACK_CART_URL") or "").strip() or None,
            status="abandoned",
            vip_mode=True,
            first_seen_at=now,
            last_seen_at=now,
        )
        AbandonedCart.set_raw(
            ac,
            {
                "session_id": _VIP_TEST_SESSION,
                "dev": "create_vip_test_cart",
                "reason_tag": "price",
            },
        )
        db.session.add(ac)

        crr = CartRecoveryReason(
            store_slug=slug,
            session_id=_VIP_TEST_SESSION,
            reason="price",
            customer_phone="+966501112233",
            source="dev_vip_codegen",
            user_rejected_help=False,
            created_at=now,
            updated_at=now,
        )
        db.session.add(crr)
        db.session.commit()

        _persist_cart_recovery_log(
            store_slug=slug,
            session_id=_VIP_TEST_SESSION,
            cart_id=_VIP_TEST_ZID,
            phone="+966501112233",
            message="[dev] VIP test cart for dashboard priority verification",
            status="vip_manual_handling",
            step=None,
        )

        return j({"ok": True, "cart_id": _VIP_TEST_ZID, "vip": True}, 200)
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        log.exception("dev_create_vip_test_cart: %s", e)
        return j({"ok": False, "error": str(e)}, 500)


@app.get("/dev/vip-flow-verify")
async def dev_vip_flow_verify(request: Request) -> Any:
    """
    يُثبت مسار VIP (كشف، تخطي استرجاع العميل، محاولة تنبيه التاجر) دون واتساب حقيقي افتراضياً.
    مع ‎ENV=development‎ و‎?real_whatsapp=1‎ يُستدعى الإرسال الفعلي عبر ‎try_send_vip_merchant_whatsapp_alert‎.
    """
    from contextlib import nullcontext
    from unittest.mock import patch

    slug_restore: Optional[str] = None
    prev_th_restore: Any = None
    prev_phone_restore: Any = None

    real_whatsapp = _is_development_mode() and (request.query_params.get("real_whatsapp") == "1")
    twilio_cm = (
        nullcontext()
        if real_whatsapp
        else patch(
            "main.try_send_vip_merchant_whatsapp_alert",
            return_value={"ok": True, "sid": "vip_flow_verify_stub"},
        )
    )
    try:
        db.create_all()
        _ensure_store_widget_schema()
        _ensure_default_store_for_recovery()
        store_row = _load_store_row_for_recovery(None)
        if store_row is None:
            return j({"ok": False, "error": "no_store"}, 500)
        slug = (getattr(store_row, "zid_store_id", None) or "").strip() or CARTFLOW_DEFAULT_RECOVERY_STORE_ZID
        slug_restore = slug
        prev_th_restore = getattr(store_row, "vip_cart_threshold", None)
        prev_phone_restore = getattr(store_row, "store_whatsapp_number", None)
        store_row.vip_cart_threshold = 100
        store_row.store_whatsapp_number = "+966501112233"
        db.session.commit()

        sid = f"vip-flow-sess-{uuid.uuid4().hex[:12]}"
        cid = f"vip-flow-cart-{uuid.uuid4().hex[:10]}"
        rk = _recovery_key_from_payload({"store": slug, "session_id": sid})
        with _recovery_session_lock:
            _session_recovery_started.pop(rk, None)
            _session_recovery_sent.pop(rk, None)

        ex_ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        if ex_ac is not None:
            db.session.delete(ex_ac)
            db.session.commit()
        ok_u, err_u, _ = upsert_abandoned_cart_from_payload(
            {"cart_id": cid, "cart_value": 500.0, "customer_phone": "+966501112233"},
            store=store_row,
        )
        if not ok_u:
            return j({"ok": False, "error": "cart_upsert_failed", "detail": err_u}, 500)

        db.session.query(CartRecoveryReason).filter(
            CartRecoveryReason.store_slug == slug,
            CartRecoveryReason.session_id == sid,
        ).delete(synchronize_session=False)
        db.session.commit()
        now_utc = datetime.now(timezone.utc)
        db.session.add(
            CartRecoveryReason(
                store_slug=slug,
                session_id=sid,
                reason="price",
                source="vip_flow_verify",
                created_at=now_utc,
                updated_at=now_utc,
            )
        )
        db.session.commit()

        abandon_payload: dict[str, Any] = {
            "event": "cart_abandoned",
            "store": slug,
            "session_id": sid,
            "cart_id": cid,
            "phone": "+966501112233",
            "cart": [{"price": 500.0, "quantity": 1}],
        }
        with twilio_cm:
            h = await handle_cart_abandoned(BackgroundTasks(), abandon_payload)

        vip_detected = h.get("recovery_state") == "vip_manual_handling"
        customer_skipped = h.get("customer_recovery_skipped") is True
        out_body: dict[str, Any] = {
            "ok": True,
            "vip_detected": vip_detected,
            "customer_recovery_skipped": customer_skipped,
            "status": "vip_manual_handling" if vip_detected else "not_vip",
            "merchant_alert_attempted": vip_detected,
        }
        return j(out_body, 200)
    finally:
        if slug_restore:
            try:
                sr = _load_store_row_for_recovery(slug_restore)
                if sr is not None:
                    sr.vip_cart_threshold = prev_th_restore
                    sr.store_whatsapp_number = prev_phone_restore
                    db.session.commit()
            except (SQLAlchemyError, OSError):
                db.session.rollback()


def _handle_cart_state_sync(payload: dict[str, Any]) -> dict[str, Any]:
    """
    مسار موحّد لمزامنة حالة السلة (‎cart_state_sync‎): قيمة، ‎VIP‎، ‎status‎ — بما فيها ‎cleared‎ للسلة الفارغة.
    """
    try:
        _ensure_store_widget_schema()
        db.create_all()
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return {"ok": False, "cart_state_sync": False, "error": "db_schema"}

    reason_raw = str(payload.get("reason") or "").strip().lower()
    allowed = frozenset({"add", "remove", "clear", "abandon", "page_load"})
    if reason_raw not in allowed:
        reason_raw = "page_load"

    ct_raw = payload.get("cart_total")
    ic_raw = payload.get("items_count")
    try:
        cart_total = float(ct_raw) if ct_raw is not None else 0.0
    except (TypeError, ValueError):
        cart_total = 0.0
    try:
        items_count = int(ic_raw) if ic_raw is not None else 0
    except (TypeError, ValueError):
        items_count = 0

    sid_log = (str(payload.get("session_id") or "").strip())[:512]
    cid_in_payload = (_cart_id_str_from_payload(payload) or "").strip()[:255]

    log.info(
        "[CART STATE SYNC RECEIVED]\nreason=%s\ncart_id=%s\nsession_id=%s\ncart_total=%s\nitems_count=%s",
        reason_raw,
        cid_in_payload or "-",
        sid_log or "-",
        str(cart_total),
        str(items_count),
    )
    print(
        f"[CART STATE SYNC RECEIVED] reason={reason_raw} cart_id={cid_in_payload or '-'} "
        f"session_id={sid_log or '-'} cart_total={cart_total} items_count={items_count}"
    )

    if reason_raw == "add":
        _clear_user_rejected_help_for_session(
            _normalize_store_slug(payload),
            _session_part_from_payload(payload),
        )

    store_slug = _normalize_store_slug(payload)
    store_row = _load_store_row_for_recovery(store_slug)
    vip_th_api: Optional[int] = None
    if store_row is not None:
        _th_raw_v = getattr(store_row, "vip_cart_threshold", None)
        if _th_raw_v is not None:
            try:
                vip_th_api = int(_th_raw_v)
            except (TypeError, ValueError):
                vip_th_api = None

    is_empty = (items_count <= 0) or (cart_total <= 0.0)

    merge_pl: dict[str, Any] = dict(payload)
    merge_pl["store"] = store_slug
    rk = _recovery_key_from_payload(merge_pl)
    merge_pl = _ensure_cart_abandon_payload_has_cart_id(merge_pl, rk)
    _inject_cf_test_customer_phone_into_abandon_payload(merge_pl)
    sync_phone = _strip_recovery_phone(merge_pl.get("phone"))
    zid = (_cart_id_str_from_payload(merge_pl) or "").strip()[:255]
    if not zid:
        _is_vip_miss = False if is_empty else bool(is_vip_cart(cart_total, store_row))
        return {
            "ok": True,
            "cart_state_sync": False,
            "error": "missing_cart_id",
            "cart_total": float(cart_total),
            "vip_cart_threshold": vip_th_api,
            "is_vip": _is_vip_miss,
            "vip_from_cart_total": True,
        }

    cart_ids = [zid]
    syn = _synthetic_zid_cart_id_from_recovery_key(rk)
    if syn and syn not in cart_ids:
        cart_ids.append(syn)

    cands = _collect_abandoned_cart_rows_for_merge(
        cart_ids=cart_ids,
        session_id=sid_log if sid_log else None,
        recovery_key=rk,
        store_row=store_row,
    )
    row = _pick_canonical_abandoned_cart_row(cands) if cands else None
    was_vip_before = bool(row is not None and getattr(row, "vip_mode", False))
    if cands and row is not None:
        ndel = _delete_noncanonical_abandoned_merge_rows(keep=row, candidates=cands)
        if ndel:
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                return {
                    "ok": False,
                    "cart_state_sync": False,
                    "error": "merge_failed",
                    "cart_total": float(cart_total),
                    "vip_cart_threshold": vip_th_api,
                    "is_vip": False
                    if is_empty
                    else bool(is_vip_cart(cart_total, store_row)),
                    "vip_from_cart_total": True,
                }

    sto_id: Optional[int] = None
    if store_row is not None and getattr(store_row, "id", None) is not None:
        sto_id = int(store_row.id)

    if is_empty:
        vip_mode_eff = False
        status_eff = "cleared"
    elif is_vip_cart(cart_total, store_row):
        vip_mode_eff = True
        status_eff = "abandoned"
    else:
        vip_mode_eff = False
        status_eff = "abandoned"

    created = row is None
    real_cid = cid_in_payload or zid

    try:
        if row is None:
            row = AbandonedCart(
                zid_cart_id=zid,
                cart_value=float(cart_total),
                status=status_eff,
                vip_mode=vip_mode_eff,
            )
            if sto_id is not None:
                row.store_id = sto_id
            if sid_log:
                row.recovery_session_id = sid_log
            db.session.add(row)
        else:
            _abandoned_cart_try_upgrade_synthetic_zid(row, real_cid)
            row.cart_value = float(cart_total)
            row.status = status_eff
            row.vip_mode = vip_mode_eff
            if sto_id is not None:
                row.store_id = sto_id
            if sid_log:
                row.recovery_session_id = sid_log

        db.session.flush()

        if sync_phone:
            row.customer_phone = sync_phone[:100]
            from services.normal_recovery_phone_persist import (
                apply_normal_recovery_phone_to_session,
            )

            inj_src = (
                "cf_test_phone"
                if str(merge_pl.get("_recovery_phone_inject_source") or "").strip()
                == "cf_test_phone"
                else None
            )
            apply_normal_recovery_phone_to_session(
                db.session,
                store_slug=store_slug,
                session_id=sid_log,
                cart_id=real_cid,
                phone=sync_phone,
                reason_tag=None,
                phone_record_source=inj_src,
            )

        prev: dict[str, Any] = {}
        if getattr(row, "raw_payload", None):
            try:
                p_raw = json.loads(row.raw_payload)
                if isinstance(p_raw, dict):
                    prev = p_raw
            except (json.JSONDecodeError, TypeError, ValueError):
                prev = {}
        prev["items_count"] = items_count
        prev["cart_state_sync_reason"] = reason_raw
        if isinstance(payload.get("cart"), list):
            prev["cart"] = payload.get("cart")
        AbandonedCart.set_raw(row, prev)

        db.session.commit()
        db.session.refresh(row)
    except IntegrityError:
        db.session.rollback()
        return {"ok": False, "cart_state_sync": False, "error": "integrity"}

    ups_cid = (str(getattr(row, "zid_cart_id", "") or zid or "")).strip()[:255]
    ups_sid = (str(getattr(row, "recovery_session_id", "") or sid_log or "")).strip()[:512]
    try:
        store_for_alert = _resolve_store_for_vip_merchant_alert(row)
        _vip_merchant_auto_alert_if_newly_entering(
            row,
            store_for_alert,
            store_slug,
            ups_sid,
            was_vip_before=was_vip_before,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("VIP merchant auto alert hook failed (non-fatal): %s", e, exc_info=True)
    log.info(
        "[CART STATE UPSERT]\nmode=%s\ncart_id=%s\nsession_id=%s\ncart_total=%s\nvip_mode=%s\nstatus=%s",
        "created" if created else "updated",
        ups_cid,
        ups_sid,
        str(row.cart_value),
        str(bool(row.vip_mode)).lower(),
        str(row.status or ""),
    )
    print(
        f"[CART STATE UPSERT] mode={'created' if created else 'updated'} cart_id={ups_cid} "
        f"session_id={ups_sid} cart_total={row.cart_value} vip_mode={bool(row.vip_mode)} status={row.status}"
    )

    return {
        "ok": True,
        "cart_state_sync": True,
        "vip_mode": bool(getattr(row, "vip_mode", False)),
        "status": str(row.status or ""),
        "cart_total": float(cart_total),
        "vip_cart_threshold": vip_th_api,
        "is_vip": bool(not is_empty and getattr(row, "vip_mode", False)),
        "vip_from_cart_total": True,
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
    print("[CF API] event received")
    try:
        pl_snip = json.dumps(
            _redact_secrets_for_log(payload), ensure_ascii=False, default=str
        )[:2000]
    except Exception:  # noqa: BLE001
        pl_snip = (str(payload))[:2000]
    _ev_dbg = payload.get("event")
    _ct_dbg = _cart_total_from_abandon_payload(payload)
    _ct_dbg_s = "none" if _ct_dbg is None else str(_ct_dbg)
    _cid_dbg = (_cart_id_str_from_payload(payload) or "").strip() or "-"
    _sid_dbg = (_session_part_from_payload(payload) or "").strip() or "-"
    log.info(
        "[API CART EVENT RECEIVED]\npayload=%s\nevent=%s\ncart_total=%s\ncart_id=%s\nsession_id=%s",
        pl_snip,
        _ev_dbg,
        _ct_dbg_s,
        _cid_dbg,
        _sid_dbg,
    )
    event = payload.get("event")
    event_norm = str(event).strip().lower() if event is not None else ""
    log.info("[EVENT ROUTING] event=%s", event)
    if event_norm == "cart_state_sync":
        out_sync: dict[str, Any] = {"ok": True, "event": "cart_state_sync"}
        out_sync.update(_handle_cart_state_sync(payload))
        return j(out_sync, 200)
    if event_norm == "cart_abandoned":
        print("[ROUTING TO VIP HANDLER]")
        log.info("[ROUTING TO VIP HANDLER]")
        print("[CF API] processing event")
        wc_id = (_cart_id_str_from_payload(payload) or "").strip() or "-"
        wc_sid = (_session_part_from_payload(payload) or "").strip() or "-"
        wc_tot = _cart_total_from_abandon_payload(payload)
        wc_tot_disp = "none" if wc_tot is None else str(wc_tot)
        log.info(
            "[WIDGET CART EVENT]\ncart_id=%s\ncart_total=%s\nsession_id=%s",
            wc_id,
            wc_tot_disp,
            wc_sid,
        )
        out_abandon: dict[str, Any] = {"ok": True, "event": event}
        out_abandon.update(await handle_cart_abandoned(background_tasks, payload))
        return j(out_abandon, 200)
    out: dict[str, Any] = {
        "ok": True,
        "event": payload.get("event"),
    }
    if payload_indicates_user_returned_to_site(payload):
        _mark_user_returned_for_payload(payload)
        record_behavioral_user_return_from_payload(payload)
    if (
        payload.get("user_converted") is True
        or payload.get("event") == "user_converted"
        or payload.get("purchase_completed") is True
    ):
        _mark_user_converted_for_payload(payload)
        out["conversion_tracked"] = True
    if payload.get("event") == "add_to_cart":
        _clear_user_rejected_help_for_session(
            _normalize_store_slug(payload),
            _session_part_from_payload(payload),
        )
        print("[BEHAVIOR RESET]")
        out["behavior_reset"] = True
    _sync_abandoned_cart_vip_after_live_cart_payload(payload)
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
    _sync_abandoned_cart_vip_after_live_cart_payload(
        {
            "store_slug": str(ss).strip(),
            "session_id": str(sid).strip(),
            "purchase_completed": True,
        }
    )
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
    d = dashboard_normal_carts(
        _minimal_get_request("/dashboard/normal-carts")
    )
    dct = d.body or b""
    dashboard_flow_ready = bool(
        d.status_code == 200 and (b"recovery_delay" in dct or b"template_price" in dct)
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
    يتحقق من مسار ‎/dashboard/normal-carts‎ وأن الرد ‎HTML‎.
    """
    try:
        route_exists = _app_route_get_exists("/dashboard/normal-carts")
        tc = _app_test_client()
        resp = tc.get("/dashboard/normal-carts")
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
            customer_phone=_cartflow_demo_test_phone(),
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
                send_whatsapp(
                    phone=_cartflow_demo_test_phone(),
                    message=message,
                    wa_trace_path=__file__,
                    wa_trace_last_activity=last,
                    wa_trace_delay_passed=True,
                )
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
                phone=row.customer_phone or _cartflow_demo_test_phone(),
                message=message,
                wa_trace_path=__file__,
                wa_trace_last_activity=last,
                wa_trace_delay_passed=True,
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
    return j(
        send_whatsapp(
            phone,
            message,
            wa_trace_path=__file__,
            wa_trace_delay_passed=WA_TRACE_DELAY_UNSPECIFIED,
        )
    )


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


def _vip_dashboard_cart_link(ac: AbandonedCart) -> str:
    """رابط إكمال الطلب على بطاقة VIP — عمود السلة أو ‎extract_cart_url‎ على ‎raw_payload‎."""
    cu = getattr(ac, "cart_url", None)
    if isinstance(cu, str) and cu.strip():
        return cu.strip()[:2048]
    rp = getattr(ac, "raw_payload", None)
    if isinstance(rp, str) and rp.strip():
        try:
            parsed = json.loads(rp)
        except (json.JSONDecodeError, TypeError, ValueError):
            return ""
        if isinstance(parsed, dict):
            ex = extract_cart_url(parsed)
            return (ex or "").strip()[:2048]
    return ""


def _vip_merchant_ready_reply_bodies(*, cart_link: str) -> dict[str, str]:
    """
    رسائل يدوية جاهزة يفتحها التاجر عبر واتساب مع العميل.
    بدون أسطر الرابط إن لم يتوفر رابط صالح.
    """
    link = (cart_link or "").strip()
    offer_lines = ["هلا 👋", "نقدر نساعدك تكمل طلبك الآن بعرض مناسب 🎁"]
    reminder_lines = ["هلا 👋", "لاحظنا إن طلبك ما اكتمل، ونقدر نساعدك تكمله بسهولة."]
    if link:
        offer_lines.extend(["تقدر تكمل من هنا:", link])
        reminder_lines.extend(["هذا رابط السلة:", link])
    direct = (
        "هلا 👋\n"
        "أنا من المتجر، أقدر أساعدك تكمل الطلب أو أجاوب على أي استفسار."
    )
    return {
        "offer": "\n".join(offer_lines),
        "reminder": "\n".join(reminder_lines),
        "direct": direct,
    }


def _vip_wa_prefill_utf8_base64(body: Optional[str]) -> str:
    """UTF-8 → base64 لوسم data-* حتى تبقى العربية والإيموجي سليمة عند القراءة من DOM."""
    if body is None:
        return ""
    s = str(body).strip()
    if not s:
        return ""
    try:
        return base64.b64encode(s.encode("utf-8")).decode("ascii")
    except (UnicodeEncodeError, TypeError, ValueError):
        return ""


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
        emit_recovery_wa_send_trace(
            path_file=__file__,
            delay_passed=WA_TRACE_DELAY_UNSPECIFIED,
        )
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

def _store_slug_for_cart_vip_sync(payload: dict[str, Any]) -> str:
    """مفتاح المتجر من حمولة الويدجت أو ‎/api/conversion‎ (‎store‎ أو ‎store_slug‎)."""
    raw = payload.get("store")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    ss = payload.get("store_slug")
    if isinstance(ss, str) and ss.strip():
        return ss.strip()
    return "default"


def _sync_abandoned_cart_vip_after_live_cart_payload(payload: dict[str, Any]) -> None:
    """
    بعد أحداث سلة حية (غير ‎cart_abandoned‎): تحديث أو إنشاء ‎AbandonedCart‎؛
    تعزيز ‎vip_mode/status‎ عند تحقق العتبة — دون تعديل ‎is_vip_cart‎ نفسها.
    """
    if not isinstance(payload, dict):
        return
    ev = str((payload.get("event") or "")).strip().lower()
    if ev == "cart_abandoned":
        return
    try:
        _ensure_store_widget_schema()
        db.create_all()
        store_slug = _store_slug_for_cart_vip_sync(payload)
        store_row = _load_store_row_for_recovery(store_slug)

        payload_session = dict(payload)
        if isinstance(store_slug, str) and store_slug.strip() and payload_session.get("store") is None:
            payload_session["store"] = store_slug.strip()

        merge_payload = dict(payload_session)
        rk = _recovery_key_from_payload(merge_payload)
        merge_payload = _ensure_cart_abandon_payload_has_cart_id(merge_payload, rk)
        cid_synth = (_cart_id_str_from_payload(merge_payload) or "").strip()
        if not cid_synth:
            return

        cid_from_request = (_cart_id_str_from_payload(payload) or "").strip()

        row = _resolve_abandoned_cart_row_for_vip_live_sync(
            payload=payload,
            merge_payload=merge_payload,
            payload_session=payload_session,
            store_row=store_row,
            cid_synth=cid_synth[:255],
        )
        if row is not None:
            _abandoned_cart_try_upgrade_synthetic_zid(row, cid_from_request)
            db.session.flush()

        sid_for_log_raw = merge_payload.get("session_id") or payload_session.get("session_id")
        sid_for_log = (
            sid_for_log_raw.strip()[:512]
            if isinstance(sid_for_log_raw, str) and sid_for_log_raw.strip()
            else ""
        )
        sto_for_log: Optional[int] = (
            int(store_row.id) if store_row is not None and getattr(store_row, "id", None) is not None else None
        )

        purchase_done = bool(
            payload.get("purchase_completed") is True
            or payload.get("user_converted") is True
            or ev == "user_converted"
        )

        def _apply_store_id_if_missing(ac: AbandonedCart) -> None:
            if store_row is not None and getattr(store_row, "id", None) is not None:
                if getattr(ac, "store_id", None) is None:
                    try:
                        ac.store_id = int(store_row.id)
                    except (TypeError, ValueError):
                        pass

        if purchase_done:
            if row is None:
                return
            had_vip = bool(getattr(row, "vip_mode", False))
            if str(row.status or "").strip() != "recovered":
                row.status = "recovered"
                row.recovered_at = datetime.now(timezone.utc)
            row.vip_mode = False
            AbandonedCart.set_raw(row, payload_session)
            db.session.commit()
            if had_vip:
                log.info("[VIP REMOVED] reason=purchase_completed")
                print("[VIP REMOVED] reason=purchase_completed")
            return

        cart_list = merge_payload.get("cart")
        cart_empty = isinstance(cart_list, list) and len(cart_list) == 0
        if cart_empty:
            tot_eff: Optional[float] = 0.0
        else:
            tot = _cart_total_from_abandon_payload(merge_payload)
            tot_eff = float(tot) if tot is not None else None

        if tot_eff is None:
            return

        th_raw = getattr(store_row, "vip_cart_threshold", None) if store_row else None
        th_s = "none" if th_raw is None else str(th_raw)
        is_vip_now = bool(is_vip_cart(tot_eff, store_row))

        # صف جديد: فقط عند ‎VIP‎ وقيمة سلّة صالحة — وإلا دمج/تحديث صف موجود (لا تكرار)
        if row is None:
            log.info(
                "[VIP UPDATE CHECK]\ncart_total=%s\nthreshold=%s\nis_vip=%s",
                str(tot_eff),
                th_s,
                str(is_vip_now).lower(),
            )
            print(
                f"[VIP UPDATE CHECK] cart_total={tot_eff} threshold={th_s} is_vip={str(is_vip_now).lower()}"
            )
            if not is_vip_now or cart_empty or tot_eff <= 0:
                return
            row_ins = AbandonedCart(
                zid_cart_id=cid_synth[:255],
                cart_value=float(tot_eff),
                status="abandoned",
                vip_mode=True,
            )
            _apply_store_id_if_missing(row_ins)
            rsid_ins = merge_payload.get("session_id") or payload_session.get("session_id")
            if isinstance(rsid_ins, str) and rsid_ins.strip():
                row_ins.recovery_session_id = rsid_ins.strip()[:512]
            AbandonedCart.set_raw(row_ins, merge_payload)
            db.session.add(row_ins)
            try:
                db.session.flush()
                row = row_ins
            except IntegrityError:
                db.session.rollback()
                row = _resolve_abandoned_cart_row_for_vip_live_sync(
                    payload=payload,
                    merge_payload=merge_payload,
                    payload_session=payload_session,
                    store_row=store_row,
                    cid_synth=cid_synth[:255],
                )
                if row is not None:
                    _abandoned_cart_try_upgrade_synthetic_zid(row, cid_from_request)
                    db.session.flush()
                if row is None:
                    row = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid_synth[:255]).first()
                if row is None:
                    return
            else:
                db.session.commit()
                db.session.refresh(row)
                upsert_cid = (row.zid_cart_id or cid_synth or "").strip()[:255]
                upsert_sid = (getattr(row, "recovery_session_id", None) or sid_for_log or "").strip()[:512]
                upsert_st = getattr(row, "store_id", None)
                upsert_st = int(upsert_st) if upsert_st is not None else sto_for_log
                _log_vip_cart_upsert("created", cart_id=upsert_cid, session_id=upsert_sid, store_id=upsert_st)
                _log_vip_cart_saved(row)
                try:
                    store_alert = _resolve_store_for_vip_merchant_alert(row)
                    _vip_merchant_auto_alert_if_newly_entering(
                        row,
                        store_alert,
                        store_slug,
                        upsert_sid,
                        was_vip_before=False,
                    )
                except Exception as e:  # noqa: BLE001
                    log.warning("VIP merchant auto alert (insert) failed: %s", e, exc_info=True)
                return

        was_vip_before_update = bool(getattr(row, "vip_mode", False))
        st_norm = str(row.status or "").strip().lower()
        if st_norm == "recovered":
            if tot_eff is not None:
                row.cart_value = tot_eff
            AbandonedCart.set_raw(row, merge_payload)
            db.session.commit()
            return

        row.cart_value = tot_eff
        AbandonedCart.set_raw(row, merge_payload)

        log.info(
            "[VIP UPDATE CHECK]\ncart_total=%s\nthreshold=%s\nis_vip=%s",
            str(tot_eff),
            th_s,
            str(is_vip_now).lower(),
        )
        print(f"[VIP UPDATE CHECK] cart_total={tot_eff} threshold={th_s} is_vip={str(is_vip_now).lower()}")

        if cart_empty or tot_eff <= 0:
            had_vip = bool(getattr(row, "vip_mode", False))
            if str(row.status or "").strip() != "recovered":
                row.status = "recovered"
                row.recovered_at = datetime.now(timezone.utc)
            row.vip_mode = False
            db.session.commit()
            if had_vip:
                log.info("[VIP REMOVED] reason=cart_cleared")
                print("[VIP REMOVED] reason=cart_cleared")
            return

        did_vip_save = False
        if is_vip_now and str(row.status or "").strip() != "recovered":
            row.vip_mode = True
            row.status = "abandoned"
            _apply_store_id_if_missing(row)
            rsid2 = merge_payload.get("session_id") or payload_session.get("session_id")
            if isinstance(rsid2, str) and rsid2.strip():
                row.recovery_session_id = rsid2.strip()[:512]
            did_vip_save = True

        if (
            th_raw is not None
            and bool(getattr(row, "vip_mode", False))
            and not is_vip_now
        ):
            row.vip_mode = False
            log.info("[VIP REMOVED] reason=below_threshold")
            print("[VIP REMOVED] reason=below_threshold")
            did_vip_save = False

        db.session.commit()
        if did_vip_save and bool(getattr(row, "vip_mode", False)):
            upsert_cid = (row.zid_cart_id or cid_synth or "").strip()[:255]
            upsert_sid = (getattr(row, "recovery_session_id", None) or sid_for_log or "").strip()[:512]
            upsert_st = getattr(row, "store_id", None)
            upsert_st = int(upsert_st) if upsert_st is not None else sto_for_log
            _log_vip_cart_upsert("updated", cart_id=upsert_cid, session_id=upsert_sid, store_id=upsert_st)
            _log_vip_cart_saved(row)
            try:
                store_alert = _resolve_store_for_vip_merchant_alert(row)
                _vip_merchant_auto_alert_if_newly_entering(
                    row,
                    store_alert,
                    store_slug,
                    upsert_sid,
                    was_vip_before=was_vip_before_update,
                )
            except Exception as e:  # noqa: BLE001
                log.warning("VIP merchant auto alert (update) failed: %s", e, exc_info=True)
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        log.warning("[VIP CART SYNC] failed", exc_info=True)


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
        emit_recovery_wa_send_trace(
            path_file=__file__,
            delay_passed=WA_TRACE_DELAY_UNSPECIFIED,
        )
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
        or p.get("cart_total")
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


def upsert_abandoned_cart_from_payload(
    payload: dict,
    *,
    store: Optional[Any] = None,
) -> Tuple[bool, str, Optional[AbandonedCart]]:
    # إدراج أو تحديث ‎AbandonedCart‎ — دمج حسب ‎zid_cart_id‎ ثم ‎recovery_session_id‎ ثم ‎cf_w_*‎ من ‎recovery_key‎
    fields = normalize_zid_cart_fields(payload)
    if not fields["zid_cart_id"]:
        return False, "missing zid_cart_id", None

    pl = payload if isinstance(payload, dict) else {}
    rk = _recovery_key_from_payload(pl)
    sid_raw = pl.get("session_id")
    sid_s = sid_raw.strip()[:512] if isinstance(sid_raw, str) and sid_raw.strip() else ""

    cart_ids: list[str] = []
    zid = (fields["zid_cart_id"] or "").strip()[:255]
    if zid:
        cart_ids.append(zid)
    syn = _synthetic_zid_cart_id_from_recovery_key(rk)
    if syn and syn not in cart_ids:
        cart_ids.append(syn)

    store_any = store if store is not None else None
    cands = _collect_abandoned_cart_rows_for_merge(
        cart_ids=cart_ids,
        session_id=sid_s if sid_s else None,
        recovery_key=rk,
        store_row=store_any,
    )
    row = _pick_canonical_abandoned_cart_row(cands) if cands else None
    merged_away = 0
    if cands and row is not None:
        merged_away = _delete_noncanonical_abandoned_merge_rows(keep=row, candidates=cands)
        if merged_away:
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                log.warning("[ABANDON UPSERT] merge_flush_failed", exc_info=True)
                return False, "merge_flush_failed", None

    created = False
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
        created = True
    else:
        _abandoned_cart_try_upgrade_synthetic_zid(row, zid)
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
    if store is not None and getattr(store, "id", None) is not None:
        try:
            row.store_id = int(store.id)
        except (TypeError, ValueError):
            pass
    evt_raw = ""
    try:
        evt_raw = str((payload.get("event") or "")).strip().lower()
    except Exception:  # noqa: BLE001
        evt_raw = ""
    if evt_raw == "cart_abandoned":
        if str(row.status or "").strip() != "recovered":
            row.status = "abandoned"
    try:
        rsid = payload.get("session_id")
        if isinstance(rsid, str) and rsid.strip():
            row.recovery_session_id = rsid.strip()[:512]
    except (AttributeError, TypeError):
        pass
    try:
        cv_disp = row.cart_value
        if cv_disp is None:
            cv_disp = fields.get("cart_value")
        sid_out = str(row.store_id) if getattr(row, "store_id", None) is not None else "none"
        log.info(
            "[ABANDONED CART SAVED]\ncart_id=%s\ncart_value=%s\nstore_id=%s\nsession_id=%s",
            fields["zid_cart_id"],
            str(cv_disp) if cv_disp is not None else "",
            sid_out,
            (str(payload.get("session_id") or "").strip()[:512] or "-"),
        )
    except Exception:  # noqa: BLE001
        pass

    vip_upsert_log = False
    try:
        if bool(getattr(row, "vip_mode", False)) and str(row.status or "").strip() == "abandoned":
            vip_upsert_log = True
    except Exception:  # noqa: BLE001
        vip_upsert_log = False

    db.session.commit()

    if vip_upsert_log and row is not None:
        try:
            db.session.refresh(row)
        except (SQLAlchemyError, OSError):
            db.session.rollback()
        cid_u = (str(getattr(row, "zid_cart_id", "") or "").strip())[:255]
        sid_u = (
            str(getattr(row, "recovery_session_id", "") or "").strip()[:512]
            or sid_s
            or "-"
        )
        st_u = getattr(row, "store_id", None)
        st_u_int = int(st_u) if st_u is not None else None
        _log_vip_cart_upsert("created" if created else "updated", cart_id=cid_u, session_id=sid_u, store_id=st_u_int)
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


VIP_LIFECYCLE_VALUES = frozenset({"abandoned", "contacted", "closed", "converted"})

_VIP_LIFECYCLE_LABELS_AR: dict[str, str] = {
    "abandoned": "بانتظار التواصل",
    "contacted": "تم التواصل مع العميل",
    "closed": "تم الإغلاق",
    "converted": "تم البيع",
}


def _vip_dashboard_lifecycle_card_and_badge_classes(lc: str) -> tuple[str, str]:
    """فئات ‎Tailwind‎ خفيفة: بطاقة (‎li‎) + شارة الحالة فقط."""
    b = (
        "inline-flex max-w-full items-center rounded-full border px-2.5 py-0.5 "
        "text-xs font-semibold leading-tight"
    )
    if lc == "contacted":
        return (
            "border border-blue-200/90 bg-blue-50/60",
            b + " border-blue-200 bg-blue-50 text-blue-900",
        )
    if lc == "converted":
        return (
            "border border-emerald-200/90 bg-emerald-50/50",
            b + " border-emerald-200 bg-emerald-100/90 text-emerald-900",
        )
    if lc == "closed":
        return (
            "border border-slate-200/70 bg-slate-50/40 opacity-90",
            b + " border-slate-200 bg-slate-100/80 text-slate-600",
        )
    return (
        "border border-slate-200 bg-slate-50/80",
        b + " border-slate-300 bg-slate-100 text-slate-700",
    )


def _vip_lifecycle_effective(ac: AbandonedCart) -> str:
    raw = getattr(ac, "vip_lifecycle_status", None)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return "abandoned"
    s = str(raw).strip().lower()
    if s in VIP_LIFECYCLE_VALUES:
        return s
    return "abandoned"


def _vip_dashboard_ac_in_scope(ac: AbandonedCart, dash_store: Optional[Any]) -> bool:
    """هل سلة ‎VIP‎ ضمن متجر لوحة الاستعادة (نفس منطق قائمة الأولوية)."""
    if dash_store is None:
        return False
    did = getattr(dash_store, "id", None)
    if did is None:
        return False
    try:
        vid = int(did)
    except (TypeError, ValueError):
        return False
    sid = getattr(ac, "store_id", None)
    if sid is None:
        return True
    try:
        return int(sid) == vid
    except (TypeError, ValueError):
        return False


def _vip_rows_same_logical_vip_cart(ac: AbandonedCart) -> list[AbandonedCart]:
    """نفس الجلسة أو ‎zid_cart_id‎ ضمن نفس ‎store_id‎ — لتوحيد الحالة على الصفوف المكررة."""
    sid = getattr(ac, "store_id", None)
    rs = (getattr(ac, "recovery_session_id", None) or "").strip()
    zi = (getattr(ac, "zid_cart_id", None) or "").strip()
    q = db.session.query(AbandonedCart).filter(AbandonedCart.vip_mode.is_(True))
    if sid is not None:
        q = q.filter(AbandonedCart.store_id == sid)
    else:
        q = q.filter(AbandonedCart.store_id.is_(None))
    if rs:
        q = q.filter(AbandonedCart.recovery_session_id == rs)
    elif zi:
        q = q.filter(AbandonedCart.zid_cart_id == zi)
    else:
        r = db.session.get(AbandonedCart, int(ac.id))
        return [r] if r is not None else []
    rows = list(q.all())
    return rows if rows else ([ac] if ac else [])


def _vip_apply_lifecycle_status(group: list[AbandonedCart], status: str) -> None:
    s = (status or "").strip().lower()
    for row in group:
        row.vip_lifecycle_status = s


VIP_PRIORITY_LC_ACTIVE_SQL = or_(
    AbandonedCart.vip_lifecycle_status.is_(None),
    AbandonedCart.vip_lifecycle_status == "abandoned",
    AbandonedCart.vip_lifecycle_status == "contacted",
)
VIP_PRIORITY_LC_TERMINAL_SQL = or_(
    AbandonedCart.vip_lifecycle_status == "closed",
    AbandonedCart.vip_lifecycle_status == "converted",
)


def _vip_pick_priority_cart_groups(
    full_rows: list[AbandonedCart],
) -> list[list[AbandonedCart]]:
    def _distinct_key(ac: AbandonedCart) -> str:
        rs = (ac.recovery_session_id or "").strip()
        if rs:
            return f"rs:{rs}"
        zi = (ac.zid_cart_id or "").strip()
        if zi:
            return f"zid:{zi}"
        return f"id:{int(ac.id)}"

    def _ts_norm(ac: AbandonedCart) -> datetime:
        t = ac.last_seen_at
        if t is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if t.tzinfo is None:
            return t.replace(tzinfo=timezone.utc)
        return t.astimezone(timezone.utc)

    def _group_latest_ts(grp: list[AbandonedCart]) -> datetime:
        if not grp:
            return datetime.min.replace(tzinfo=timezone.utc)
        return max(_ts_norm(ac) for ac in grp)

    groups: dict[str, list[AbandonedCart]] = defaultdict(list)
    for ac in full_rows:
        groups[_distinct_key(ac)].append(ac)

    sorted_group_keys = sorted(
        groups.keys(),
        key=lambda k: _group_latest_ts(groups[k]),
        reverse=True,
    )

    picked_groups: list[list[AbandonedCart]] = []
    for dk in sorted_group_keys:
        grp = groups[dk]
        grp_sorted = sorted(grp, key=_ts_norm, reverse=True)
        picked_groups.append(grp_sorted)
        if len(picked_groups) >= 24:
            break
    return picked_groups


def _vip_dashboard_cart_alert_dict_from_group(
    grp_sorted: list[AbandonedCart],
    dash_store: Optional[Any],
    *,
    recovery_card_tier: str = "vip",
) -> dict[str, Any]:
    ac = grp_sorted[0]
    tier = (recovery_card_tier or "vip").strip().lower()
    is_vip_card = tier != "normal"
    wa_digits = ""
    for ac_g in grp_sorted:
        if is_vip_card:
            raw_phone = _vip_dashboard_customer_phone_raw(
                ac_g,
                dash_store,
                prefer_persisted_cart_column_before_memory=False,
            )
        else:
            raw_phone = _normal_recovery_dashboard_resolve_customer_phone_raw(
                ac_g,
                dash_store,
            )
        cand = _normalize_customer_phone_for_wa_me(raw_phone)
        if cand:
            wa_digits = cand
            break
    zid = (ac.zid_cart_id or "").strip()
    cart_short = zid[:28] + ("…" if len(zid) > 28 else "") if zid else "—"
    st = ((ac.status or "").strip() or "—")[:48]
    hint_ar = ""
    if is_vip_card:
        hint_ar = (vip_offer_card_hint_ar(dash_store) if wa_digits else "") or ""
    override_msg = vip_offer_manual_contact_whatsapp_body(dash_store)
    if wa_digits and override_msg:
        contact_msg = override_msg
    else:
        contact_msg = _vip_customer_contact_whatsapp_message(ac)
    rs_log = (getattr(ac, "recovery_session_id", None) or "").strip()[:512]
    reason_tag_resolved = _reason_tag_for_abandoned_cart(ac)
    if is_vip_card:
        log.info(
            "[VIP PHONE RESOLVED] cart_id=%s session_id=%s customer_phone=%s",
            zid[:255] if zid else "-",
            rs_log if rs_log else "-",
            wa_digits if wa_digits else "-",
        )
        try:
            print(
                "[VIP PHONE RESOLVED]\n"
                "cart_id=" + (zid[:255] if zid else "-") + "\n"
                "session_id=" + (rs_log if rs_log else "-") + "\n"
                "customer_phone=" + (wa_digits if wa_digits else "-"),
                flush=True,
            )
        except OSError:
            pass
    else:
        log_normal_recovery_phone_line(
            session_id=rs_log if rs_log else "",
            cart_id=zid or None,
            reason_tag=reason_tag_resolved,
            phone=(wa_digits if wa_digits else None),
        )
    cart_link_raw = _vip_dashboard_cart_link(ac)
    merchant_replies_ar = _vip_merchant_ready_reply_bodies(cart_link=cart_link_raw)
    offer_ready = vip_offer_manual_contact_whatsapp_body(dash_store)
    lc = _vip_lifecycle_effective(ac)
    lbl = _VIP_LIFECYCLE_LABELS_AR.get(lc, _VIP_LIFECYCLE_LABELS_AR["abandoned"])
    card_cls, badge_cls = _vip_dashboard_lifecycle_card_and_badge_classes(lc)
    hide_actions = lc in ("closed", "converted")
    smart_action = get_cart_smart_action(
        {
            "is_vip": is_vip_card,
            "reason_tag": reason_tag_resolved,
            "vip_lifecycle_effective": lc if is_vip_card else "abandoned",
            "has_customer_phone": bool(wa_digits),
        }
    )
    smart_cta = smart_action_cta_target(smart_action["action_key"])
    smart_cta_target_display = "none" if not is_vip_card else smart_cta
    out_payload: dict[str, Any] = {
        "id": ac.id,
        "cart_value": float(ac.cart_value or 0.0),
        "cart_short": cart_short or "—",
        "last_seen": _format_reason_ts(ac.last_seen_at),
        "status": st,
        "vip_lifecycle_status": lc,
        "vip_lifecycle_label_ar": lbl,
        "vip_lifecycle_card_class": card_cls,
        "vip_lifecycle_badge_class": badge_cls,
        "vip_show_wa_opened_hint": lc == "contacted",
        "vip_lifecycle_hide_actions": hide_actions,
        "interactive": True,
        "customer_wa_phone": wa_digits,
        "contact_wa_message": contact_msg,
        "vip_offer_hint_ar": hint_ar,
        "merchant_reply_offer_ar": offer_ready,
        "merchant_reply_offer_b64": _vip_wa_prefill_utf8_base64(offer_ready),
        "merchant_reply_reminder_ar": merchant_replies_ar["reminder"],
        "merchant_reply_reminder_b64": _vip_wa_prefill_utf8_base64(
            merchant_replies_ar["reminder"]
        ),
        "merchant_reply_direct_ar": merchant_replies_ar["direct"],
        "merchant_reply_direct_b64": _vip_wa_prefill_utf8_base64(
            merchant_replies_ar["direct"]
        ),
        "smart_action": smart_action,
        "smart_cta_target": smart_cta,
        "smart_cta_target_display": smart_cta_target_display,
        "recovery_card_tier": "vip" if is_vip_card else "normal",
        "recovery_hide_vip_lifecycle_buttons": not is_vip_card,
    }
    if not is_vip_card:
        out_payload.update(_normal_recovery_phase_steps_payload(ac))
    return out_payload


def _vip_priority_alert_rows_for_lc_clause(lc_clause: Any, *, log_suffix: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    _ensure_store_widget_schema()
    db.create_all()
    _ensure_default_store_for_recovery()
    dash_store = _dashboard_recovery_store_row()
    dash_id_raw = getattr(dash_store, "id", None) if dash_store is not None else None
    scope_id: Optional[int] = None
    q = (
        db.session.query(AbandonedCart)
        .filter(AbandonedCart.vip_mode.is_(True))
        .filter(AbandonedCart.status == "abandoned")
        .filter(lc_clause)
    )
    if dash_id_raw is not None:
        try:
            vid = int(dash_id_raw)
            scope_id = vid
            q = q.filter(
                (AbandonedCart.store_id == vid) | (AbandonedCart.store_id.is_(None))  # type: ignore[union-attr]
            )
        except (TypeError, ValueError):
            pass

    _cleanup_duplicate_vip_abandoned_rows(store_id_scope=scope_id)

    full_rows = list(q.order_by(AbandonedCart.last_seen_at.desc()).all())

    def _distinct_key_plain(acr: AbandonedCart) -> str:
        rsv = (acr.recovery_session_id or "").strip()
        if rsv:
            return f"rs:{rsv}"
        zzz = (acr.zid_cart_id or "").strip()
        if zzz:
            return f"zid:{zzz}"
        return f"id:{int(acr.id)}"

    n_match = len({_distinct_key_plain(ac) for ac in full_rows})
    sid_log = "none" if dash_id_raw is None else str(dash_id_raw)
    log.info(
        "[VIP PRIORITY QUERY %s]\nstore_id=%s\ncount=%s", log_suffix, sid_log, str(n_match)
    )
    try:
        print(
            f"[VIP PRIORITY QUERY {log_suffix}] store_id={sid_log} count={n_match}",
            flush=True,
        )
    except OSError:
        pass

    for grp_sorted in _vip_pick_priority_cart_groups(full_rows):
        out.append(_vip_dashboard_cart_alert_dict_from_group(grp_sorted, dash_store))
    return out


def _vip_priority_cart_alert_list() -> list[dict[str, Any]]:
    """قائمة ‎VIP‎ النشطة (بانتظار التواصل / تم التواصل) للوحة الإعدادات."""
    try:
        return _vip_priority_alert_rows_for_lc_clause(VIP_PRIORITY_LC_ACTIVE_SQL, log_suffix="ACTIVE")
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("vip_priority_cart_alerts: db read failed: %s", e)
    return []


def _vip_priority_completed_cart_alert_list() -> list[dict[str, Any]]:
    """المغلقة والمُباعة — لعرض اختياري في اللوحة فقط."""
    try:
        return _vip_priority_alert_rows_for_lc_clause(
            VIP_PRIORITY_LC_TERMINAL_SQL, log_suffix="TERMINAL"
        )
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("vip_priority_completed_cart_alerts: db read failed: %s", e)
    return []


def _vip_cart_alerts_merchant_list() -> list[dict[str, Any]]:
    """توافق خلفي — يعرض الآن قائمة الأولوية الحقيقية فقط."""
    return _vip_priority_cart_alert_list()


def _normal_carts_dashboard_stats() -> dict[str, Any]:
    """أرقام قراءة فقط لواجهة «السلال العادية» — بدون تغيير منطق الاسترجاع."""
    out = {
        "normal_cart_count": 0,
        "normal_recovered_count": 0,
        "messages_sent_count": 0,
        "stopped_flow_count": 0,
    }
    try:
        _ensure_store_widget_schema()
        db.create_all()
        dash_store = _dashboard_recovery_store_row()
        if dash_store is None:
            return out
        dash_id_raw = getattr(dash_store, "id", None)
        slug = (getattr(dash_store, "zid_store_id", None) or "").strip()
        base_q = db.session.query(AbandonedCart).filter(AbandonedCart.vip_mode.is_(False))
        if dash_id_raw is not None:
            try:
                vid = int(dash_id_raw)
                base_q = base_q.filter(
                    (AbandonedCart.store_id == vid)
                    | (AbandonedCart.store_id.is_(None))  # type: ignore[union-attr]
                )
            except (TypeError, ValueError):
                pass
        q_abandoned = base_q.filter(AbandonedCart.status == "abandoned")
        out["normal_cart_count"] = int(q_abandoned.count() or 0)
        out["normal_recovered_count"] = int(
            base_q.filter(AbandonedCart.status == "recovered").count() or 0
        )
        if slug:
            out["messages_sent_count"] = int(
                db.session.query(func.count(CartRecoveryLog.id))
                .filter(
                    CartRecoveryLog.store_slug == slug,
                    CartRecoveryLog.status.in_(_NORMAL_RECOVERY_SENT_LOG_STATUSES),
                )
                .scalar()
                or 0
            )
            stop_clause = or_(
                CartRecoveryLog.status.like("skipped%"),
                CartRecoveryLog.status.like("stopped%"),
            )
            out["stopped_flow_count"] = int(
                db.session.query(func.count(CartRecoveryLog.id))
                .filter(CartRecoveryLog.store_slug == slug, stop_clause)
                .scalar()
                or 0
            )
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("normal_carts_dashboard_stats: %s", e)
    return out


def _normal_recovery_cart_alert_list(limit_groups: int = 15) -> list[dict[str, Any]]:
    """سلات غير ‎VIP‎ بحالة ‎abandoned‎ — نفس أدوات التواصل اليدوي مع اقتراح ذكي منفصل."""
    try:
        _ensure_store_widget_schema()
        db.create_all()
        _ensure_default_store_for_recovery()
        dash_store = _dashboard_recovery_store_row()
        dash_id_raw = getattr(dash_store, "id", None) if dash_store is not None else None
        q = db.session.query(AbandonedCart).filter(
            AbandonedCart.vip_mode.is_(False),
            AbandonedCart.status == "abandoned",
        )
        if dash_id_raw is not None:
            try:
                vid = int(dash_id_raw)
                q = q.filter(
                    (AbandonedCart.store_id == vid)
                    | (AbandonedCart.store_id.is_(None))  # type: ignore[union-attr]
                )
            except (TypeError, ValueError):
                pass
        full_rows = list(
            q.order_by(AbandonedCart.last_seen_at.desc()).limit(240).all()
        )
        out: list[dict[str, Any]] = []
        for grp_sorted in _vip_pick_priority_cart_groups(full_rows)[:limit_groups]:
            out.append(
                _vip_dashboard_cart_alert_dict_from_group(
                    grp_sorted,
                    dash_store,
                    recovery_card_tier="normal",
                )
            )
        return out
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("normal_recovery_cart_alerts: db read failed: %s", e)
    return []


def _recovery_sales_trend_last_7_days() -> list[dict[str, Any]]:
    """
    مجموع ‎cart_value‎ للسلات ‎status=recovered‎ حسب يوم ‎recovered_at‎ (UTC)؛ ‎7‎ أيام متتالية حتى اليوم.
    """
    today = datetime.now(timezone.utc).date()
    start_day = today - timedelta(days=6)
    day_keys = [(start_day + timedelta(days=i)).isoformat() for i in range(7)]
    totals: dict[str, float] = {k: 0.0 for k in day_keys}
    start_dt = datetime.combine(start_day, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    try:
        db.create_all()
        q = (
            db.session.query(AbandonedCart.recovered_at, AbandonedCart.cart_value)
            .filter(AbandonedCart.status == "recovered")
            .filter(AbandonedCart.recovered_at.isnot(None))
            .filter(AbandonedCart.recovered_at >= start_dt)
            .filter(AbandonedCart.recovered_at < end_dt)
        )
        for recovered_at, cart_value in q.all():
            dt = recovered_at
            if dt is None:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            dk = dt.date().isoformat()
            if dk in totals:
                totals[dk] += float(cart_value or 0.0)
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("recovery-trend: %s", e)
    return [{"date": k, "value": round(totals[k], 2)} for k in day_keys]


@app.get("/api/dashboard/recovery-trend")
def api_dashboard_recovery_trend():
    """قراءة فقط — اتجاه المبيعات المسترجعة (مجموع قيمة السلة) لآخر ‎7‎ أيام."""
    return _recovery_sales_trend_last_7_days()


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
            _ensure_store_widget_schema()
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
                        "kind": "activity",
                        "session_id": (r.session_id or "")[:32]
                        + ("…" if r.session_id and len(r.session_id) > 32 else ""),
                        "reason_key": k,
                        "reason_ar": label,
                        "product": product_hint,
                        "time_str": _format_reason_ts(r.updated_at),
                    }
                )
            if len(live_rows) > 14:
                live_rows = live_rows[:14]
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
                "kind": "activity",
                "session_id": "dem…sess_01",
                "reason_key": "price",
                "reason_ar": "السعر",
                "product": "سماعة",
                "time_str": "2026-04-20 14:32",
            },
            {
                "kind": "activity",
                "session_id": "dem…sess_02",
                "reason_key": "warranty",
                "reason_ar": "الضمان",
                "product": "—",
                "time_str": "2026-04-20 13:10",
            },
            {
                "kind": "activity",
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
    """توافق خلفي — التوقيت والقوالب ضمن «السلال العادية»."""
    return RedirectResponse(
        url="/dashboard/normal-carts#cf-normal-timing", status_code=302
    )


@app.get("/dashboard/normal-carts")
def dashboard_normal_carts(request: Request):
    """السلال العادية — مراقبة أتمتة، قوالب حسب السبب، وتوقيت التسلسل."""
    from services.cartflow_observability_runtime import runtime_health_snapshot_readonly

    normal_recovery_alerts = _normal_recovery_cart_alert_list()
    normal_stats = dict(_normal_carts_dashboard_stats())
    normal_stats["normal_monitoring_card_count"] = len(normal_recovery_alerts)
    return templates.TemplateResponse(
        request,
        "normal_carts_dashboard.html",
        {
            "request": request,
            "normal_recovery_alerts": normal_recovery_alerts,
            "normal_stats": normal_stats,
            "cartflow_runtime_health": runtime_health_snapshot_readonly(),
        },
    )


@app.get("/dashboard/normal-recovery")
def dashboard_normal_recovery_legacy(request: Request):
    """توافق خلفي لمسار العنوان السابق."""
    return RedirectResponse(url="/dashboard/normal-carts", status_code=302)


@app.get("/dashboard/vip-cart-settings")
def dashboard_vip_cart_settings(request: Request):
    """السلال المميزة (VIP) — عتبة عبر ‎GET/POST /api/recovery-settings‎؛ قائمة أولوية حقيقية فقط."""
    qcomp = (request.query_params.get("vip_show_completed") or "").strip().lower()
    vip_show_completed = qcomp in ("1", "true", "yes", "on")
    vip_priority_alerts = _vip_priority_cart_alert_list()
    vip_completed_alerts = (
        _vip_priority_completed_cart_alert_list() if vip_show_completed else []
    )
    merchant_followup_actions = merchant_followup_actions_for_dashboard(limit=10)
    return templates.TemplateResponse(
        request,
        "vip_cart_settings.html",
        {
            "request": request,
            "vip_priority_alerts": vip_priority_alerts,
            "vip_completed_alerts": vip_completed_alerts,
            "vip_show_completed": vip_show_completed,
            "merchant_followup_actions": merchant_followup_actions,
        },
    )


@app.get("/api/merchant-followup-actions")
def api_merchant_followup_actions():
    """قائمة قراءة فقط لإجراءات المتابعة اليدوية (ردود إيجابية واتساب)."""
    try:
        actions = merchant_followup_actions_for_dashboard(limit=10)
        return j({"ok": True, "actions": actions})
    except (OSError, TypeError, ValueError) as e:
        log.warning("api merchant-followup-actions: %s", e)
        return j({"ok": False, "error": "failed", "actions": []}, 500)


@app.post("/api/merchant-followup-actions/{action_id}/complete")
def api_merchant_followup_action_complete(action_id: int):
    """تمييز إجراء المتابعة كمكتمل — يدوي من لوحة التاجر."""
    try:
        db.create_all()
        row = db.session.get(MerchantFollowupAction, int(action_id))
        if row is None:
            return j({"ok": False, "error": "لم يتم العثور على الإجراء"}, 404)
        if str(row.status or "").strip() != STATUS_NEEDS_MERCHANT_FOLLOWUP:
            return j({"ok": False, "error": "لا يمكن إتمام هذا الإجراء"}, 400)
        if not _merchant_followup_action_row_visible_for_dashboard(row):
            return j({"ok": False, "error": "غير مسموح"}, 403)
        row.status = STATUS_MERCHANT_FOLLOWUP_COMPLETED
        row.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return j({"ok": True})
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("api merchant-followup complete: %s", e)
        return j({"ok": False, "error": "failed"}, 500)


@app.get("/dashboard/cartflow-messages")
def dashboard_cartflow_messages(request: Request):
    """إعادة توجيه — دمج إعدادات استعادة السلة ضمن السلال العادية."""
    return RedirectResponse(
        url="/dashboard/normal-carts#cart-recovery-settings", status_code=302
    )


@app.get("/dashboard/exit-intent-settings")
def dashboard_exit_intent_settings(request: Request):
    """رسالة قبل الخروج فقط — نفس ‎GET/POST /api/recovery-settings‎ (تحديث جزئي)."""
    return templates.TemplateResponse(
        request,
        "exit_intent_settings.html",
        {"request": request},
    )


@app.get("/dashboard/cart-recovery-messages")
def dashboard_cart_recovery_messages(request: Request):
    """توافق خلفي — القوالب ضمن «السلال العادية»."""
    return RedirectResponse(
        url="/dashboard/normal-carts#reason-recovery-settings", status_code=302
    )


@app.get("/dashboard/general-settings")
def dashboard_general_settings(request: Request):
    """إعدادات عامة — واتساب المتجر، ظهور الودجيت، ومظهر الودجيت."""
    return templates.TemplateResponse(
        request,
        "general_settings.html",
        {"request": request},
    )


@app.get("/dashboard/widget-customization")
def dashboard_widget_customization(request: Request):
    """توافق خلفي — تخصيص الودجيت ضمن إعدادات عامة."""
    return RedirectResponse(
        url="/dashboard/general-settings#cf-widget-custom", status_code=302
    )


def _vip_reason_tag_from_abandoned_cart(ac: Optional[AbandonedCart]) -> Optional[str]:
    """قراءة ‎reason_tag‎ من ‎AbandonedCart.raw_payload‎ (JSON) لتضمينه في رسالة تنبيه التاجر."""
    if ac is None:
        return None
    rp = getattr(ac, "raw_payload", None)
    if not isinstance(rp, str) or not rp.strip():
        return None
    try:
        d = json.loads(rp)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    t = (d.get("reason_tag") or "").strip()
    return t or None


_MERCHANT_FOLLOWUP_REASON_TAG_SYNONYMS: dict[str, str] = {
    "price_high": "price",
    "shipping_cost": "shipping",
    "quality_uncertainty": "quality",
    "delivery_time": "shipping",
}


def _merchant_followup_prefill_whatsapp_body(*, cart_link: str) -> str:
    """نص جاهز لـ‎ wa.me‎ (يدوي) بعد رد إيجابي من العميل."""
    base = "هلا 👋\nوصلنا ردك، ونقدر نساعدك تكمل الطلب الآن."
    link = (cart_link or "").strip()
    if link:
        return base + "\nرابط السلة:\n" + link
    return base


def _merchant_followup_reason_ar(reason: Optional[str]) -> str:
    r = (reason or "").strip()
    if r == REASON_CUSTOMER_REPLIED_YES:
        return "رد العميل بنعم"
    return r or "—"


def _merchant_followup_reason_tag_label_ar(raw_tag: Optional[str]) -> str:
    tag = (raw_tag or "").strip()
    if not tag:
        return ""
    key = _MERCHANT_FOLLOWUP_REASON_TAG_SYNONYMS.get(tag.lower(), tag.lower())
    return _REASON_LABELS_AR.get(key, tag)


def _merchant_followup_dashboard_scope_filter(q):  # type: ignore
    dash = _dashboard_recovery_store_row()
    if dash is None or getattr(dash, "id", None) is None:
        return q
    vid = int(dash.id)
    return q.filter(
        or_(
            MerchantFollowupAction.store_id.is_(None),
            MerchantFollowupAction.store_id == vid,
        )
    )


def _merchant_followup_row_to_payload(row: MerchantFollowupAction) -> dict[str, Any]:
    ac: Optional[AbandonedCart] = None
    aid = getattr(row, "abandoned_cart_id", None)
    if aid is not None:
        try:
            ac = db.session.get(AbandonedCart, int(aid))
        except (SQLAlchemyError, OSError, TypeError, ValueError):
            db.session.rollback()
            ac = None
    cart_link = _vip_dashboard_cart_link(ac) if ac is not None else ""
    reason_tag_raw = _vip_reason_tag_from_abandoned_cart(ac)
    cv: Optional[float] = None
    if ac is not None and getattr(ac, "cart_value", None) is not None:
        try:
            cv = float(ac.cart_value)
        except (TypeError, ValueError):
            cv = None
    wa_digits = _normalize_customer_phone_for_wa_me(row.customer_phone)
    return {
        "id": row.id,
        "customer_phone": (row.customer_phone or "").strip(),
        "customer_wa_digits": wa_digits,
        "status": row.status,
        "status_ar": "جاهز للتواصل",
        "reason": row.reason,
        "reason_ar": _merchant_followup_reason_ar(getattr(row, "reason", None)),
        "inbound_message": (row.inbound_message or "").strip(),
        "replied_at": _format_reason_ts(row.created_at),
        "cart_value": cv,
        "reason_tag_raw": reason_tag_raw,
        "reason_tag_ar": _merchant_followup_reason_tag_label_ar(reason_tag_raw),
        "cart_link": cart_link.strip(),
        "contact_prefill_body": _merchant_followup_prefill_whatsapp_body(
            cart_link=cart_link
        ),
    }


def merchant_followup_actions_for_dashboard(limit: int = 10) -> list[dict[str, Any]]:
    """أحدث ‎MerchantFollowupAction‎ بحالة تحتاج متابعة — نطاق المتجر الحالي للوحة."""
    out: list[dict[str, Any]] = []
    try:
        db.create_all()
        _ensure_store_widget_schema()
        q = db.session.query(MerchantFollowupAction).filter(
            MerchantFollowupAction.status == STATUS_NEEDS_MERCHANT_FOLLOWUP,
        )
        q = _merchant_followup_dashboard_scope_filter(q)
        rows = (
            q.order_by(MerchantFollowupAction.created_at.desc())
            .limit(max(1, min(int(limit), 50)))
            .all()
        )
        out = [_merchant_followup_row_to_payload(r) for r in rows]
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("merchant followup dashboard list failed: %s", e)
    return out


def _merchant_followup_action_row_visible_for_dashboard(
    row: MerchantFollowupAction,
) -> bool:
    dash = _dashboard_recovery_store_row()
    if dash is None or getattr(dash, "id", None) is None:
        return True
    vid = int(dash.id)
    sid = getattr(row, "store_id", None)
    if sid is None:
        return True
    try:
        return int(sid) == vid
    except (TypeError, ValueError):
        return False


def _store_row_for_abandoned_cart(ac: Optional[AbandonedCart]) -> Optional[Store]:
    """متجر السلة أو آخر متجر افتراضي — إرسال تنبيهات التاجر فقط لا يفسد مسارات أخرى."""
    if ac is None:
        return None
    try:
        sid = getattr(ac, "store_id", None)
        if sid is not None:
            st = db.session.get(Store, int(sid))
            if st is not None:
                return st
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return None
    return _load_latest_store_for_recovery()


def _resolve_store_for_vip_merchant_alert(ac: AbandonedCart) -> Optional[Store]:
    """
    متجر لتنبيه التاجر VIP: متجر السلة إن وفّر رقم/‎URL‎ جهة؛ وإلا آخر متجر فيه جهة اتصال
    (‎recovery settings‎ غالباً تحدّث أحدث ‎Store‎).
    """
    primary = _store_row_for_abandoned_cart(ac)
    if primary is not None:
        phone, _ = resolve_merchant_whatsapp_phone(primary)
        if phone:
            return primary
    latest = _load_latest_store_for_recovery()
    if latest is None:
        return primary
    phone2, _ = resolve_merchant_whatsapp_phone(latest)
    if phone2:
        return latest
    return primary


@app.post("/api/dashboard/vip-cart/{cart_row_id}/merchant-alert")
def api_dashboard_vip_cart_merchant_alert(cart_row_id: int):
    """إرسال واتساب للتاجر فقط (VIP) من لوحة السلال المميزة — لا عميل."""
    log.info("[VIP MANUAL SEND CLICKED] abandoned_cart_row_id=%s", cart_row_id)
    try:
        db.create_all()
        _ensure_store_widget_schema()
        ac = db.session.get(AbandonedCart, int(cart_row_id))
        if ac is None:
            return j({"ok": False, "error": "لم يتم العثور على السلة"}, 404)
        if not bool(getattr(ac, "vip_mode", False)):
            return j({"ok": False, "error": "هذه السلة ليست في وضع VIP"}, 400)
        if str(getattr(ac, "status", "") or "").strip() == "recovered":
            return j({"ok": False, "error": "السلة مستردة بالفعل"}, 400)

        cart_sid = getattr(ac, "store_id", None)
        store_obj = _resolve_store_for_vip_merchant_alert(ac)
        resolved_id = getattr(store_obj, "id", None) if store_obj is not None else None
        sw_raw = getattr(store_obj, "store_whatsapp_number", None) if store_obj is not None else None
        sw_disp = (sw_raw or "").strip() if isinstance(sw_raw, str) else ""
        log.info(
            "[VIP STORE RESOLUTION] cart_store_id=%s resolved_store_id=%s store_whatsapp_number=%s",
            cart_sid,
            resolved_id,
            sw_disp,
        )
        if store_obj is None:
            log.warning("[VIP MERCHANT ALERT FAILED] reason=no_store")
            return j(
                {"ok": False, "error": "لا يوجد رقم واتساب للمتجر", "detail": "no_store"},
                400,
            )

        cv = float(ac.cart_value or 0.0)
        rtag = _vip_reason_tag_from_abandoned_cart(ac)
        alert_body = build_vip_merchant_alert_body(
            cv,
            reason_tag=rtag,
            dashboard_link=vip_dashboard_review_link(),
        )
        out = try_send_vip_merchant_whatsapp_alert(store_obj, message=alert_body)

        if out.get("ok") is True:
            return j(
                {
                    "ok": True,
                    "message": "تم إرسال تنبيه التاجر",
                },
                200,
            )

        err_code = str(out.get("error") or "").strip()
        src = str(out.get("source") or "").strip()

        if err_code == "no_merchant_phone" or (
            src in ("no_merchant_contact", "url_unparsed", "no_store")
        ):
            user_msg = "لا يوجد رقم واتساب للمتجر"
            return j(
                {
                    "ok": False,
                    "error": user_msg,
                    "detail": err_code or src,
                },
                400,
            )

        return j(
            {
                "ok": False,
                "error": err_code or "فشل إرسال رسالة الواتساب للتاجر",
                "detail": src,
            },
            502,
        )
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        log.warning(
            "[VIP MERCHANT ALERT FAILED] reason=endpoint_exception err=%s",
            str(e),
            exc_info=True,
        )
        return j({"ok": False, "error": "خطأ غير متوقع في الخادم"}, 500)


@app.post("/api/dashboard/vip-cart/{cart_row_id}/lifecycle")
def api_dashboard_vip_cart_lifecycle(
    cart_row_id: int, payload: Dict[str, Any] = Body(...)
) -> Any:
    """تحديث حالة متابعة VIP في لوحة التحكم فقط — لا يغيّر مسار إرسال واتساب."""
    try:
        db.create_all()
        _ensure_store_widget_schema()
        new_raw = (payload.get("status") or "").strip().lower()
        allowed_in = frozenset({"contacted", "closed", "converted"})
        if new_raw not in allowed_in:
            return j({"ok": False, "error": "حالة غير صالحة"}, 400)
        ac = db.session.get(AbandonedCart, int(cart_row_id))
        if ac is None:
            return j({"ok": False, "error": "لم يتم العثور على السلة"}, 404)
        if not bool(getattr(ac, "vip_mode", False)):
            return j({"ok": False, "error": "هذه السلة ليست في وضع VIP"}, 400)
        if str(getattr(ac, "status", "") or "").strip() == "recovered":
            return j({"ok": False, "error": "السلة مستردة بالفعل"}, 400)
        dash_store = _dashboard_recovery_store_row()
        if not _vip_dashboard_ac_in_scope(ac, dash_store):
            return j({"ok": False, "error": "غير مسموح"}, 403)

        cur = _vip_lifecycle_effective(ac)
        if cur == new_raw:
            return j(
                {
                    "ok": True,
                    "status": new_raw,
                    "label_ar": _VIP_LIFECYCLE_LABELS_AR.get(new_raw, ""),
                },
                200,
            )
        if cur in ("closed", "converted"):
            return j({"ok": False, "error": "حالة نهائية"}, 400)

        group = _vip_rows_same_logical_vip_cart(ac)
        _vip_apply_lifecycle_status(group, new_raw)
        db.session.commit()
        return j(
            {
                "ok": True,
                "status": new_raw,
                "label_ar": _VIP_LIFECYCLE_LABELS_AR.get(new_raw, ""),
            },
            200,
        )
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("vip_cart_lifecycle: %s", e)
        return j({"ok": False, "error": "فشل التحديث"}, 500)


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
    """الصفحة العامة — واجهة تسويق CartFlow (عربي، RTL مع تخطيط مطابق للمرجع)."""
    return templates.TemplateResponse(
        request,
        "cartflow_landing.html",
        {"request": request},
    )


@app.get("/register")
def register_placeholder(request: Request):
    """صفحة تسجيل مؤقتة — روابط CTA من الصفحة العامة (بدون OTP/واتساب)."""
    return templates.TemplateResponse(
        request,
        "register_placeholder.html",
        {"request": request},
    )


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
