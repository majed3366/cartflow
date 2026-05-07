# -*- coding: utf-8 -*-
"""عرض عربي لشارات نية رد الاسترجاع — منفصل عن المحرك لتسهيل الترجمة والـ AI لاحقاً."""
from __future__ import annotations

from typing import Final

from services.recovery_reply_intent_detector import detect_recovery_reply_intent

_INTENT_BADGE_AR: Final[dict[str, str]] = {
    "price": "اعتراض سعر",
    "shipping": "يسأل عن الشحن",
    "delivery": "يسأل عن التوصيل",
    "warranty": "يسأل عن الضمان",
    "ready_to_buy": "مهتم بالشراء",
    "quality": "يسأل عن الجودة",
    "hesitation": "تردد أو تأجيل",
    "other": "استفسار عام",
}


def recovery_reply_intent_badge_ar(intent_key: str) -> str:
    k = (intent_key or "").strip().lower()
    return _INTENT_BADGE_AR.get(k, _INTENT_BADGE_AR["other"])


def recovery_reply_intent_badge_for_message(message_text: str) -> tuple[str, str]:
    """‎(intent_key, label_ar)‎ من نص الرسالة — للاختبارات والمعاينة."""
    ik = detect_recovery_reply_intent(message_text)
    return ik, recovery_reply_intent_badge_ar(ik)
