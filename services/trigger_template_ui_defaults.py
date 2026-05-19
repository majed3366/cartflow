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

# تأخير مقترح لكل مرحلة (قيمة عرض الواجهة: minute | hour | day) — يُطبَّق فقط على خانات جديدة/فارغة
DASHBOARD_STAGE_DELAYS: Dict[str, List[Tuple[float, str]]] = {
    "price": [(60.0, "minute"), (5.0, "hour"), (5.0, "day")],
    "quality": [(90.0, "minute"), (8.0, "hour"), (5.0, "day")],
    "shipping": [(30.0, "minute"), (4.0, "hour"), (2.0, "day")],
    "delivery": [(30.0, "minute"), (6.0, "hour"), (3.0, "day")],
    "warranty": [(2.0, "hour"), (12.0, "hour"), (5.0, "day")],
    "other": [(3.0, "hour"), (1.0, "day"), (5.0, "day")],
}

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


def _coerce_messages_list(raw: Any) -> List[Any]:
    """‎messages‎ قد يكون غير قائمة في بيانات قديمة — لا نُسقِط تحميل اللوحة."""
    if isinstance(raw, list):
        return raw
    return []


def _persist_delay_for_api(value: float, unit: str) -> Tuple[float, str]:
    u = (unit or "minute").strip().lower()
    if u == "day":
        return (float(value) * 24.0, "hour")
    if u == "hour":
        return (float(value), "hour")
    return (float(value), "minute")


def _is_generic_legacy_delay(index: int, delay: float, unit: str) -> bool:
    """تأخيرات بذور قديمة فقط (1–2 د للمرحلة 1) — لا تُعامل 3–5 د كغير مُعدّة."""
    u = (unit or "minute").strip().lower()
    try:
        d = float(delay)
    except (TypeError, ValueError):
        return False
    if u == "minute":
        if index == 0 and d in (1.0, 2.0):
            return True
        if index > 0 and d in (1.0, 2.0, 120.0):
            return True
    if u == "hour" and index == 0 and d == 1.0:
        return True
    return False


def _text_is_defaultish_for_delay(
    key: str,
    index: int,
    text: str,
    defaults: Tuple[str, str, str],
    *,
    fallback_message: str = "",
) -> bool:
    t = (text or "").strip()
    if not t and index == 0:
        t = (fallback_message or "").strip()
    if not t:
        return True
    if is_loadtest_placeholder(t):
        return True
    if index < len(defaults) and t == defaults[index]:
        return True
    legacy = _LEGACY_WRONG_STAGE1.get(key)
    if legacy and t in legacy:
        return True
    if index == 0 and _stage1_needs_repair(key, t, defaults):
        return True
    return False


def _should_apply_recommended_delay(
    key: str,
    index: int,
    slot: Dict[str, Any],
    had_raw: bool,
    defaults: Tuple[str, str, str],
    raw_text: str,
    fallback_message: str,
) -> bool:
    if not had_raw:
        return True
    raw_t = (raw_text or "").strip()
    if is_loadtest_placeholder(raw_t):
        return True
    if _text_is_defaultish_for_delay(
        key, index, raw_t, defaults, fallback_message=fallback_message
    ) and _is_generic_legacy_delay(
        index, float(slot.get("delay", 0)), str(slot.get("unit") or "minute")
    ):
        return True
    return False


def _apply_recommended_delay_to_slot(
    key: str, index: int, slot: Dict[str, Any]
) -> Dict[str, Any]:
    row = DASHBOARD_STAGE_DELAYS.get(key)
    if not row or index >= len(row):
        return slot
    val, unit = row[index]
    delay_v, unit_v = _persist_delay_for_api(val, unit)
    slot["delay"] = delay_v
    slot["unit"] = unit_v
    return slot


def format_delay_for_dashboard_ui(delay: float, unit: str) -> str:
    """صيغة عرض مطابقة للوحة (دقائق / ساعات / أيام)."""
    u = (unit or "minute").strip().lower()
    d = float(delay)
    if u == "hour" and d >= 24:
        days = d / 24.0
        rnd = round(days)
        if rnd >= 1 and abs(days - rnd) < 1e-6:
            return f"{rnd} يوم"
    if u == "hour":
        iv = int(d) if d == int(d) else d
        return f"{iv} ساعة"
    iv = int(d) if d == int(d) else d
    return f"{iv} دقيقة"


def stage_default_delay_ui(reason_key: str, index: int) -> Tuple[float, str]:
    row = DASHBOARD_STAGE_DELAYS.get(reason_key)
    if not row or index < 0 or index >= len(row):
        return (60.0, "minute")
    val, unit = row[index]
    return (float(val), str(unit))


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
    try:
        if not isinstance(ent, dict):
            ent = {}
        else:
            ent = dict(ent)
        defaults = DASHBOARD_STAGE_TEXTS.get(key)
        if not defaults:
            return ent

        mc = _coerce_mc(ent.get("message_count"))
        msgs_in = _coerce_messages_list(ent.get("messages"))
        msgs_out: List[Dict[str, Any]] = []
        fallback_msg = str(ent.get("message") or "").strip()
        for i in range(mc):
            had_raw = i < len(msgs_in) and isinstance(msgs_in[i], dict)
            raw_item = msgs_in[i] if had_raw else {}
            raw_text = str(raw_item.get("text") or "").strip() if had_raw else ""
            slot = _slot_dict(raw_item)
            if _should_apply_recommended_delay(
                key, i, slot, had_raw, defaults, raw_text, fallback_msg
            ):
                slot = _apply_recommended_delay_to_slot(key, i, slot)
            slot["text"] = _repair_slot_text(key, i, slot["text"], defaults)
            msgs_out.append(slot)

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
    except Exception:
        if isinstance(ent, dict):
            safe = dict(ent)
            safe["messages"] = _coerce_messages_list(ent.get("messages"))
            return safe
        return {}


def stage_texts_are_distinct(reason_key: str) -> bool:
    row = DASHBOARD_STAGE_TEXTS.get(reason_key)
    if not row:
        return True
    texts = [t.strip() for t in row if (t or "").strip()]
    return len(texts) == len(set(texts))
