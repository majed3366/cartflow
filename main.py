# -*- coding: utf-8 -*-
"""
CartFlow — تطبيق Flask الرئيسي لاستقبال الويبهوك ولوحة التاجر.
"""
import base64
import hashlib
import hmac
import os
import json
import traceback
from typing import Any, Optional, Tuple

import anthropic  # مكتبة Anthropic الرسمية لطلبات Claude
import requests  # طلبات ‎HTTP‎ / ‎Zid / واتساب‎
from dotenv import load_dotenv
from extensions import db
from flask import Flask, request, render_template, jsonify, Response
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

# تحميل متغيرات البيئة من ملف ‎.env (إن وُجد) قبل إنشاء التطبيق
load_dotenv()

# إنشاء كائن تطبيق Flask — نقطة دخول WSGI لـ Gunicorn: ‎app‎
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-in-production")

# قاعدة البيانات: ‎DATABASE_URL‎ من Railway/البيئة فقط (بدون تثبيت مضيف يدوي)
# إن وُجد ‎DATABASE_URL‎ نستخدمه كما يعطيه النظام؛ وإلا ‎SQLite‎ للتطوير المحلي
_db = os.getenv("DATABASE_URL")
_database_url = (_db or "").strip() or "sqlite:///local.db"
if _database_url.startswith("postgres://"):
    _database_url = _database_url.replace("postgres://", "postgresql://", 1)
if _database_url.startswith("postgresql+asyncpg://"):
    _database_url = _database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = _database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# تسجيل النماذج (يجب بعد ‎init_app‎)
from models import AbandonedCart, Store  # noqa: E402

# تسمية مودل Claude (يمكن تغييره من البيئة)
DEFAULT_CLAUDE_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

ZID_OAUTH_BASE = (os.getenv("ZID_OAUTH_BASE") or "https://oauth.zid.sa").rstrip("/")
ZID_PROFILE_API = os.getenv("ZID_PROFILE_API_URL", "https://api.zid.sa/v1/managers/account/profile")

# --- دعم القراءة من الحقول العامة (يُستدعى قبل ‎extract_cart_url‎) ---


# --- ‎CSP: السماح بتضمين التطبيق داخل لوحة زد (بدون ‎X-Frame-Options: DENY‎) ---
@app.after_request
def set_embed_csp(response: Response) -> Response:
    # ‎frame-ancestors‎ يسمح بـ ‎https://web.zid.sa‎ فقط
    csp = "frame-ancestors 'self' https://web.zid.sa"
    response.headers["Content-Security-Policy"] = csp
    response.headers.pop("X-Frame-Options", None)
    return response


def verify_zid_webhook_signature(
    body: bytes, header_sig: Optional[str], secret: str
) -> bool:
    # ‎HMAC-SHA256‎ للجسد الخام — مقارنة آمنة (لا تسجيل الأسرار)
    if not secret or not body or not header_sig or not header_sig.strip():
        return False
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256)
    hexd = mac.hexdigest()
    b64d = base64.b64encode(mac.digest()).decode("ascii")
    s = header_sig.strip()
    if s.lower().startswith("sha256="):
        s = s[7:].strip()
    if hmac.compare_digest(hexd, s) or hmac.compare_digest(b64d, s):
        return True
    return False


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


def save_or_update_store(zid_store_id: str, access_token: str) -> None:
    sid = (zid_store_id or "").strip()
    if not sid:
        return
    row = Store.query.filter_by(zid_store_id=sid).first()
    if row is None:
        row = Store(zid_store_id=sid, access_token=access_token, is_active=True)
        db.session.add(row)
    else:
        row.access_token = access_token
        row.is_active = True
    db.session.commit()


def zid_token_exchange_by_code(code: str) -> tuple[dict, int]:
    # استبدال ‎code‎ بـ ‎access_token‎ (زد) وحفظ ‎Store‎ — نتيجة قابلة لـ ‎Flask / FastAPI‎
    client_id = (os.getenv("CLIENT_ID") or "").strip()
    client_secret = (os.getenv("CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        return ({"ok": False, "error": "oauth_not_configured"}, 500)
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }
    redir = (os.getenv("OAUTH_REDIRECT_URI") or "").strip()
    if redir:
        payload["redirect_uri"] = redir
    try:
        tr = requests.post(
            f"{ZID_OAUTH_BASE}/oauth/token",
            data=payload,
            timeout=30,
        )
    except requests.RequestException:
        return ({"ok": False, "error": "token_request_failed"}, 502)
    if tr.status_code // 100 != 2:
        print("[Zid OAuth] token endpoint HTTP error", tr.status_code)
        return ({"ok": False, "error": "token_exchange_failed"}, 400)
    try:
        data = tr.json()
    except Exception:  # noqa: BLE001
        return ({"ok": False, "error": "invalid_token_response"}, 400)
    if not isinstance(data, dict):
        return ({"ok": False, "error": "invalid_token_response"}, 400)
    access_token = data.get("access_token")
    if not access_token or not isinstance(access_token, str):
        return ({"ok": False, "error": "missing_access_token"}, 400)
    zid = _parse_zid_store_id_from_token(data)
    if not zid:
        zid = _fetch_zid_store_id_from_profile(access_token)
    if not zid:
        return ({"ok": False, "error": "store_id_unresolved"}, 400)
    try:
        save_or_update_store(zid, access_token)
    except SQLAlchemyError:
        db.session.rollback()
        return ({"ok": False, "error": "db_error"}, 500)
    return ({"ok": True}, 200)


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
        status = "Recovered"
    elif st_raw in ("recovered", "completed", "paid", "success"):
        status = "Recovered"
    elif st_raw in ("sent", "message_sent", "delivered"):
        status = "Sent"
    else:
        status = "Pending"

    cart_url = extract_cart_url(payload)

    return {
        "cart_id": cart_id,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "cart_value": cart_value,
        "status": status,
        "cart_url": cart_url,
    }


def upsert_abandoned_cart_from_payload(payload: dict) -> Tuple[bool, str, Optional[AbandonedCart]]:
    # إدراج أو تحديث سجل ‎AbandonedCart‎ حسب ‎cart_id‎ ثم ‎commit‎
    fields = normalize_zid_cart_fields(payload)
    if not fields["cart_id"]:
        return False, "missing cart_id", None
    row = AbandonedCart.query.filter_by(cart_id=fields["cart_id"]).first()
    if row is None:
        row = AbandonedCart(
            cart_id=fields["cart_id"],
            customer_name=fields["customer_name"],
            customer_phone=fields["customer_phone"],
            cart_value=fields["cart_value"],
            status=fields["status"],
            cart_url=fields.get("cart_url") or "",
        )
        db.session.add(row)
    else:
        row.customer_name = fields["customer_name"] or row.customer_name
        row.customer_phone = fields["customer_phone"] or row.customer_phone
        if fields["cart_value"] != 0.0 or row.cart_value == 0.0:
            row.cart_value = fields["cart_value"]
        if fields.get("cart_url"):
            row.cart_url = fields["cart_url"]
        # ‎Recovered‎ أعلى أولوية — لا نعيد ‎Pending‎ فوق ‎Sent‎ أثناء تكرار الويبهوك
        new = fields["status"]
        if new == "Recovered":
            row.status = "Recovered"
        elif new == "Sent":
            row.status = "Sent"
        else:
            if row.status not in ("Sent", "Recovered"):
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


# --- المسارات ---

@app.get("/auth/callback")
def auth_callback():
    # ‎OAuth 2.0‎: بدون ‎code‎ نثبت أن المسار يعمل؛ مع ‎code‎ نستبدل برمز زد
    code = (request.args.get("code") or "").strip()
    if not code:
        return jsonify({"status": "callback route exists"})
    body, status = zid_token_exchange_by_code(code)
    return jsonify(body), status


@app.route("/dashboard", methods=["GET"])
def dashboard():
    # تجميع إحصائيات + آخر 5 سلات (حسب ‎created_at‎ تنازلياً)
    total_carts = AbandonedCart.query.count()
    rev = (
        db.session.query(func.coalesce(func.sum(AbandonedCart.cart_value), 0.0))
        .filter(AbandonedCart.status == "Recovered")
        .scalar()
    )
    total_revenue = float(rev) if rev is not None else 0.0
    recovered = AbandonedCart.query.filter_by(status="Recovered").count()
    recent_carts = (
        AbandonedCart.query.order_by(AbandonedCart.created_at.desc()).limit(5).all()
    )
    return render_template(
        "index.html",
        total_carts=total_carts,
        total_revenue=total_revenue,
        recovered_carts=recovered,
        recent_carts=recent_carts,
    )


@app.post("/api/carts/<int:row_id>/send")
def send_cart_manual(row_id: int):
    # إعادة إرسال يدوي للتجريب: نفس ‎send_whatsapp_message‎ ثم ‎Sent‎
    row = db.session.get(AbandonedCart, row_id)
    if row is None:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if row.status == "Recovered":
        return jsonify({"ok": False, "error": "already_recovered"}), 400
    cart_link = (row.cart_url or os.getenv("WHATSAPP_FALLBACK_CART_URL") or "https://example.com/cart").strip()
    msg = row.generated_message or DEFAULT_RECOVERY_SMS
    ok, err, _r = send_whatsapp_message(row.customer_phone, msg, cart_link)
    if ok:
        if row.status != "Recovered":
            row.status = "Sent"
        db.session.commit()
    return jsonify({"ok": ok, "error": err})


@app.route("/webhook/zid", methods=["POST"])
def zid_webhook():
    # التحقق من ‎X-Zid-Signature‎ قبل أي معالجة
    raw = request.get_data()
    secret = (os.getenv("ZID_WEBHOOK_SECRET") or "").strip()
    sig = request.headers.get("X-Zid-Signature")
    if not secret or not verify_zid_webhook_signature(raw, sig, secret):
        return jsonify({"error": "unauthorized"}), 401
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    print("[Zid Webhook]", json.dumps(payload, ensure_ascii=False, indent=2))
    out: dict[str, Any] = {"ok": True}
    if not isinstance(payload, dict):
        return jsonify(out), 200
    try:
        ok, err, row = upsert_abandoned_cart_from_payload(payload)
        if not ok:
            out["ok"] = False
            out["message"] = err
        elif row is not None:
            # ‎Recovered‎: سجل مكتمل — بلا توليد ولا واتساب
            if row.status == "Recovered":
                pass
            # ‎Sent‎: تم الإرسال مسبقاً (تجنّب تكرار ‎Claude/واتساب)‎
            elif row.status == "Sent":
                pass
            else:
                cart_items = extract_cart_items_summary(payload)
                ai = generate_recovery_message(
                    row.customer_name,
                    cart_items,
                    float(row.cart_value or 0.0),
                )
                row.generated_message = ai
                db.session.add(row)
                db.session.commit()
                # إرسال ‎CTA + إكمال الشراء‎ ثم ‎Sent‎ عند نجاح ‎Graph API‎
                cart_link = (row.cart_url or extract_cart_url(payload) or "").strip()
                w_ok, w_err, _wa = send_whatsapp_message(
                    row.customer_phone,
                    row.generated_message or DEFAULT_RECOVERY_SMS,
                    cart_link,
                )
                if w_ok:
                    row.status = "Sent"
                    db.session.add(row)
                    db.session.commit()
                else:
                    out["whatsapp_error"] = w_err
    except SQLAlchemyError:
        db.session.rollback()
        out["ok"] = False
        out["message"] = "db_error"
        out["error"] = traceback.format_exc()
        print("[Zid Webhook DB Error]", out["error"])
    return jsonify(out), 200


@app.get("/")
def home():
    # جذر التطبيق: استجابة بسيطة (تضمين في لوحة زد دون الاعتماد على ‎/dashboard‎ أو قاعدة البيانات)
    return jsonify({"status": "app is running"})


# لا نستدعي ‎_ensure_db_schema()‎ عند التحميل — يتجنب الاتصال بقاعدة البيانات عند إقلاع ‎Gunicorn‎

if __name__ == "__main__":
    # تشغيل وضع التطوير فقط؛ في الإنتاج: ‎gunicorn main:app‎
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
