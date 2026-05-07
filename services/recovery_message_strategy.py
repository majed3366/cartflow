# -*- coding: utf-8 -*-
"""
طبقة نصوص الاسترجاع حسب السبب ورقم المحاولة — جاهزة لاحقاً لـ A/B ووكلاء الذكاء وتخصيص التاجر.

لا يغيّر التوقيت أو الإرسال؛ استدعِ ‎get_recovery_message‎ فقط عند تكوين النص.
"""
from __future__ import annotations

from typing import Any, Optional

from services.recovery_template_defaults import default_guided_line
from services.recovery_template_storage import get_merchant_guided_line, strategy_key_for_tag


def get_recovery_message(
    reason_tag: Optional[str],
    attempt_index: int,
    store: Any = None,
) -> str:
    """
    نص استرجاع عادي حسب المحاولة (1 = دعم، 2 = طمأنة، 3 = تذكير لطيف).
    يقرأ ‎guided_attempts‎ من ‎Store‎ إن وُجدت؛ وإلا القوالب الافتراضية المنسّقة لكل سبب.
    """
    try:
        n = int(attempt_index)
    except (TypeError, ValueError):
        n = 1
    if n < 1:
        n = 1
    if n > 3:
        n = 3
    if store is not None:
        custom = get_merchant_guided_line(store, reason_tag, n)
        if custom:
            return custom.strip()
    sk = strategy_key_for_tag(reason_tag)
    return default_guided_line(sk, n)
