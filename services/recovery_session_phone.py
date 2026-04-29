# -*- coding: utf-8 -*-
"""نسخة في الذاكرة لرقم الواتساب لكل جلسة (‎store_slug:session_id‎) لتكمل الطلب بعد التأخير."""
from __future__ import annotations

import threading
from typing import Optional

_lock = threading.Lock()
# نفس صيغة ‎main._recovery_key_from_payload‎ — بدون المتجر الأولى كجزء أول فقط‎ store:session‎
_customer_phone_by_recovery_key: dict[str, str] = {}


def record_recovery_customer_phone(recovery_key: str, phone: Optional[str]) -> None:
    """
    يحدّث التخزين المؤقت عند إرسال ‎POST /api/cart-recovery/reason‎ مع ‎phone‎.
    """
    rk = (recovery_key or "").strip()[:800]
    if not rk:
        return
    p = _strip_phone(phone)
    with _lock:
        if p:
            _customer_phone_by_recovery_key[rk] = p
        elif rk in _customer_phone_by_recovery_key:
            del _customer_phone_by_recovery_key[rk]


def get_recovery_customer_phone(recovery_key: str) -> Optional[str]:
    rk = (recovery_key or "").strip()[:800]
    if not rk:
        return None
    with _lock:
        v = _customer_phone_by_recovery_key.get(rk)
        return v if v else None


def recovery_phone_memory_clear() -> None:
    """للاختبارات فقط."""
    with _lock:
        _customer_phone_by_recovery_key.clear()


def _strip_phone(raw: Optional[str]) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    return s[:100] if s else ""


def recovery_key_for_reason_session(store_slug: str, session_id: str) -> str:
    """متوافق مع ‎main._recovery_key_from_payload‎ (‎store + session‎)."""
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    store_key = ss if ss else "default"
    return f"{store_key}:{sid}"
