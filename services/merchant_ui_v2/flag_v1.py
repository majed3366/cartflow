# -*- coding: utf-8 -*-
"""Merchant UI V2 feature gate — production Home baseline with V1 rollback."""
from __future__ import annotations

import os
from typing import Any, Mapping, MutableMapping, Optional

FLAG_MERCHANT_UI_V2 = "CARTFLOW_MERCHANT_UI_V2"
COOKIE_MERCHANT_UI_V2 = "cf_ui_v2"
QUERY_MERCHANT_UI_V2 = "cf_ui"

# Production default after Home Desktop Stage Closure V1 approval (71cf4e3).
DEFAULT_MERCHANT_UI_V2 = True


def _truthy(raw: str) -> Optional[bool]:
    v = (raw or "").strip().lower()
    if v in {"1", "true", "yes", "on", "v2"}:
        return True
    if v in {"0", "false", "no", "off", "v1"}:
        return False
    return None


def merchant_ui_v2_env_enabled() -> bool:
    """
    Env override for the production default.

    - unset → DEFAULT_MERCHANT_UI_V2 (ON)
    - CARTFLOW_MERCHANT_UI_V2=0|false|v1 → force V1 rollback
    - CARTFLOW_MERCHANT_UI_V2=1|true|v2 → force V2
    """
    decided = _truthy(os.environ.get(FLAG_MERCHANT_UI_V2) or "")
    return bool(decided) if decided is not None else DEFAULT_MERCHANT_UI_V2


def merchant_ui_selection_source(
    *,
    query: Optional[Mapping[str, Any]] = None,
    cookies: Optional[Mapping[str, Any]] = None,
) -> str:
    """How V1/V2 was chosen. query | cookie_v2 | env | default.

    Cookie ``cf_ui_v2=0`` is not a selector (INV-VIS-07). Only ``=1`` counts.
    """
    q = query or {}
    raw_q = ""
    if hasattr(q, "get"):
        raw_q = str(q.get(QUERY_MERCHANT_UI_V2) or "")
    if _truthy(raw_q) is not None:
        return "query"
    c = cookies or {}
    raw_c = ""
    if hasattr(c, "get"):
        raw_c = str(c.get(COOKIE_MERCHANT_UI_V2) or "")
    if _truthy(raw_c) is True:
        return "cookie"
    if (os.environ.get(FLAG_MERCHANT_UI_V2) or "").strip():
        return "env"
    return "default"


def leftover_v1_cookie(
    *,
    cookies: Optional[Mapping[str, Any]] = None,
) -> bool:
    """True when a stale rollback cookie is present (must not select V1)."""
    c = cookies or {}
    raw_c = ""
    if hasattr(c, "get"):
        raw_c = str(c.get(COOKIE_MERCHANT_UI_V2) or "")
    return _truthy(raw_c) is False


def merchant_ui_v2_requested(
    *,
    query: Optional[Mapping[str, Any]] = None,
    cookies: Optional[Mapping[str, Any]] = None,
) -> bool:
    """
    Production Home V2 is the default surface.

    Priority (highest first):
    1. ?cf_ui=v2|v1 (explicit compare / rollback) — only explicit V1
    2. cookie cf_ui_v2=1 (persisted V2 / review bind). Cookie=0 is ignored.
    3. env CARTFLOW_MERCHANT_UI_V2 (or DEFAULT_MERCHANT_UI_V2 when unset)
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
    if decided_c is True:
        return True

    return merchant_ui_v2_env_enabled()


def merchant_ui_v2_cookie_value(enabled: bool) -> str:
    return "1" if enabled else "0"


def apply_merchant_ui_v2_cookie(
    response: Any,
    enabled: bool,
    *,
    max_age: int = 60 * 60 * 24 * 14,
) -> Any:
    """Persist V2 only. V1 rollback is query-scoped and must not leave cookie=0."""
    if not enabled:
        if hasattr(response, "delete_cookie"):
            response.delete_cookie(key=COOKIE_MERCHANT_UI_V2, path="/")
        return response
    response.set_cookie(
        key=COOKIE_MERCHANT_UI_V2,
        value=merchant_ui_v2_cookie_value(True),
        max_age=max_age,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return response


def heal_silent_v1_cookie(
    response: Any,
    *,
    query: Optional[Mapping[str, Any]] = None,
    cookies: Optional[Mapping[str, Any]] = None,
) -> Any:
    """Overwrite leftover cf_ui_v2=0 when this request is canonical V2."""
    q = query or {}
    raw_q = ""
    if hasattr(q, "get"):
        raw_q = str(q.get(QUERY_MERCHANT_UI_V2) or "")
    if _truthy(raw_q) is False:
        return response
    if leftover_v1_cookie(cookies=cookies) and merchant_ui_v2_requested(
        query=query, cookies=cookies
    ):
        apply_merchant_ui_v2_cookie(response, True)
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
        "default": DEFAULT_MERCHANT_UI_V2,
        "rollback": {
            "query": "?cf_ui=v1",
            "cookie": f"{COOKIE_MERCHANT_UI_V2}=0",
            "env": f"{FLAG_MERCHANT_UI_V2}=0",
            "dev_route": "/dev/merchant-ui-v1",
        },
        "surfaces": ["frame", "home", "workspace"],
        "home_visual_baseline": "71cf4e3",
    }
