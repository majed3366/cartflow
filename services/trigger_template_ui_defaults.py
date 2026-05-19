# -*- coding: utf-8 -*-
"""
نصوص المراحل الافتراضية لواجهة «قوالب حسب سبب التردد» فقط.

لا تُستخدم في مسار إرسال واتساب / محرّك القرار — عرض وإصلاح عرض لوحة التاجر.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# (مرحلة 1 طمأنة، مرحلة 2 عرض/تفاصيل، مرحلة 3 بديل/متابعة)
DASHBOARD_STAGE_TEXTS: Dict[str, Tuple[str, str, str]] = {
    "price": (
        "نعرف إن السعر قرار مهم 👍 إذا عندك استفسار عن السعر أو الدفع نوضحه بسرعة.",
        "عندنا عرض ممكن يساعدك تكمل الطلب، تحب نرسل لك التفاصيل؟",
        "عندنا خيارات بديلة أو باكج قد يفيدك أكثر 👍 نقدر نلخصها لك بسرعة إذا حاب.",
    ),
    "quality": (
        "الجودة عندنا خط واضح 👍 أي نقطة تحتاج طمأنة نجاوبك بكل صراحة.",
        "نقدر نشرح لك أهم المواصفات بجمل بسيطة تسهّل القرار بدون تعقيد.",
        "كثير من عملائنا اختاروا نفس المنتج برضا 👍 إذا حاب نعطيك فكرة سريعة عن التجارب.",
    ),
    "shipping": (
        "بخصوص الشحن: نقدر نوضّح لك المدة والتكلفة والخيارات المتاحة لمنطقتك.",
        "إذا يتوفر شحن مجاني أو عرض شحن يناسبك، نشرح لك الشروط باختصار بدون التزام منك الآن.",
        "نقدر نتابع معك بشكل خاص لحد ما ترتاح من تفاصيل الشحن والتسليم.",
    ),
    "delivery": (
        "بخصوص موعد التوصيل: نعطيك توقيتاً تقريبياً واضحاً يناسب عنوانك.",
        "إذا في خيار أسرع أو تسريع متاح لموقعك، نبلغك باختصار وتقرر براحتك 👍",
        "نقدر متابعة خاصة معك لمتابعة الطلب وتوضيح الموعد خطوة بخطوة.",
    ),
    "warranty": (
        "الضمان جزء من راحتك 👍 أي سؤال نجاوبك بوضوح.",
        "نلخّصلك أهم بنود الضمان بجمل قصيرة تفيدك قبل إكمال الطلب.",
        "إذا تحتاج خيار استبدال أو إرجاع، نوضّح لك الخطوات ببساطة بدون إرباك.",
    ),
    "other": (
        "نحنا هنا نساعدك 🙏 أي استفسار عام عن الطلب أو المتجر قولنا باختصار.",
        "وش اللي يوقفك الآن؟ اكتب لنا باختصار ونجاوبك بطريقة مفتوحة وواضحة.",
        "نقدر متابعة خاصة معك لين ترتاح وتكمّل براحة.",
    ),
}

_PRICE_OFFER_TEXT = DASHBOARD_STAGE_TEXTS["price"][1]
_PRICE_REASSURANCE_TEXT = DASHBOARD_STAGE_TEXTS["price"][0]
# نص طمأنة قديم في الواجهة قبل التصحيح — يُعاد فقط عند تطابقه مع خطأ «الرسالة = عرض»
_PRICE_LEGACY_REASSURANCE_TEXT = (
    "نحب نطمّنك 👍 أي استفسار عن السعر أو طريقة الدفع نقدر نوضّحه باختصار."
)


def stage_default_text(reason_key: str, index: int) -> str:
    row = DASHBOARD_STAGE_TEXTS.get(reason_key)
    if not row or index < 0 or index > 2:
        return ""
    return (row[index] or "").strip()


def _coerce_mc(raw: Any) -> int:
    try:
        mc = int(raw)
    except (TypeError, ValueError):
        mc = 1
    return max(1, min(3, mc))


def _slot_dict(raw: Any, index: int) -> Dict[str, Any]:
    if isinstance(raw, dict):
        base = dict(raw)
    else:
        base = {}
    try:
        delay_v = float(base.get("delay", 1.0))
    except (TypeError, ValueError):
        delay_v = 1.0
    if delay_v <= 0:
        delay_v = 1.0
    unit = base.get("unit") or "minute"
    if unit not in ("minute", "hour"):
        unit = "minute"
    text = str(base.get("text") or "").strip()
    return {"delay": delay_v, "unit": unit, "text": text}


def enrich_reason_entry_for_dashboard(key: str, ent: Dict[str, Any]) -> Dict[str, Any]:
    """
    إثراء للعرض فقط: ملء خانات فارغة من الافتراضيات؛ إصلاح خطأ شائع لـ price
    (حقل message = نص العرض بينما المرحلة 1 فارغة أو مكررة).
    لا يكتب قاعدة البيانات — يُستدعى من GET لوحة القوالب فقط.
    """
    ent = dict(ent)
    defaults = DASHBOARD_STAGE_TEXTS.get(key)
    if not defaults:
        return ent

    mc = _coerce_mc(ent.get("message_count"))
    msgs_in = list(ent.get("messages") or [])
    msgs_out: List[Dict[str, Any]] = []
    for i in range(mc):
        raw_item = msgs_in[i] if i < len(msgs_in) else {}
        slot = _slot_dict(raw_item, i)
        if not slot["text"] and i < len(defaults):
            slot["text"] = defaults[i]
        msgs_out.append(slot)

    fallback_msg = str(ent.get("message") or "").strip()

    if key == "price":
        offer = _PRICE_OFFER_TEXT
        reassure = _PRICE_REASSURANCE_TEXT
        t0 = str(msgs_out[0].get("text") or "").strip() if msgs_out else ""
        t1 = str(msgs_out[1].get("text") or "").strip() if len(msgs_out) > 1 else ""
        if fallback_msg == offer or t0 == offer or (not t0 and fallback_msg == offer):
            if msgs_out and (not t0 or t0 == offer):
                msgs_out[0]["text"] = reassure
            fallback_msg = reassure if fallback_msg == offer else fallback_msg
        if msgs_out and t0 == offer and t1 == offer:
            msgs_out[0]["text"] = reassure
        if fallback_msg == _PRICE_LEGACY_REASSURANCE_TEXT and reassure:
            if msgs_out and str(msgs_out[0].get("text") or "").strip() in (
                "",
                _PRICE_LEGACY_REASSURANCE_TEXT,
            ):
                msgs_out[0]["text"] = reassure
            if fallback_msg == _PRICE_LEGACY_REASSURANCE_TEXT:
                fallback_msg = reassure

    text0 = str(msgs_out[0].get("text") or "").strip() if msgs_out else ""
    if text0:
        message_one = text0
    elif fallback_msg:
        message_one = fallback_msg
    elif defaults:
        message_one = defaults[0]
    else:
        message_one = ""

    ent["message"] = message_one
    ent["messages"] = msgs_out
    ent["message_count"] = mc
    return ent


def stage_texts_are_distinct(reason_key: str) -> bool:
    row = DASHBOARD_STAGE_TEXTS.get(reason_key)
    if not row:
        return True
    texts = [t.strip() for t in row if (t or "").strip()]
    return len(texts) == len(set(texts))
