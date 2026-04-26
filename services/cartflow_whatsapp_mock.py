# -*- coding: utf-8 -*-
"""
قواعد ‎Mock‎ لنصوص متابعة واتساب من سبب التردد (بدون ‎AI‎ ولا إرسال فعلي).
"""
from __future__ import annotations

from typing import Optional

# يطابق ‎REASON_CHOICES / PRICE_SUB_CATEGORIES‎ في ‎routes/cartflow.py‎
REASON_CHOICES = frozenset(
    {"price", "quality", "warranty", "shipping", "thinking", "other", "human_support"}
)
PRICE_SUB_CATEGORIES = frozenset(
    {
        "price_discount_request",
        "price_budget_issue",
        "price_cheaper_alternative",
    }
)


def _name(product_name: Optional[str]) -> str:
    t = (product_name or "").strip()
    return t if t else "المنتج المختار"


def _url(cart_url: Optional[str]) -> str:
    t = (cart_url or "").strip()
    return t if t else "#"


def build_mock_whatsapp_message(
    *,
    reason: str,
    sub_category: Optional[str],
    product_name: Optional[str] = None,
    product_price: Optional[str] = None,
    cart_url: Optional[str] = None,
) -> str:
    """
    يُرجع نصاً متعدد الأسطر حسب ‎reason‎ / ‎sub_category‎. ‎product_price‎ محجوز لاحقاً.
    """
    _ = product_price
    r = (reason or "").strip().lower()
    sub = (sub_category or "").strip() or None
    pn = _name(product_name)
    cu = _url(cart_url)

    if r == "price":
        if sub not in PRICE_SUB_CATEGORIES:
            raise ValueError("sub_category_required_or_invalid")
        if sub == "price_discount_request":
            return (
                "عندك كود خصم خاص 🎁\n"
                f"استخدمه الآن وكمل طلبك على {pn}.\n"
                f"رابط السلة: {cu}"
            )
        if sub == "price_budget_issue":
            return (
                "لو السعر أعلى من ميزانيتك، نقدر نقترح لك خيار قريب بسعر أقل 👇\n"
                f"منتجك الحالي: {pn}\n"
                f"رابط السلة: {cu}"
            )
        if sub == "price_cheaper_alternative":
            return (
                "هذا خيار مشابه بسعر أفضل 👇\n"
                "بدل ما تطلع من المتجر، شوف البديل المناسب لك.\n"
                f"رابط السلة: {cu}"
            )
        raise ValueError("sub_category_required_or_invalid")

    if sub is not None and str(sub).strip():
        raise ValueError("sub_category_not_applicable")

    if r == "quality":
        return (
            "نفهم أن الجودة مهمة 👍\n"
            f"منتج {pn} موضح بتفاصيل تساعدك تتأكد قبل الشراء.\n"
            "إذا تحتاج توضيح أكثر، صاحب المتجر يقدر يساعدك."
        )
    if r == "warranty":
        return (
            "بخصوص الضمان 👍\n"
            "نرسل لك ملخص الضمان والتفاصيل المهمة قبل إكمال الطلب.\n"
            f"منتجك: {pn}\n"
            f"رابط السلة: {cu}"
        )
    if r == "shipping":
        return (
            "بخصوص الشحن 🚚\n"
            "نرسل لك تفاصيل التوصيل المتاحة قبل إتمام الطلب.\n"
            f"منتجك: {pn}\n"
            f"رابط السلة: {cu}"
        )
    if r == "thinking":
        return (
            "خذ راحتك 👍\n"
            f"إذا كنت محتار بشأن {pn}، نقدر نساعدك تقارن أو نوضح لك أهم المزايا."
        )
    if r == "other":
        return (
            "وصلتنا ملاحظتك 👍\n"
            "بنحاول نساعدك بأفضل خيار مناسب قبل إكمال الطلب."
        )
    if r == "human_support":
        return (
            "تم تحويل طلبك لصاحب المتجر 👤\n"
            "راح يساعدك مباشرة بخصوص المنتج أو الطلب."
        )
    if r not in REASON_CHOICES:
        raise ValueError("invalid_reason")
    raise ValueError("invalid_reason")
