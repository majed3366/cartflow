# -*- coding: utf-8 -*-
"""
واتساب للاسترجاع: الإرسال الفعلي عبر Twilio (‎TWILIO_*‎).
توقيت «متى نرسل؟» — يدعم حقول ‎Store.recovery_*‎ عند تمرير ‎store‎.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from twilio.rest import Client

from config_system import get_cartflow_config

logger = logging.getLogger(__name__)


def _resolved_store_slug(store: Optional[Any]) -> Optional[str]:
    """مفتاح ‎CartFlow‎: ‎slug‎ أو ‎zid_store_id‎ عند حضور سلسلة."""
    if store is None:
        return None
    sl = getattr(store, "slug", None)
    if isinstance(sl, str) and sl.strip():
        return sl.strip()[:255]
    zid = getattr(store, "zid_store_id", None)
    if isinstance(zid, str) and zid.strip():
        return zid.strip()[:255]
    return None


def _recovery_config(store: Optional[Any]) -> Dict[str, Any]:
    """طبقة ‎Layer C‎ — قراءة فقط؛ ‎demo‎ عندما لا يوجد كائن متجر."""
    if store is None:
        return get_cartflow_config(store_slug="demo")
    return get_cartflow_config(store_slug=_resolved_store_slug(store))


def _min_quiet_from_store_legacy(store: Optional[Any]) -> timedelta:
    """
    منطق زمن السكون قبل حقن الإعداد من ‎config_system‎ (انسجام مع الواجهات الاختبارية بدون slug).
    """
    if store is None:
        return timedelta(minutes=2)
    delay = getattr(store, "recovery_delay", None)
    raw_unit = getattr(store, "recovery_delay_unit", None) or "minutes"
    if isinstance(raw_unit, str):
        unit = raw_unit.strip().lower()
    else:
        unit = "minutes"
    if delay is None:
        d = 2
    else:
        try:
            d = int(delay)
        except (TypeError, ValueError):
            d = 2
    d = max(0, d)
    if unit == "hours":
        total_minutes = d * 60
    elif unit == "days":
        total_minutes = d * 1440
    else:
        total_minutes = d
    return timedelta(minutes=total_minutes)


def _min_quiet_from_store_settings(store: Optional[Any]) -> timedelta:
    """
    يحوّل ‎recovery_delay + recovery_delay_unit‎ إلى ‎timedelta‎.
    عند وجود مفتاح متجر (‎slug / zid_store_id‎) يُطبَّق جزء الدقائق من ‎get_cartflow_config‎.
    وإلا يُستخدم المنطق السابق لعدم تحطيم الاختبارات بالوسائط الموصوفة بدون هوية متجر.
    """
    slug = None if store is None else _resolved_store_slug(store)

    if store is None:
        cfg = _recovery_config(None)
        recovery_delay_minutes = int(cfg.get("recovery_delay_minutes", 1))
        return timedelta(minutes=max(0, recovery_delay_minutes))

    if slug is None:
        return _min_quiet_from_store_legacy(store)

    raw_unit = getattr(store, "recovery_delay_unit", None) or "minutes"
    if isinstance(raw_unit, str):
        unit = raw_unit.strip().lower()
    else:
        unit = "minutes"

    cfg = _recovery_config(store)
    recovery_delay_minutes_cfg = max(0, int(cfg.get("recovery_delay_minutes", 1)))

    if unit == "hours" or unit == "days":
        delay = getattr(store, "recovery_delay", None)
        if delay is None:
            d = 2
        else:
            try:
                d = int(delay)
            except (TypeError, ValueError):
                d = 2
        d = max(0, d)
        if unit == "hours":
            total_minutes = d * 60
        else:
            total_minutes = d * 1440
        return timedelta(minutes=total_minutes)

    return timedelta(minutes=recovery_delay_minutes_cfg)


def recovery_delay_to_seconds(store: Optional[Any]) -> float:
    """
    يحوّل ‎recovery_delay + recovery_delay_unit‎ إلى ثوانٍ (نفس منطق ‎_min_quiet_from_store_settings‎).
    """
    return _min_quiet_from_store_settings(store).total_seconds()


def _max_recovery_attempts(store: Optional[Any]) -> int:
    """الحد الأقصى لرسائل الاسترجاع (افتراضي ‎1‎ عند غياب ‎store‎ أو الحقل)."""
    if store is None:
        return 1
    at = getattr(store, "recovery_attempts", None)
    if at is None:
        return 1
    try:
        v = int(at)
    except (TypeError, ValueError):
        return 1
    return max(0, v)


def _recovery_delay_minutes_from_store(store: Optional[Any]) -> int:
    """عدد الدقائق الكامل فقط (بدون الاعتماد على ثوانٍ في شرط الإرسال)."""
    td = _min_quiet_from_store_settings(store)
    return max(0, int(td // timedelta(minutes=1)))


def _naive_utc(dt: datetime) -> datetime:
    """مقارنة آمنة: ‎last_activity‎ مفترض تخزينه كـ ‎UTC‎."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def should_send_whatsapp(
    last_activity_time: Optional[datetime],
    *,
    user_returned_to_site: bool = False,
    now: Optional[datetime] = None,
    store: Optional[Any] = None,
    sent_count: int = 0,
) -> bool:
    """
    هل يسمح بإرسال تذكير واتساب؟ (بدون مزوّد؛ منطق فقط.)

    - إن رجع المستخدم للموقع (يُمثَّل مؤقتاً بـ user_returned_to_site): لا نرسل.
    - ‎max_recovery_attempts < 1‎: لا نرسل (مُعطّل).
    - إن ‎sent_count >= max_recovery_attempts‎: لا نرسل (نفد الحد).
    - إن لم نُسجّل نشاطاً: نسمح بالإرسال (لاحقاً يرتبط بتتبع فعلي) إن بقي في الحد.
    - وإلا: لا إرسال إلا إذا ‎now‎ (‎UTC‎) ‎>= last_activity‎ (‎UTC‎) + ‎recovery_delay بالدقائق‎ الكاملة فقط.
    """
    if user_returned_to_site:
        return False
    cfg = _recovery_config(store)
    if not cfg.get("whatsapp_recovery_enabled", True):
        return False
    try:
        sc = int(sent_count)
    except (TypeError, ValueError):
        sc = 0
    sc = max(0, sc)
    max_a = _max_recovery_attempts(store)
    if max_a < 1:
        return False
    if sc >= max_a:
        return False
    if last_activity_time is None:
        return True
    recovery_delay_minutes = _recovery_delay_minutes_from_store(store)
    t = now if now is not None else datetime.utcnow()
    t = _naive_utc(t)
    last_activity = _naive_utc(last_activity_time)
    delay_passed = t >= (last_activity + timedelta(minutes=recovery_delay_minutes))
    print("last_activity:", last_activity)
    print("now:", t)
    print("delay_minutes:", recovery_delay_minutes)
    print("should_send:", delay_passed)
    if not delay_passed:
        return False
    return True


def _normalize_twilio_whatsapp_from(raw: str) -> str:
    """يضمن صيغة ‎whatsapp:+E164‎ المطلوبة لـ Twilio."""
    r = (raw or "").strip()
    if not r:
        return ""
    rl = r.lower()
    if rl.startswith("whatsapp:"):
        return r.strip()
    if r.startswith("+"):
        return f"whatsapp:{r}"
    digits = "".join(c for c in r if c.isdigit())
    if not digits:
        return ""
    return f"whatsapp:+{digits}"


def _normalize_twilio_whatsapp_to(phone: str) -> str:
    """من حقل رقم أرضي إلى عنوان Twilio ‎whatsapp:+...‎"""
    raw = (phone or "").strip()
    rl = raw.lower()
    if rl.startswith("whatsapp:"):
        rest = raw.split(":", 1)[1].strip()
        if rest.startswith("+"):
            return f"whatsapp:{rest}"
        digits = "".join(c for c in rest if c.isdigit())
        return f"whatsapp:+{digits}" if digits else ""
    digits = "".join(c for c in raw.replace("+", "").replace(" ", "").replace("-", "") if c.isdigit())
    if not digits:
        return ""
    return f"whatsapp:+{digits}"


def send_whatsapp(
    phone: str,
    message: str,
    *,
    reason_tag: Optional[str] = None,
) -> Dict[str, Any]:
    """
    إرسال واتساب عبر Twilio Conversation API (REST).
    المتغيرات: TWILIO_ACCOUNT_SID، TWILIO_AUTH_TOKEN، TWILIO_WHATSAPP_FROM.
    """
    sid = (os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
    token = (os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
    from_raw = (os.getenv("TWILIO_WHATSAPP_FROM") or "").strip()

    if not sid or not token or not from_raw:
        return {
            "ok": False,
            "error": "twilio_not_configured",
            "hint": "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM.",
        }

    from_number = _normalize_twilio_whatsapp_from(from_raw)
    if not from_number:
        return {"ok": False, "error": "twilio_invalid_from"}

    to_addr = _normalize_twilio_whatsapp_to(phone)
    if not to_addr:
        return {"ok": False, "error": "invalid_phone"}

    body_text = (message or "").strip()
    if not body_text:
        return {"ok": False, "error": "empty_message"}

    try:
        client = Client(sid, token)
        msg = client.messages.create(
            from_=from_number,
            body=body_text,
            to=to_addr,
        )
        twilio_status = getattr(msg, "status", None)
        result: Dict[str, Any] = {
            "ok": True,
            "sid": msg.sid,
            "status": twilio_status,
        }
        print("[WA SENT]", phone, result)
        print("[WA STATUS]", twilio_status)
        return result
    except Exception as e:  # noqa: BLE001 — إرجاع خطأ المزود للمتصل
        logger.warning("Twilio WhatsApp send failed: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}


def send_whatsapp_mock(phone, message):
    print("sending whatsapp to:", phone)
    print("message:", message)
    return {"ok": True}


def is_production_mode() -> bool:
    """وضع إنتاج للاسترجاع: ‎PRODUCTION_MODE‎ = ‎true / 1 / yes‎ (حساس لحالة الأحرف)."""
    v = (os.getenv("PRODUCTION_MODE") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def whatsapp_real_configured() -> bool:
    """‎True‎ عند ضبط اعتمادات Twilio الكاملة."""
    sid = (os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
    token = (os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
    frm = (os.getenv("TWILIO_WHATSAPP_FROM") or "").strip()
    return bool(sid and token and frm)


def recovery_uses_real_whatsapp() -> bool:
    """
    يستخدم الإرسال الفعلي فقط عند ‎PRODUCTION_MODE‎ + ضبط Twilio.
    بدون الاثنين: بقاء الوهمي دون رفع خطأ.
    """
    if not is_production_mode():
        return False
    if not whatsapp_real_configured():
        logger.info(
            "PRODUCTION_MODE set but TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN/TWILIO_WHATSAPP_FROM missing — using mock"
        )
        return False
    return True


def send_whatsapp_real(
    phone: str,
    message: str,
    *,
    reason_tag: Optional[str] = None,
) -> Dict[str, Any]:
    """
    مطابق لـ‎ ``send_whatsapp`` (‎Twilio‎) — اسم قديم يستخدمه طابور الاسترجاع.
    """
    return send_whatsapp(phone, message, reason_tag=reason_tag)
