# -*- coding: utf-8 -*-
"""عرض قراءة فقط — لماذا اختار النظام رسالة معيّنة (لا يغيّر مسار الاسترجاع)."""
from __future__ import annotations

from typing import Optional

_PREVIEW_MAX = 80
_REPLY_MAX = 60

_REASON_GOAL_AR: dict[str, str] = {
    "price": "معالجة قلق السعر",
    "price_high": "معالجة قلق السعر",
    "shipping": "طمأنة حول الشحن",
    "delivery": "طمأنة حول الشحن",
    "thinking": "دعم اتخاذ القرار",
    "warranty": "طمأنة حول الجودة",
    "quality": "طمأنة حول الجودة",
    "human_support": "طمأنة حول الجودة",
    "trust": "طمأنة حول الجودة",
}

_MESSAGE_FALLBACK_AR = "اختار النظام رسالة مناسبة بناءً على سبب التردد."
_SENT_NO_PREVIEW_AR = "تم إرسال رسالة مناسبة لسبب التردد"


def _norm_tag(reason_tag: Optional[str]) -> str:
    return (reason_tag or "").strip().lower()


def merchant_reason_goal_ar(reason_tag: Optional[str]) -> str:
    """هدف الرسالة من سبب التردد المعروف — بدون اختراع منطق قرار."""
    k = _norm_tag(reason_tag)
    if not k:
        return ""
    if k in _REASON_GOAL_AR:
        return _REASON_GOAL_AR[k]
    return "متابعة سبب التردد"


def _truncate(text: str, max_len: int) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    if len(raw) <= max_len:
        return raw
    return raw[: max_len - 1].rstrip() + "…"


def _preview_from_whatsapp_line(whatsapp_line: Optional[str]) -> str:
    line = (whatsapp_line or "").strip()
    if not line:
        return ""
    if "—" in line:
        tail = line.split("—", 1)[-1].strip()
        if tail.startswith("(") and tail.endswith(")"):
            inner = tail[1:-1].strip()
            if inner and "ننتظر" not in inner[:24]:
                return inner
        elif tail and "ننتظر" not in tail[:24]:
            return tail
    return ""


def merchant_message_preview_display(
    *,
    message_preview: Optional[str] = None,
    whatsapp_line_ar: Optional[str] = None,
    max_len: int = _PREVIEW_MAX,
) -> Optional[str]:
    raw = (message_preview or "").strip()
    if not raw:
        raw = _preview_from_whatsapp_line(whatsapp_line_ar)
    if not raw:
        return None
    return _truncate(raw, max_len)


def merchant_sent_message_line_ar(
    *,
    message_preview: Optional[str] = None,
    whatsapp_line_ar: Optional[str] = None,
) -> str:
    prev = merchant_message_preview_display(
        message_preview=message_preview,
        whatsapp_line_ar=whatsapp_line_ar,
    )
    if prev:
        return f'"{prev}"'
    return _SENT_NO_PREVIEW_AR


def merchant_reason_goal_line_ar(reason_tag: Optional[str]) -> str:
    goal = merchant_reason_goal_ar(reason_tag)
    if goal:
        return goal
    if _norm_tag(reason_tag):
        return _MESSAGE_FALLBACK_AR
    return ""


def merchant_recovery_attempts_display_ar(
    send_count: int,
    *,
    customer_replied: bool = False,
) -> str:
    """
    نص محاولات الاسترداد للتاجر — يتوافق مع حقيقة المسار دون تغيير العدّ.

    إذا وُجد رد عميل لكن العدّ صفر (سجل غير مطابق)، نعرض أن الرسالة الأولى أُرسلت.
    """
    n = max(0, int(send_count or 0))
    if n >= 3:
        return f"عدد الرسائل: {n}"
    if n == 2:
        return "تمت متابعة إضافية"
    if n == 1:
        return "أُرسلت رسالة — لا توجد متابعات إضافية بعد"
    if customer_replied:
        return "تم إرسال أول رسالة استرداد"
    return "لم تبدأ عملية الاسترداد بعد"


def merchant_reply_preview_display(
    *,
    inbound_message: Optional[str] = None,
    last_message_line_ar: Optional[str] = None,
    max_len: int = _REPLY_MAX,
) -> Optional[str]:
    raw = (inbound_message or "").strip()
    if not raw:
        line = (last_message_line_ar or "").strip()
        if line and "لا يوجد رد" not in line and "يتابع النظام" not in line:
            raw = line
    if not raw:
        return None
    short = _truncate(raw, max_len)
    return f'"{short}"' if short else None
