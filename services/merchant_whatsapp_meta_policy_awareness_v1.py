# -*- coding: utf-8 -*-
"""Meta policy awareness — calm merchant guidance (no Meta terminology)."""
from __future__ import annotations

from typing import Any

META_POLICY_GUIDANCE_AR: tuple[str, ...] = (
    "التواصل المتوازن يحقق نتائق أفضل.",
    "إرسال عدد كبير من الرسائل خلال فترة قصيرة قد يؤثر على جودة التواصل مع العملاء.",
    "يوصى باستخدام التوقيت المقترح من CartFlow.",
)

TIMING_AUTO_ADJUST_MESSAGE_AR = (
    "تم تعديل التوقيت تلقائياً للحفاظ على جودة التواصل مع العملاء."
)


def meta_policy_guidance_for_merchant_api() -> dict[str, Any]:
    return {
        "meta_policy_awareness_architecture_only": True,
        "meta_technical_terms_hidden": True,
        "guidance_lines_ar": list(META_POLICY_GUIDANCE_AR),
        "timing_auto_adjust_message_ar": TIMING_AUTO_ADJUST_MESSAGE_AR,
    }
