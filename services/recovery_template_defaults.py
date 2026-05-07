# -*- coding: utf-8 -*-
"""
قوالب افتراضية مُنظَّمة لاسترجاع عادي — لكل سبب × 3 محاولات (مساعدة، طمأنة، تذكير لطيف).

طبقة بيانات فقط؛ التخزين في ‎recovery_template_storage‎ والتنسيق في ‎recovery_message_strategy‎.
"""
from __future__ import annotations

from typing import Dict

# مفاتيح تطابق ‎reason_templates‎ بعد التوسيع (‎delivery‎، ‎other‎).
DEFAULT_GUIDED_COPY: Dict[str, Dict[int, str]] = {
    "price": {
        1: "هلا 👋 لاحظنا إنك ما كمّلت الطلب — نقدر نساعدك بخطوة بسيطة إذا حاب.",
        2: "إذا عندك أي استفسار أو تردد بالطلب نقدر نساعدك 👍",
        3: "طلبك ما زال محفوظ 👍 إذا حاب تكمل قبل نفاد الكمية.",
    },
    "shipping": {
        1: "هلا 👋 بخصوص الشحن — إذا عندك أي استفسار عن التكلفة أو الخيارات نقدر نوضح لك بسرعة.",
        2: "تفاصيل الشحن مهمة 👍 إذا في شي يوقفك قولّنا ونساعدك بدون تعقيد.",
        3: "طلبك لسه محفوظ 🚚 إذا حاب تكمل نراجع معك أفضل خيار للشحن.",
    },
    "delivery": {
        1: "هلا 👋 بخصوص موعد التوصيل — نقدر نعطيك توضيح بسيط عن المدة المتوقعة إذا حاب.",
        2: "نوعدك بالوضوح بموعد التوصيل 👍 أي استفسار عن الوقت حنا حاضرين.",
        3: "تذكير لطيف 👌 طلبك منتظر إكماله — إذا يناسبك تقدر تكمل الآن.",
    },
    "warranty": {
        1: "هلا 👋 بخصوص الضمان — إذا تحب نلخّص لك أهم النقاط بجمل قصيرة نقدر.",
        2: "الضمان جزء من راحتك 👍 أي سؤال نجاوبك بكل صراحة.",
        3: "طلبك ما زال متاح للإكمال 👍 إذا حاب تكمل نكون سعداء نخدمك.",
    },
    "quality": {
        1: "هلا 👋 الجودة تهمنا مثلك — إذا في نقطة تحتاج توضيح نقدر نسهّلها عليك.",
        2: "نقدر نطمّنك على معايير الجودة 👍 اسأل براحتك، بدون ضغط.",
        3: "تذكير ودود 👌 طلبك محفوظ، ونسعد لو حاب تكمل.",
    },
    "thinking": {
        1: "هلا 👋 خذ راحتك — إذا تحب نمشي معك خطوة بسيطة عشان تكمل الطلب نقدر.",
        2: "التردد طبيعي 👍 نقدر نساعدك تقرر براحة، بدون إحساس بضغط.",
        3: "تذكير لطيف: طلبك لسه موجود 👍 أي سؤال نرحّب فيه.",
    },
    "other": {
        1: "هلا 👋 لاحظنا ما كمّلت الطلب — إذا في شي وقفك قولّنا ونشوف لك حل بسيط.",
        2: "نحب نطمّنك 👍 نقدر نجاوب ونبسّط لك الخطوة اللي تناسبك.",
        3: "طلبك محفوظ 👌 إذا حاب ترجع وتكمل، نحن هنا.",
    },
}

_STRATEGY_KEYS = tuple(DEFAULT_GUIDED_COPY.keys())


def default_guided_line(strategy_key: str, attempt_index: int) -> str:
    """نص افتراضي لمحاولة ‎1..3‎؛ مفتاح غير معروف يُعامل كـ ‎other‎."""
    try:
        n = int(attempt_index)
    except (TypeError, ValueError):
        n = 1
    if n < 1:
        n = 1
    if n > 3:
        n = 3
    sk = (strategy_key or "").strip().lower()
    if sk not in DEFAULT_GUIDED_COPY:
        sk = "other"
    row = DEFAULT_GUIDED_COPY.get(sk) or DEFAULT_GUIDED_COPY["other"]
    return (row.get(n) or "").strip()


def guided_defaults_for_api() -> Dict[str, Dict[str, str]]:
    """لـ ‎GET /api/recovery-settings‎ — مفاتيح نصية ‎\"1\"/\"2\"/\"3\"‎ للواجهة."""
    out: Dict[str, Dict[str, str]] = {}
    for sk, row in DEFAULT_GUIDED_COPY.items():
        out[sk] = {
            "1": (row.get(1) or "").strip(),
            "2": (row.get(2) or "").strip(),
            "3": (row.get(3) or "").strip(),
        }
    return out


def all_strategy_keys() -> tuple[str, ...]:
    return _STRATEGY_KEYS
