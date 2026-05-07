# -*- coding: utf-8 -*-
"""Dev / demo-only helpers for ‎cf_test_phone‎ (normal recovery QA — not production customer UX)."""
from __future__ import annotations

import os
from typing import Any


def cf_test_customer_phone_override_allowed(store_slug: str) -> bool:
    env = (os.getenv("ENV") or "").strip().lower()
    if env == "development":
        return True
    ss = (store_slug or "").strip().lower()
    return ss == "demo"


def normalize_cf_test_customer_phone(raw: Any) -> str:
    """Match ‎main._normalize_customer_phone_for_wa_me‎ (SA WhatsApp digits)."""
    if raw is None or not str(raw).strip():
        return ""
    d = "".join(c for c in str(raw) if c.isdigit())
    if not d:
        return ""
    if len(d) == 9 and d.startswith("5"):
        return "966" + d
    if len(d) == 10 and d.startswith("05"):
        return "966" + d[1:]
    if d.startswith("966") and len(d) >= 11:
        return d
    return d
