# -*- coding: utf-8 -*-
"""Merchant UI V2 feature gate — clean-slate vertical slice (frame + Home + Workspace)."""
from __future__ import annotations

import os
from typing import Any, Mapping, MutableMapping, Optional

FLAG_MERCHANT_UI_V2 = "CARTFLOW_MERCHANT_UI_V2"
COOKIE_MERCHANT_UI_V2 = "cf_ui_v2"
QUERY_MERCHANT_UI_V2 = "cf_ui"


def _truthy(raw: str) -> Optional[bool]:
    v = (raw or "").strip().lower()
    if v in {"1", "true", "yes", "on", "v2"}:
        return True
    if v in {"0", "false", "no", "off", "v1"}:
        return False
    return None


def merchant_ui_v2_env_enabled() -> bool:
    """Explicit env only — default OFF so V1 remains production until approval."""
    decided = _truthy(os.environ.get(FLAG_MERCHANT_UI_V2) or "")
    return bool(decided) if decided is not None else False


def merchant_ui_v2_requested(
    *,
    query: Optional[Mapping[str, Any]] = None,
    cookies: Optional[Mapping[str, Any]] = None,
) -> bool:
    """
    Review/compare gate inside real /dashboard.

    Priority:
    1. ?cf_ui=v2|v1 (explicit)
    2. cookie cf_ui_v2=1|0
    3. env CARTFLOW_MERCHANT_UI_V2
    """
    q = query or {}
    raw_q = ""
    if hasattr(q, "get"):
        raw_q = str(q.get(QUERY_MERCHANT_UI_V2) or "")
    decided_q = _truthy(raw_q)
    if decided_q is not None:
        return decided_q

    c = cookies or {}
    raw_c = ""
    if hasattr(c, "get"):
        raw_c = str(c.get(COOKIE_MERCHANT_UI_V2) or "")
    decided_c = _truthy(raw_c)
    if decided_c is not None:
        return decided_c

    return merchant_ui_v2_env_enabled()


def merchant_ui_v2_cookie_value(enabled: bool) -> str:
    return "1" if enabled else "0"


def apply_merchant_ui_v2_cookie(
    response: Any,
    enabled: bool,
    *,
    max_age: int = 60 * 60 * 24 * 14,
) -> Any:
    """Attach review cookie so subsequent /dashboard loads keep V2 without query."""
    response.set_cookie(
        key=COOKIE_MERCHANT_UI_V2,
        value=merchant_ui_v2_cookie_value(enabled),
        max_age=max_age,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return response


def merchant_ui_v2_flag_state(
    *,
    query: Optional[Mapping[str, Any]] = None,
    cookies: Optional[Mapping[str, Any]] = None,
) -> dict:
    return {
        "flag": FLAG_MERCHANT_UI_V2,
        "cookie": COOKIE_MERCHANT_UI_V2,
        "query": QUERY_MERCHANT_UI_V2,
        "enabled": merchant_ui_v2_requested(query=query, cookies=cookies),
        "env_enabled": merchant_ui_v2_env_enabled(),
        "env_raw": (os.environ.get(FLAG_MERCHANT_UI_V2) or "").strip() or None,
        "default": False,
        "surfaces": ["frame", "home", "workspace"],
    }
