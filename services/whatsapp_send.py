# -*- coding: utf-8 -*-
"""
واتساب: إرسال (ستُربط بمزود لاحقاً) — حالياً تسجيل فقط.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def send_whatsapp(phone: str, message: str) -> Dict[str, Any]:
    """
    يرسل رسالة واتساب. حالياً لا يرسل فعلياً — يطابق الرسالة في الـ logging فقط.
    """
    logger.info("send_whatsapp (no provider): phone=%r, message=%s", phone, message)
    return {"ok": True}
