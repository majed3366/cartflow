# -*- coding: utf-8 -*-
"""
طبقة تصنيف نية رد العميل على واتساب الاسترجاع — مطابقة كلمات فقط (بدون نماذج).
جاهز لاحقاً لاستبدال/دمج مع تصنيف ذكاء أو درجات ثقة.
"""
from __future__ import annotations

from typing import Final

IntentKey = str

_INTENT_READY_TO_BUY: Final = "ready_to_buy"
_INTENT_DELIVERY: Final = "delivery"
_INTENT_SHIPPING: Final = "shipping"
_INTENT_PRICE: Final = "price"
_INTENT_WARRANTY: Final = "warranty"
_INTENT_QUALITY: Final = "quality"
_INTENT_HESITATION: Final = "hesitation"
_INTENT_OTHER: Final = "other"

_READY_TO_BUY: Final[frozenset[str]] = frozenset(
    {
        "نعم",
        "yes",
        "ابغى اطلب",
        "أبغى أطلب",
        "ابغي اطلب",
        "ابغى اكمل",
        "ابغي اكمل",
        "أبي أكمل",
        "ابي أكمل",
        "وين الرابط",
        "أين الرابط",
        "وين الرابط؟",
        "ارسل الرابط",
        "أرسل الرابط",
        "ارسال الرابط",
    }
)
_READY_TO_BUY_FRAGMENTS: Final[frozenset[str]] = frozenset(
    {
        "ابغى اطلب",
        "ابغي اطلب",
        "ابغى اكمل",
        "ابغي اكمل",
        "ابي اكمل",
        "أبي أكمل",
        "ارسل الرابط",
        "أرسل الرابط",
    }
)

_DELIVERY: Final[frozenset[str]] = frozenset(
    {
        "متى يوصل",
        "التوصيل",
        "delivery",
        "موعد التوصيل",
        "وقت التوصيل",
        "يوصل",
        "متى التوصيل",
        "وصل الطلب",
    }
)

_SHIPPING: Final[frozenset[str]] = frozenset(
    {
        "شحن",
        "shipping",
        "رسوم الشحن",
        "تكلفة الشحن",
        "سعر الشحن",
    }
)

_PRICE: Final[frozenset[str]] = frozenset(
    {
        "غالي",
        "السعر",
        "خصم",
        "expensive",
        "price",
        "سعر",
        "تخفيض",
        "توفر خصم",
    }
)

_WARRANTY: Final[frozenset[str]] = frozenset(
    {
        "ضمان",
        "warranty",
    }
)

_QUALITY: Final[frozenset[str]] = frozenset(
    {
        "الجودة",
        "جودة",
        "أصلي",
        "اصلي",
        "authentic",
        "original",
    }
)

_HESITATION: Final[frozenset[str]] = frozenset(
    {
        "بفكر",
        "بفكر؟",
        "بعدين",
        "later",
        "خلني افكر",
    }
)


def _normalize_for_intent(text: str) -> str:
    t = (text or "").strip().lower()
    for a, b in (
        ("أ", "ا"),
        ("إ", "ا"),
        ("آ", "ا"),
        ("ٱ", "ا"),
        ("ى", "ي"),
        ("ة", "ه"),
        ("ؤ", "و"),
        ("ئ", "ي"),
    ):
        t = t.replace(a, b)
    return " ".join(t.split())


def detect_recovery_reply_intent(message_text: str) -> str:
    """
    يصنّف نص رد العميل إلى واحدة من مفاتيح الاسترجاع التفاعلي.
    """
    raw = (message_text or "").strip()
    if not raw:
        return _INTENT_OTHER

    n = _normalize_for_intent(raw)
    if not n:
        return _INTENT_OTHER

    tokens = frozenset(n.split())

    if tokens & _READY_TO_BUY:
        return _INTENT_READY_TO_BUY
    for frag in _READY_TO_BUY_FRAGMENTS:
        if frag in n:
            return _INTENT_READY_TO_BUY

    if any(k in n for k in _DELIVERY):
        return _INTENT_DELIVERY

    if any(k in n for k in _SHIPPING):
        return _INTENT_SHIPPING

    if any(k in n for k in _PRICE):
        return _INTENT_PRICE

    if any(k in n for k in _WARRANTY):
        return _INTENT_WARRANTY

    if any(k in n for k in _QUALITY):
        return _INTENT_QUALITY

    if any(k in n for k in _HESITATION):
        return _INTENT_HESITATION

    return _INTENT_OTHER
