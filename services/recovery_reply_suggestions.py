# -*- coding: utf-8 -*-
"""
اقتراحات رد قصيرة للبيع — للتاجر فقط (لا إرسال تلقائي).
جاهز لاحقاً لتوليد بالذكاء أو تخصيص حسب الرسالة.
"""
from __future__ import annotations

from typing import TypedDict

from services.recovery_reply_actions import recovery_merchant_action_for_intent

_FALLBACK_REPLY = "أكيد 👍 كيف نقدر نساعدك أكثر؟"

_REPLIES: dict[str, str] = {
    "price": (
        "نفهمك 👍 أحيانًا السعر يكون سبب للتردد، "
        "تحب نشوف لك خيار أنسب أو عرض أفضل؟"
    ),
    "delivery": (
        "التوصيل غالبًا خلال أيام قليلة 👍 إذا تحب أرسل لك التفاصيل كاملة."
    ),
    "warranty": "أكيد 👍 المنتج يشمل ضمان، وإذا تحب أوضح لك التفاصيل.",
    "ready_to_buy": "ممتاز 👍 أرسل لك رابط إكمال الطلب مباشرة.",
    "hesitation": "خذ راحتك 👍 وإذا احتجت أي استفسار أنا موجود.",
    "quality": "نعتمد جودة واضحة 👍 وإذا تحب أرسل لك تفاصيل تزيد راحتك.",
}


class RecoveryReplySuggestion(TypedDict):
    suggested_reply: str
    suggested_action: str


def _normalize_intent_for_suggestion(intent: str) -> str:
    k = (intent or "").strip().lower()
    if k == "shipping":
        return "delivery"
    return k if k else "other"


def effective_suggestion_intent(intent: str) -> str:
    """المفتاح الفعلي لاختيار الرد والإجراء بعد الالتزام بـ ‎other‎ كاحتياط."""
    norm = _normalize_intent_for_suggestion(intent)
    if norm in _REPLIES:
        return norm
    return "other"


def get_recovery_reply_suggestion(
    intent: str,
    customer_message: str = "",
) -> RecoveryReplySuggestion:
    """
    يُرجع نصاً مقترحاً للتاجر وتلميح إجراء عربي قصير.
    ‎customer_message‎ محجوزة لتخصيص لاحق دون تغيير التوقيع العام.
    """
    _ = (customer_message or "").strip()
    eff = effective_suggestion_intent(intent)
    reply = _REPLIES.get(eff, _FALLBACK_REPLY)
    action = recovery_merchant_action_for_intent(eff)
    return {"suggested_reply": reply, "suggested_action": action.hint_ar}
