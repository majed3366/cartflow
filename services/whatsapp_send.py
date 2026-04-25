# -*- coding: utf-8 -*-
"""
واتساب: إرسال (ستُربط بمزود لاحقاً) — حالياً تسجيل فقط.
توقيت «متى نرسل؟» — يدعم حقول ‎Store.recovery_*‎ عند تمرير ‎store‎.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

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


def should_send_whatsapp(
    last_activity_time: Optional[datetime],
    *,
    user_returned_to_site: bool = False,
    now: Optional[datetime] = None,
    store: Optional[Any] = None,
) -> bool:
    """
    هل يسمح بإرسال تذكير واتساب؟ (بدون مزوّد؛ منطق فقط.)

    - إن رجع المستخدم للموقع (يُمثَّل مؤقتاً بـ user_returned_to_site): لا نرسل.
    - ‎store.recovery_attempts < 1‎: لا نرسل (مُعطّل).
    - إن لم نُسجّل نشاطاً: نسمح بالإرسال (لاحقاً يرتبط بتتبع فعلي).
    - وإلا يلزم أن يمر زمن سكون ‎>=‎ الحد المضبوط (من ‎Store‎ أو افتراضياً ‎2‎ دقيقة).
    """
    if user_returned_to_site:
        return False
    if store is not None:
        at = getattr(store, "recovery_attempts", None)
        if at is not None:
            try:
                if int(at) < 1:
                    return False
            except (TypeError, ValueError):
                pass
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
