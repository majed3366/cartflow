# -*- coding: utf-8 -*-
"""
قوالب رسائل واتساب الاسترجاع حسب وسم السبب — طبقة نص فقط (بدون إرسال).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from services.store_trigger_templates import parse_trigger_templates_column

WHATSAPP_REASON_TEMPLATES: dict[str, str] = {
    "price": (
        "وفرنا لك خيار بنفس الفكرة بسعر أقل 👌\n"
        "تقدر تكمل الطلب مباشرة من هنا 👇"
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

# مفتاح القالب المنطقي ← عمود ‎Store‎ (لوحة التحكم لاحقاً)
_STORE_TEMPLATE_COLUMN_BY_CANON: Dict[str, str] = {
    "price": "template_price",
    "shipping": "template_shipping",
    "quality": "template_quality",
    "delivery": "template_delivery",
    "warranty": "template_warranty",
    "other": "template_other",
}


def _store_dashboard_template(store: Any, canon_key: Optional[str]) -> Optional[str]:
    """نص من المتجر إن وُجد وغير فارغ؛ وإلا ‎None‎."""
    if store is None or not canon_key:
        return None
    attr = _STORE_TEMPLATE_COLUMN_BY_CANON.get(canon_key)
    if not attr:
        return None
    raw = getattr(store, attr, None)
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


def _canonical_template_key(reason_tag: Optional[str]) -> Optional[str]:
    """يحوّل وسوم الواجهة (‎price_high‎، ‎shipping_cost‎…) إلى مفتاح القالب."""
    k = (reason_tag or "").strip().lower()
    if not k:
        return None
    # التردد في الودجيت (‎thinking‎) يستخدم نفس سلة قالب ‎other‎ والقالب المشغّل ‎other‎.
    if k == "thinking":
        return "other"
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


def resolve_whatsapp_recovery_template_message(
    reason_tag: Optional[str],
    *,
    store: Any = None,
) -> str:
    """
    قالب مشغّل مفعّل → ‎message‎ المخصص؛ وإلا ‎template_*‎ من لوحة التحكم أو الافتراضي.
    """
    canon = _canonical_template_key(reason_tag)
    rt_log = reason_tag if reason_tag is not None else ""

    trigger_template_used = False
    final: Optional[str] = None
    source = "default"

    if canon is not None and store is not None:
        triggers = parse_trigger_templates_column(
            getattr(store, "trigger_templates_json", None)
        )
        tentry = triggers.get(canon)
        if tentry and bool(tentry.get("enabled")):
            msg_t = str(tentry.get("message") or "").strip()
            if msg_t:
                final = msg_t
                source = "trigger"
                trigger_template_used = True

    if final is None:
        raw = (reason_tag or "").strip().lower()
        lookup = canon if canon is not None else raw
        msg = WHATSAPP_REASON_TEMPLATES.get(lookup)
        if msg is None and canon is not None:
            msg = WHATSAPP_REASON_TEMPLATES.get(canon)
        default_message = msg if msg else DEFAULT_WHATSAPP_TEMPLATE_MESSAGE

        store_override = _store_dashboard_template(store, canon)
        final = store_override if store_override else default_message
        source = "dashboard" if store_override else "default"

    try:
        log_tag = canon if canon is not None else rt_log
        print("[TRIGGER TEMPLATE USED]")
        print("reason_tag=", log_tag)
        print(
            "template_enabled=" + ("true" if trigger_template_used else "false")
        )
    except Exception:
        pass
    try:
        if canon == "price" and source == "default":
            print("[TEMPLATE IMPROVED] reason_tag=price")
    except Exception:
        pass
    try:
        print("[TEMPLATE SOURCE]")
        print("reason_tag=", rt_log)
        print("source=", source)
        print("message=", final)
    except Exception:
        pass
    return final
