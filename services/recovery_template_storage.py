# -*- coding: utf-8 -*-
"""
قراءة ‎guided_attempts‎ من ‎Store.reason_templates_json‎ — طبقة تخزين منفصلة للتوسعة (A/B، ذكاء، توصيات).
"""
from __future__ import annotations

from typing import Any, Optional

from services.reason_template_recovery import canonical_reason_template_key
from services.store_reason_templates import (
    _parse_guided_attempts_column,
    parse_reason_templates_column,
)


def strategy_key_for_tag(reason_tag: Optional[str]) -> str:
    """
    مفتاح استراتيجية للنصوص الموجّهة؛ ‎None‎ أو غير معروف → ‎other‎.
    """
    canon = canonical_reason_template_key(reason_tag)
    if canon is not None:
        return canon
    return "other"


def get_merchant_guided_line(store: Any, reason_tag: Optional[str], attempt_index: int) -> Optional[str]:
    """نص التاجر لمحاولة ‎1..3‎ أو ‎None‎."""
    try:
        n = int(attempt_index)
    except (TypeError, ValueError):
        n = 1
    if n < 1:
        n = 1
    if n > 3:
        n = 3
    sk = strategy_key_for_tag(reason_tag)
    templates = parse_reason_templates_column(
        getattr(store, "reason_templates_json", None) if store is not None else None
    )
    entry = templates.get(sk)
    if not isinstance(entry, dict):
        return None
    ga = _parse_guided_attempts_column(entry.get("guided_attempts"))
    return ga.get(str(n))
