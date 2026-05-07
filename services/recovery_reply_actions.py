# -*- coding: utf-8 -*-
"""
تلميحات إجراء للتاجر أثناء الاسترجاع التفاعلي — جاهزة لاحقاً لسير موافقة/إرسال/ذكاء.
لا ترسل رسائل؛ توجيه لوحة فقط.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class RecoveryMerchantAction:
    """مفتاح ثابت للسير المستقبلي + نص عربي قصير للوحة."""

    key: str
    hint_ar: str


_ACTION_REASSURE_PRICE: Final = RecoveryMerchantAction(
    "reassure_price",
    "طمأنة العميل حول السعر",
)
_ACTION_CLARIFY_DELIVERY: Final = RecoveryMerchantAction(
    "clarify_shipping",
    "توضيح الشحن والتوصيل",
)
_ACTION_EXPLAIN_WARRANTY: Final = RecoveryMerchantAction(
    "explain_warranty",
    "توضيح الضمان",
)
_ACTION_SEND_CHECKOUT: Final = RecoveryMerchantAction(
    "send_checkout_link",
    "إرسال رابط الطلب",
)
_ACTION_GENTLE_SPACE: Final = RecoveryMerchantAction(
    "gentle_follow_up",
    "إعطاء مساحة مع إبقاء فرصة البيع",
)
_ACTION_TRUST_QUALITY: Final = RecoveryMerchantAction(
    "build_trust_quality",
    "تعزيز الثقة بالجودة",
)
_ACTION_HELPFUL: Final = RecoveryMerchantAction(
    "open_helpful_reply",
    "متابعة مفيدة ومساعدة على الإغلاق",
)


def recovery_merchant_action_for_intent(intent_key: str) -> RecoveryMerchantAction:
    """يُرجع تلميح الإجراء حسب مفتاح النية (بعد تعيين ‎shipping‎ → ‎delivery‎ إن لزم)."""
    k = (intent_key or "").strip().lower()
    if k == "price":
        return _ACTION_REASSURE_PRICE
    if k in ("delivery", "shipping"):
        return _ACTION_CLARIFY_DELIVERY
    if k == "warranty":
        return _ACTION_EXPLAIN_WARRANTY
    if k == "ready_to_buy":
        return _ACTION_SEND_CHECKOUT
    if k == "hesitation":
        return _ACTION_GENTLE_SPACE
    if k == "quality":
        return _ACTION_TRUST_QUALITY
    return _ACTION_HELPFUL
