# -*- coding: utf-8 -*-
"""نسخة في الذاكرة لرقم الواتساب لكل جلسة (‎store_slug:session_id‎) لتكمل الطلب بعد التأخير."""
from __future__ import annotations

import threading
from typing import Optional

_lock = threading.Lock()
# نفس صيغة ‎main._recovery_key_from_payload‎ — بدون المتجر الأولى كجزء أول فقط‎ store:session‎
_customer_phone_by_recovery_key: dict[str, str] = {}
# مصدر مؤقت للتسمية في ‎[PHONE RESOLUTION]‎ (مثل ‎cf_test_phone‎ في تجارب ‎demo‎ فقط).
_phone_resolution_source_by_recovery_key: dict[str, str] = {}


def record_recovery_customer_phone(
    recovery_key: str, phone: Optional[str], *, source: Optional[str] = None
) -> None:
    """
    يحدّث التخزين المؤقت عند إرسال ‎POST /api/cart-recovery/reason‎ مع ‎phone‎.
    ‎source‎ اختياري: عند ‎None‎ تُمسح تسمية المصدر المرتبطة بهذا المفتاح.
    """
    rk = (recovery_key or "").strip()[:800]
    if not rk:
        return
    p = _strip_phone(phone)
    with _lock:
        if p:
            _customer_phone_by_recovery_key[rk] = p
            if source is not None:
                s = str(source).strip()[:80]
                if s:
                    _phone_resolution_source_by_recovery_key[rk] = s
                else:
                    _phone_resolution_source_by_recovery_key.pop(rk, None)
            else:
                _phone_resolution_source_by_recovery_key.pop(rk, None)
        else:
            if rk in _customer_phone_by_recovery_key:
                del _customer_phone_by_recovery_key[rk]
            _phone_resolution_source_by_recovery_key.pop(rk, None)


def get_recovery_customer_phone(recovery_key: str) -> Optional[str]:
    rk = (recovery_key or "").strip()[:800]
    if not rk:
        return None
    with _lock:
        v = _customer_phone_by_recovery_key.get(rk)
        return v if v else None


def get_recovery_phone_resolution_source(recovery_key: str) -> str:
    """يعود ‎customer_profile‎ إن لم يُسجَّل مصدر ‎QA‎."""
    rk = (recovery_key or "").strip()[:800]
    if not rk:
        return "customer_profile"
    with _lock:
        s = _phone_resolution_source_by_recovery_key.get(rk)
        if not s:
            return "customer_profile"
        if s == "cf_test_phone":
            return "demo_test_phone"
        return s


def recovery_phone_memory_clear() -> None:
    """للاختبارات فقط."""
    with _lock:
        _customer_phone_by_recovery_key.clear()
        _phone_resolution_source_by_recovery_key.clear()


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
