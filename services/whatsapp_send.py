# -*- coding: utf-8 -*-
"""
واتساب: إرسال (ستُربط بمزود لاحقاً) — حالياً تسجيل فقط.
توقيت «متى نرسل؟» — يدعم حقول ‎Store.recovery_*‎ عند تمرير ‎store‎.
إرسال فعلي اختياري عبر ‎WHATSAPP_API_URL + WHATSAPP_API_KEY‎ عند ‎PRODUCTION_MODE‎.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


def _min_quiet_from_store_settings(store: Optional[Any]) -> timedelta:
    """
    يحوّل ‎recovery_delay + recovery_delay_unit‎ إلى ‎timedelta‎.
    الافتراضي ‎2‎ دقيقة عند غياب الضبط أو ‎store‎.
    - minutes: recovery_delay
    - hours: recovery_delay * 60
    - days: recovery_delay * 1440
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
    - وإلا يلزم أن يمر زمن سكون ‎>=‎ الحد المضبوط (من ‎Store‎ أو افتراضياً ‎2‎ دقيقة).
    """
    if user_returned_to_site:
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
    t = now if now is not None else datetime.now(timezone.utc)
    if last_activity_time.tzinfo is None:
        last = last_activity_time.replace(tzinfo=timezone.utc)
    else:
        last = last_activity_time
    min_quiet = _min_quiet_from_store_settings(store)
    if t - last < min_quiet:
        return False
    return True


def send_whatsapp(phone: str, message: str) -> Dict[str, Any]:
    """
    يرسل رسالة واتساب. حالياً لا يرسل فعلياً — يطابق الرسالة في الـ logging فقط.
    """
    logger.info("send_whatsapp (no provider): phone=%r, message=%s", phone, message)
    return {"ok": True}


def send_whatsapp_mock(phone, message):
    print("sending whatsapp to:", phone)
    print("message:", message)
    return {"ok": True}


def is_production_mode() -> bool:
    """وضع إنتاج للاسترجاع: ‎PRODUCTION_MODE‎ = ‎true / 1 / yes‎ (حساس لحالة الأحرف)."""
    v = (os.getenv("PRODUCTION_MODE") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def whatsapp_real_configured() -> bool:
    """يُرجع ‎True‎ إن وُجد ‎URL‎ ومفتاح غير فارغين."""
    u = (os.getenv("WHATSAPP_API_URL") or "").strip()
    k = (os.getenv("WHATSAPP_API_KEY") or "").strip()
    return bool(u and k)


def recovery_uses_real_whatsapp() -> bool:
    """
    يستخدم الإرسال الفعلي فقط عند ‎PRODUCTION_MODE‎ + ضبط المزوّد.
    بدون الاثنين: بقاء الوهمي دون رفع خطأ.
    """
    if not is_production_mode():
        return False
    if not whatsapp_real_configured():
        logger.info(
            "PRODUCTION_MODE set but WHATSAPP_API_URL/WHATSAPP_API_KEY missing — using mock"
        )
        return False
    return True


def send_whatsapp_real(phone: str, message: str) -> Dict[str, Any]:
    """
    يرسل عبر ‎POST‎ إلى ‎WHATSAPP_API_URL‎ بجسم ‎JSON‎ عام:
    ‎{ \"phone\": ..., \"message\": ... }‎ مع ‎Authorization: Bearer <KEY>‎.

    يُناسب واجهة مخصّصة أو ‎webhook proxy‎؛ اضبط المزوّد أو عدّل الحمولة لاحقاً.
    """
    url = (os.getenv("WHATSAPP_API_URL") or "").strip()
    key = (os.getenv("WHATSAPP_API_KEY") or "").strip()
    if not url or not key:
        return {"ok": False, "error": "not_configured"}
    p = (phone or "").strip()
    body_text = (message or "").strip()
    try:
        r = requests.post(
            url,
            json={"phone": p, "message": body_text},
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        if 200 <= r.status_code < 300:
            return {
                "ok": True,
                "status_code": r.status_code,
            }
        logger.warning(
            "WhatsApp API non-success: %s %s", r.status_code, r.text[:1000]
        )
        return {
            "ok": False,
            "error": "http_error",
            "status_code": r.status_code,
            "body": r.text[:2000],
        }
    except requests.RequestException as e:  # noqa: BLE001
        logger.warning("WhatsApp API request failed: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}
    except (OSError, TypeError, ValueError) as e:  # noqa: BLE001
        logger.warning("WhatsApp send unexpected error: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}
