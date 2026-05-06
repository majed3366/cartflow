# -*- coding: utf-8 -*-
"""رسائل المتابعة الذكية للاسترجاع العادي — نصوص مختصرة غير مكررة للرسالة الأولى."""
from __future__ import annotations

from typing import Any, Optional


_SECOND_ATTEMPT_MESSAGES_AR: tuple[str, ...] = (
    "إذا احتجت أي مساعدة بالطلب حنا موجودين 👍",
    "باقي طلبك محفوظ لك 🙌 تقدر تكمل لما يكون مريح لك.",
)


def resolve_smart_second_recovery_message(
    first_message_body: str,
    reason_tag: Optional[str],
    store: Any,
) -> str:
    """
    اختيار رسالة ثانية قصيرة وإنسانية، مختلفة عن الأولى قدر الإمكان.
    ‎reason_tag‎ و ‎store‎ جاهزان لتوسعة لاحقة (قوالب لكل سبب).
    """
    _ = (reason_tag, store)
    first = (first_message_body or "").strip()
    for cand in _SECOND_ATTEMPT_MESSAGES_AR:
        c = cand.strip()
        if c and c != first:
            return c
    return _SECOND_ATTEMPT_MESSAGES_AR[0]
