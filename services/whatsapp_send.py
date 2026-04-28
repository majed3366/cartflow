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
    إرسال واتساب: عند ضبط ‎WHATSAPP_API_URL + WHATSAPP_API_KEY‎ يُمرَّر إلى ‎send_whatsapp_real‎
    ويعود بنتيجة المزود؛ وإلا تسجيل فقط بدون ادّعاء إرسال فعلي (‎ok: False‎، ‎not_configured‎).
    """
    if whatsapp_real_configured():
        return send_whatsapp_real(phone, message)
    logger.info(
        "send_whatsapp (no HTTP provider): phone=%r, message=%s", phone, message
    )
    return {
        "ok": False,
        "error": "not_configured",
        "hint": "Set WHATSAPP_API_URL and WHATSAPP_API_KEY for confirmed delivery.",
    }


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
            out: Dict[str, Any] = {
                "ok": True,
                "status_code": r.status_code,
            }
            try:
                data = r.json()
            except ValueError:
                txt = (r.text or "").strip()
                if txt:
                    out["provider_body_preview"] = txt[:2000]
                return out
            out["provider_response"] = data
            return out
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
