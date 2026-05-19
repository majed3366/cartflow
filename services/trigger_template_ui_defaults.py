# -*- coding: utf-8 -*-
"""
نصوص المراحل الافتراضية لواجهة «قوالب حسب سبب التردد» فقط.

لا تُستخدم في مسار إرسال واتساب / محرّك القرار — عرض وإصلاح عرض لوحة التاجر.
"""
from __future__ import annotations

import re
from typing import Any, Dict, FrozenSet, List, Tuple

# (مرحلة 1 طمأنة، مرحلة 2 عرض/تفاصيل، مرحلة 3 بديل/متابعة)
DASHBOARD_STAGE_TEXTS: Dict[str, Tuple[str, str, str]] = {
    "price": (
        "نعرف إن السعر قرار مهم 👍 إذا عندك استفسار عن السعر أو الدفع نوضحه بسرعة.",
        "عندنا عرض ممكن يساعدك تكمل الطلب، تحب نرسل لك التفاصيل؟",
        "عندنا خيارات بديلة أو باكج قد يفيدك أكثر 👍 نقدر نلخصها لك بسرعة إذا حاب.",
    ),
    "quality": (
        "نحب نطمنك 👍 إذا عندك أي سؤال عن جودة المنتج أو تفاصيله نوضحها لك باختصار.",
        "نقدر نشرح لك أهم المواصفات بجمل بسيطة تسهّل القرار بدون تعقيد.",
        "كثير من عملائنا اختاروا نفس المنتج برضا 👍 إذا حاب نعطيك فكرة سريعة عن التجارب.",
    ),
    "shipping": (
        "نوضح لك خيارات الشحن والتكلفة بكل اختصار 👍",
        "إذا يتوفر شحن مجاني أو عرض شحن يناسبك، نشرح لك الشروط باختصار بدون التزام منك الآن.",
        "إذا حاب، نوضح لك آخر تحديثات الشحن أو الخيارات المتاحة بسرعة 👍",
    ),
    "delivery": (
        "نقدر نوضح لك مدة التوصيل المتوقعة قبل ما تكمل الطلب 👍",
        "إذا فيه خيار أسرع أو أقرب لموعدك، نوضح لك المتاح باختصار.",
        "إذا حاب، نوضح لك آخر موعد متوقع أو أي تحديث يفيد قرارك 👍",
    ),
    "warranty": (
        "نوضح لك تفاصيل الضمان أو الاستبدال بكل بساطة 👍",
        "نلخّصلك أهم بنود الضمان بجمل قصيرة تفيدك قبل إكمال الطلب.",
        "إذا تحتاج خيار استبدال أو إرجاع، نوضّح لك الخطوات ببساطة بدون إرباك.",
    ),
    "other": (
        "نقدر نساعدك بأي استفسار قبل إكمال الطلب 👍",
        "وش اللي يوقفك الآن؟ اكتب لنا باختصار ونجاوبك بطريقة مفتوحة وواضحة.",
        "نقدر متابعة خاصة معك لين ترتاح وتكمّل براحة.",
    ),
}

_LOADTEST_PLACEHOLDER_RE = re.compile(r"LOADTEST_STORE_\d+", re.IGNORECASE)

# نصوص مرحلة 1/رسالة قديمة أو خطأ شائع (عرض في المرحلة 1) — تُستبدل عند العرض فقط
_LEGACY_WRONG_STAGE1: Dict[str, FrozenSet[str]] = {
    "price": frozenset(
        {
            DASHBOARD_STAGE_TEXTS["price"][1],
            "نحب نطمّنك 👍 أي استفسار عن السعر أو طريقة الدفع نقدر نوضّحه باختصار.",
        }
    ),
    "quality": frozenset(
        {
            "الجودة عندنا خط واضح 👍 أي نقطة تحتاج طمأنة نجاوبك بكل صراحة.",
            DASHBOARD_STAGE_TEXTS["quality"][1],
            DASHBOARD_STAGE_TEXTS["quality"][2],
        }
    ),
    "shipping": frozenset(
        {
            "بخصوص الشحن: نقدر نوضّح لك المدة والتكلفة والخيارات المتاحة لمنطقتك.",
            DASHBOARD_STAGE_TEXTS["shipping"][1],
            DASHBOARD_STAGE_TEXTS["shipping"][2],
            "نقدر نتابع معك بشكل خاص لحد ما ترتاح من تفاصيل الشحن والتسليم.",
        }
    ),
    "delivery": frozenset(
        {
            "بخصوص موعد التوصيل: نعطيك توقيتاً تقريبياً واضحاً يناسب عنوانك.",
            DASHBOARD_STAGE_TEXTS["delivery"][1],
            DASHBOARD_STAGE_TEXTS["delivery"][2],
            "إذا في خيار أسرع أو تسريع متاح لموقعك، نبلغك باختصار وتقرر براحتك 👍",
            "نقدر متابعة خاصة معك لمتابعة الطلب وتوضيح الموعد خطوة بخطوة.",
        }
    ),
    "warranty": frozenset(
        {
            "الضمان جزء من راحتك 👍 أي سؤال نجاوبك بوضوح.",
            DASHBOARD_STAGE_TEXTS["warranty"][1],
            DASHBOARD_STAGE_TEXTS["warranty"][2],
        }
    ),
    "other": frozenset(
        {
            "نحنا هنا نساعدك 🙏 أي استفسار عام عن الطلب أو المتجر قولنا باختصار.",
            DASHBOARD_STAGE_TEXTS["other"][1],
            DASHBOARD_STAGE_TEXTS["other"][2],
        }
    ),
}


def is_loadtest_placeholder(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return bool(_LOADTEST_PLACEHOLDER_RE.search(t))


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


def _slot_dict(raw: Any) -> Dict[str, Any]:
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


def _stage1_needs_repair(key: str, text: str, defaults: Tuple[str, str, str]) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if is_loadtest_placeholder(t):
        return True
    if len(defaults) > 1 and t == defaults[1]:
        return True
    if len(defaults) > 2 and t == defaults[2]:
        return True
    legacy = _LEGACY_WRONG_STAGE1.get(key)
    if legacy and t in legacy:
        return True
    return False


def _repair_slot_text(
    key: str,
    index: int,
    text: str,
    defaults: Tuple[str, str, str],
) -> str:
    t = (text or "").strip()
    if index >= len(defaults):
        return t
    default_for_slot = defaults[index]
    if not t:
        return default_for_slot
    if is_loadtest_placeholder(t):
        return default_for_slot
    if index == 0 and _stage1_needs_repair(key, t, defaults):
        return defaults[0]
    return t


def enrich_reason_entry_for_dashboard(key: str, ent: Dict[str, Any]) -> Dict[str, Any]:
    """
    إثراء للعرض فقط: ملء خانات فارغة؛ إصلاح مرحلة 1 (طمأنة)؛ إزالة عناوين LOADTEST.
    لا يكتب قاعدة البيانات — يُستدعى من GET/POST استجابة لوحة القوالب فقط.
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
        slot = _slot_dict(raw_item)
        slot["text"] = _repair_slot_text(key, i, slot["text"], defaults)
        msgs_out.append(slot)

    fallback_msg = str(ent.get("message") or "").strip()
    fallback_msg = _repair_slot_text(key, 0, fallback_msg, defaults)

    text0 = str(msgs_out[0].get("text") or "").strip() if msgs_out else ""
    if text0:
        message_one = text0
    elif fallback_msg:
        message_one = fallback_msg
    else:
        message_one = defaults[0]

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
