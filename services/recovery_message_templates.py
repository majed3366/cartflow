# -*- coding: utf-8 -*-
"""
قوالب رسائل واتساب الاسترجاع حسب وسم السبب — طبقة نص فقط (بدون إرسال).
"""
from __future__ import annotations

from typing import Optional

WHATSAPP_REASON_TEMPLATES: dict[str, str] = {
    "price": (
        "أفهمك 👍 السعر مهم... عندنا خيار مناسب بسعر أقل 👌 تحب أرسله لك؟"
    ),
    "shipping": (
        "أتفهمك 👍 تكلفة الشحن تفرق... أحيانًا فيه عروض أو خيارات أفضل 👍 تحب أشوف لك؟"
    ),
    "quality": (
        "سؤال مهم 👌 الجودة تهم... هذا المنتج عليه ضمان وجودة عالية 👍 تحب تفاصيل أكثر؟"
    ),
    "delivery": (
        "واضح 👍 وقت التوصيل مهم... نقدر نشوف لك أسرع خيار متاح 🚚 تحب؟"
    ),
    "warranty": (
        "أفهمك 👌 الضمان مهم... هذا المنتج عليه ضمان رسمي 👍 تحب أوضح لك؟"
    ),
    "other": (
        "تمام 👍 خلني أساعدك بشكل أفضل... وش أكثر شيء مسبب لك تردد؟"
    ),
}

DEFAULT_WHATSAPP_TEMPLATE_MESSAGE = (
    "لاحظنا إنك مهتم 👌 حاب نساعدك تكمل الطلب؟"
)


def _canonical_template_key(reason_tag: Optional[str]) -> Optional[str]:
    """يحوّل وسوم الواجهة (‎price_high‎، ‎shipping_cost‎…) إلى مفتاح القالب."""
    k = (reason_tag or "").strip().lower()
    if not k:
        return None
    if k in WHATSAPP_REASON_TEMPLATES:
        return k
    if k == "other" or k.startswith("other"):
        return "other"
    if k.startswith("price") or "price" in k:
        return "price"
    if "shipping" in k:
        return "shipping"
    if "quality" in k:
        return "quality"
    if "delivery" in k:
        return "delivery"
    if "warranty" in k:
        return "warranty"
    return None


def resolve_whatsapp_recovery_template_message(reason_tag: Optional[str]) -> str:
    """
    ‎message = templates.get(canonical_key, default_message)‎ مع تسجيل الاختيار.
    """
    canon = _canonical_template_key(reason_tag)
    raw = (reason_tag or "").strip().lower()
    lookup = canon if canon is not None else raw
    msg = WHATSAPP_REASON_TEMPLATES.get(lookup)
    if msg is None and canon is not None:
        msg = WHATSAPP_REASON_TEMPLATES.get(canon)
    final = msg if msg else DEFAULT_WHATSAPP_TEMPLATE_MESSAGE
    rt_log = reason_tag if reason_tag is not None else ""
    try:
        print("[TEMPLATE SELECTED]")
        print("reason_tag=", rt_log)
        print("message=", final)
    except Exception:
        pass
    return final
