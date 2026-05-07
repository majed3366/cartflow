# -*- coding: utf-8 -*-
"""
طبقة نصوص الاسترجاع حسب رقم المحاولة — جاهزة لاحقاً لـ A/B ووكلاء الذكاء وتخصيص التاجر.

لا يغيّر التوقيت أو الإرسال؛ استدعِ get_recovery_message فقط عند تكوين النص.
"""
from __future__ import annotations

import hashlib
from typing import Optional

# محاولة 1 — دعم ودي، فتح محادثة
_ATTEMPT_SUPPORT_AR: tuple[str, ...] = (
    "هلا 👋 لاحظنا إنك ما كمّلت الطلب — نقدر نساعدك بخطوة بسيطة إذا حاب.",
)

# محاولة 2 — طمأنة وتقليل احتكاك
_ATTEMPT_REASSURANCE_AR: tuple[str, ...] = (
    "إذا عندك أي استفسار أو تردد بالطلب نقدر نساعدك 👍",
    "أحيانًا يبقى الطلب معلّق بسبب تردد بسيط — إذا حاب نوضح أي شيء حنا بالخدمة 🙌",
)

# محاولة 3 — إلحاح لطيف دون ضغط مزعج
_ATTEMPT_SOFT_URGENCY_AR: tuple[str, ...] = (
    "بعض المنتجات تنفد بسرعة لذلك حبينا نذكرك فقط 👌",
    "طلبك ما زال محفوظ 👍 إذا حاب تكمل قبل نفاد الكمية.",
)


def _stable_variant_index(reason_tag: Optional[str], modulo: int) -> int:
    if modulo <= 0:
        return 0
    key = (reason_tag or "default").strip().lower() or "default"
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)
    return h % modulo


def _pick_from_variants(reason_tag: Optional[str], variants: tuple[str, ...]) -> str:
    if not variants:
        return ""
    i = _stable_variant_index(reason_tag, len(variants))
    return (variants[i] or "").strip() or variants[0].strip()


def get_recovery_message(reason_tag: Optional[str], attempt_index: int) -> str:
    """
    نص استرجاع عادي حسب المحاولة (1 = دعم، 2 = طمأنة، 3 = تذكير لطيف).
    ‎reason_tag‎ يغيّر فقط اختيار بديل ضمن نفس النبرة (مستقر بين الطلبات).
    """
    try:
        n = int(attempt_index)
    except (TypeError, ValueError):
        n = 1
    if n < 1:
        n = 1
    if n > 3:
        n = 3
    if n == 1:
        return _ATTEMPT_SUPPORT_AR[0].strip()
    if n == 2:
        return _pick_from_variants(reason_tag, _ATTEMPT_REASSURANCE_AR)
    return _pick_from_variants(reason_tag, _ATTEMPT_SOFT_URGENCY_AR)
