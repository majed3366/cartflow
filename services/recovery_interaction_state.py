# -*- coding: utf-8 -*-
"""
حالات تفاعلية للاسترجاع العادي — طبقة بيانات فقط (توسعة لاحقة: صندوق وارد، ذكاء، تصعيد).
"""
from __future__ import annotations

from typing import Optional

STATE_REPLIED = "replied"
STATE_ENGAGED = "engaged"
STATE_WAITING_MERCHANT = "waiting_merchant"
STATE_RECOVERED = "recovered"
STATE_CLOSED = "closed"

_VALID = frozenset(
    {
        STATE_REPLIED,
        STATE_ENGAGED,
        STATE_WAITING_MERCHANT,
        STATE_RECOVERED,
        STATE_CLOSED,
    }
)


def normalize_interaction_state(raw: Optional[str]) -> str:
    s = (raw or "").strip().lower()
    return s if s in _VALID else STATE_ENGAGED


def is_terminal_interaction_state(state: Optional[str]) -> bool:
    snormalize = (state or "").strip().lower()
    return snormalize in (STATE_RECOVERED, STATE_CLOSED)


def truncate_preview_text(text: str, *, max_chars: int = 140) -> str:
    t = (text or "").strip().replace("\r\n", "\n").replace("\r", "\n")
    if not t:
        return ""
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rstrip() + "…"
