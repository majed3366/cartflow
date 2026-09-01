# -*- coding: utf-8 -*-
"""Merchant-visible message body contract — strip internal/simulator markers."""
from __future__ import annotations

import re

_SRS_INTERNAL = re.compile(r"^\[SRS\]\s*", re.I)
_MOCK_SENT_INTERNAL = re.compile(r"mock_sent", re.I)


def is_internal_merchant_message_body(raw: str | None) -> bool:
    """True when body is simulator/internal-only and must not paint as sent text."""
    t = (raw or "").strip()
    if not t:
        return False
    if _SRS_INTERNAL.match(t):
        return True
    if t.startswith("[SRS]"):
        return True
    if "no provider call" in t.lower() and _MOCK_SENT_INTERNAL.search(t):
        return True
    return False


def merchant_visible_message_body(raw: str | None, *, status: str | None = None) -> str:
    """
    Presentation-only. Internal log truth unchanged in DB.
    mock_sent without merchant copy → empty (UI shows honest unavailable / trial status).
    """
    t = (raw or "").strip()
    if not t or t in {"—", "-"}:
        return ""
    if is_internal_merchant_message_body(t):
        return ""
    st = (status or "").strip().lower()
    if st == "mock_sent" and is_internal_merchant_message_body(t):
        return ""
    return t
