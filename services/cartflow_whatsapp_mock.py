# -*- coding: utf-8 -*-
"""
قواعد ‎Mock‎ لنصوص متابعة واتساب من سبب التردد (بدون ‎AI‎ ولا إرسال فعلي).
نص ‎{generated_message}‎ بدون ‎رابط سلة‎ — يُلحق الواجهة ‎رابط السلة‎ مرة واحدة.
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


def get_merchant_whatsapp_e164_for_store(store_slug: str) -> Optional[str]:
    """
    رقم ‎E.164‎ بدون + لبناء ‎https://wa.me/{num}?text=‎.
    لاحقاً: اقرأ من إعدادات المتجر/لوحة التحكم. حالياً: ‎None‎ → ‎wa.me/?text=‎.
    """
    _ = (store_slug or "").strip()[:255]
    return None


def build_mock_whatsapp_message(
    *,
    reason: str,
    sub_category: Optional[str],
    product_name: Optional[str] = None,
    product_price: Optional[str] = None,
    cart_url: Optional[str] = None,
) -> str:
    """
    نص جسم الرسالة فقط (بلا ‎رابط سلة‎ — يضيفه الودجت في آخر النص الظاهر لواتساب).
    ‎cart_url‎ مُتجاهل هنا عمداً للتوافق مع ‎API‎.
    """
    _ = product_price
    _ = cart_url  # يُلحق الودجت رابط السلة مرة في آخر نص واتساب
    r = (reason or "").strip().lower()
    sub = (sub_category or "").strip() or None
    pn = _name(product_name)

    if r == "price":
        if sub not in PRICE_SUB_CATEGORIES:
            raise ValueError("sub_category_required_or_invalid")
        if sub == "price_discount_request":
            return "جهزنا لك عرض مناسب يساعدك تكمل الطلب."
        if sub == "price_budget_issue":
            return "نقدر نقترح لك خيار قريب يناسب ميزانيتك."
        if sub == "price_cheaper_alternative":
            return "نقدر نعرض لك بدائل مشابهة بسعر أقل."
        raise ValueError("sub_category_required_or_invalid")

    if sub is not None and str(sub).strip():
        raise ValueError("sub_category_not_applicable")

    if r == "quality":
        return (
            "نقدر نرسل لك تفاصيل الخامة، الاستخدام، أو أي مميزات تساعدك تقرر بثقة."
        )
    if r == "warranty":
        return (
            "نقدر نوضح لك مدة الضمان، ماذا يشمل، وطريقة الاستفادة منه قبل إكمال الطلب."
        )
    if r == "shipping":
        return (
            "نقدر نوضح لك مدة التوصيل المتوقعة، تكلفة الشحن، وخيارات التوصيل المتاحة."
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
