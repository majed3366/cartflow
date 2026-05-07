# -*- coding: utf-8 -*-
"""Psychology-differentiated copy for sequential normal recovery (when templates empty)."""
from __future__ import annotations

from typing import Any, Optional

from services.normal_recovery_followup_message import resolve_smart_second_recovery_message


_SECOND_ANGLE_MESSAGES_AR: tuple[str, ...] = (
    "إذا عندك أي تردد أو استفسار بسيط، نقدر نوضّحه لك بدون إلحاح 👍",
    "كثير من عملاء المتجر يطلعون من السلة ويرجعون لاحقاً ويكملون بسهولة — الأختيار لك.",
)


_THIRD_ANGLE_MESSAGES_AR: tuple[str, ...] = (
    "بعض المنتجات تنفد بسرعة؛ حبينا نذكرك بس لو حاب تكمّل الطلب 👌",
    "لسه السلة محفوظة؛ إذا احتجت خطوة بسيطة نكمّل معك.",
)


def resolve_behavioral_followup_message(
    *,
    step_num: int,
    first_message_body: str,
    second_message_body: str,
    reason_tag: Optional[str],
    store: Any,
) -> str:
    """
    step_num 2: reassurance / social proof (never reuse first structure).
    step_num 3+: soft urgency / gentle scarcity (short, Saudi-friendly).
    Falls back to resolve_smart_second_recovery_message for step 2 legacy path.
    """
    first = (first_message_body or "").strip()
    second_ref = (second_message_body or "").strip()
    if step_num <= 2:
        base = resolve_smart_second_recovery_message(first, reason_tag, store)
        for cand in _SECOND_ANGLE_MESSAGES_AR:
            c = cand.strip()
            if c and c != first and c != second_ref and c != base:
                return c
        return base
    for cand in _THIRD_ANGLE_MESSAGES_AR:
        c = cand.strip()
        if c and c != first and c != second_ref:
            return c
    return _THIRD_ANGLE_MESSAGES_AR[0]
