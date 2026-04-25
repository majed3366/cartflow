# -*- coding: utf-8 -*-
"""
واتساب: إرسال (ستُربط بمزود لاحقاً) — حالياً تسجيل فقط.
توقيت «متى نرسل؟» — مؤقتاً قيم مُدخَلة يدوياً/مُتخيّلة إلى أن يُربط التتبع.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# حد أدنى من آخر تفاعل (قابلة لربط ‎.env لاحقاً)
_WHATSAPP_MIN_QUIET = timedelta(minutes=2)


def should_send_whatsapp(
    last_activity_time: Optional[datetime],
    *,
    user_returned_to_site: bool = False,
    now: Optional[datetime] = None,
) -> bool:
    """
    هل يسمح بإرسال تذكير واتساب؟ (بدون مزوّد؛ منطق فقط.)

    - إن رجع المستخدم للموقع (يُمثَّل مؤقتاً بـ user_returned_to_site): لا نرسل.
    - إن لم نُسجّل نشاطاً: نسمح بالإرسال (لاحقاً يرتبط بتتبع فعلي).
    - وإلا يلزم أن يمر ≥ دقيقتين من آخر نشاط.
    """
    if user_returned_to_site:
        return False
    if last_activity_time is None:
        return True
    t = now if now is not None else datetime.now(timezone.utc)
    if last_activity_time.tzinfo is None:
        last = last_activity_time.replace(tzinfo=timezone.utc)
    else:
        last = last_activity_time
    if t - last < _WHATSAPP_MIN_QUIET:
        return False
    return True


def send_whatsapp(phone: str, message: str) -> Dict[str, Any]:
    """
    يرسل رسالة واتساب. حالياً لا يرسل فعلياً — يطابق الرسالة في الـ logging فقط.
    """
    logger.info("send_whatsapp (no provider): phone=%r, message=%s", phone, message)
    return {"ok": True}
