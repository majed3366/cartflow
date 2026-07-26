# -*- coding: utf-8 -*-
"""
Merchant Session Identity V1 — account verification panel payload.

Thin composition over existing auth + store connection. No new engines.
Allows demo / Living Store review principals (unlike onboarding resolve).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.living_store_reality_prod_v1 import REVIEW_EMAIL
from services.merchant_auth_http import (
    merchant_cookie_name,
    parse_merchant_session_cookie_value,
)
from services.merchant_auth_v1 import (
    get_merchant_user_by_id,
    get_primary_store_for_merchant,
    is_development_env,
)
from services.merchant_onboarding_store import merchant_store_display_name
from services.merchant_store_connection_v1 import (
    build_merchant_store_connection_status_for_store,
    is_merchant_store_platform_connected,
)
from services.store_reality_simulator.contracts_v1 import DEMO_STORE_SLUG

_TTL_S = 14 * 24 * 3600


def _signing_secret() -> bytes:
    return (
        os.getenv("SECRET_KEY") or "dev-only-change-in-production"
    ).strip().encode("utf-8")


def _parse_cookie_exp(raw: str | None) -> Optional[int]:
    if not raw or raw.count(":") != 2:
        return None
    _mid_s, exp_s, _sig = raw.split(":", 2)
    try:
        exp = int(exp_s)
    except ValueError:
        return None
    return exp if exp > 0 else None


def _fmt_utc(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )


def _session_fingerprint(*, merchant_id: int, store_slug: str, exp: int) -> str:
    payload = f"{int(merchant_id)}|{(store_slug or '').strip()}|{int(exp)}".encode(
        "utf-8"
    )
    digest = hmac.new(_signing_secret(), payload, hashlib.sha256).hexdigest()
    return f"sess_{digest[:12]}"


def build_merchant_session_identity_v1(
    *,
    cookies: Optional[Mapping[str, str]] = None,
    dashboard_store_slug: str = "",
) -> dict[str, Any]:
    """
    Build merchant-facing identity for the Account Identity panel.

    ``dashboard_store_slug`` is the store the loaded dashboard claims
    (client passes summary.store_slug for consistency check).
    """
    ck = dict(cookies or {})
    raw = ck.get(merchant_cookie_name())
    mid = parse_merchant_session_cookie_value(raw)
    exp = _parse_cookie_exp(raw) or 0

    out: dict[str, Any] = {
        "ok": False,
        "authenticated": False,
        "merchant_name": "",
        "merchant_email": "",
        "merchant_id": None,
        "store_name": "",
        "store_slug": "",
        "commerce_provider": "—",
        "connection_status": "غير مصادق",
        "connection_status_key": "unauthenticated",
        "environment": "development" if is_development_env() else "production",
        "session_fingerprint": "",
        "last_sign_in_at": "",
        "last_sign_in_label_ar": "وقت بدء الجلسة الحالية",
        "review_label_ar": "هذا هو الحساب قيد المراجعة حالياً",
        "is_living_store_review": False,
        "consistency": {
            "ok": False,
            "status": "unauthenticated",
            "message_ar": "لا توجد جلسة تاجر صالحة.",
            "action_ar": "",
            "action_href": "",
        },
    }

    if not mid:
        return out

    user = get_merchant_user_by_id(int(mid))
    if user is None:
        out["consistency"]["message_ar"] = "تعذر التحقق من حساب التاجر."
        return out

    email = (getattr(user, "email", None) or "").strip().lower()
    merchant_name = (getattr(user, "merchant_name", None) or "").strip() or "—"
    store = get_primary_store_for_merchant(user)
    store_slug = (
        (getattr(store, "zid_store_id", None) or "").strip() if store is not None else ""
    )
    store_name = merchant_store_display_name(store, merchant_user=user)
    is_review = email == REVIEW_EMAIL.strip().lower() and store_slug == DEMO_STORE_SLUG

    conn = build_merchant_store_connection_status_for_store(
        store, store_name=store_name
    )
    connected = bool(conn.connected) or (
        is_review and store is not None
    )
    if is_review:
        provider = "Living Store"
        status_ar = "جلسة مراجعة نشطة"
        status_key = "living_store_review"
    elif connected:
        provider = (conn.platform_ar or "—").strip() or "—"
        status_ar = (conn.status_label_ar or "تم الربط").strip()
        status_key = "connected"
    else:
        provider = "—"
        status_ar = (conn.status_label_ar or "غير مربوط").strip()
        status_key = "disconnected"

    session_start = max(0, int(exp) - _TTL_S) if exp else 0
    fingerprint = (
        _session_fingerprint(
            merchant_id=int(mid), store_slug=store_slug or "-", exp=int(exp or 0)
        )
        if exp
        else ""
    )

    dash_slug = (dashboard_store_slug or "").strip()
    auth_ok = True
    store_ok = bool(store_slug)
    dash_ok = (not dash_slug) or (dash_slug == store_slug)
    # Shell default "demo" without auth store is a mismatch when authenticated elsewhere.
    if dash_slug and store_slug and dash_slug != store_slug:
        dash_ok = False

    if auth_ok and store_ok and dash_ok:
        consistency = {
            "ok": True,
            "status": "consistent",
            "message_ar": "✓ أنت تعرض نفس التاجر والمتجر عبر هذه الجلسة.",
            "action_ar": "",
            "action_href": "",
        }
    else:
        consistency = {
            "ok": False,
            "status": "mismatch",
            "message_ar": "✕ يوجد اختلاف في الجلسة. أعد التحميل عبر الحساب الصحيح.",
            "action_ar": "افتح حساب المراجعة الصحيح",
            "action_href": "/dev/living-store-home-review",
            "details": {
                "authenticated_store_slug": store_slug,
                "dashboard_store_slug": dash_slug,
                "merchant_id": int(mid),
            },
        }

    out.update(
        {
            "ok": True,
            "authenticated": True,
            "merchant_name": merchant_name,
            "merchant_email": email,
            "merchant_id": int(mid),
            "store_name": store_name,
            "store_slug": store_slug,
            "commerce_provider": provider,
            "connection_status": status_ar,
            "connection_status_key": status_key,
            "environment": "development" if is_development_env() else "production",
            "session_fingerprint": fingerprint,
            "last_sign_in_at": _fmt_utc(session_start) if session_start else "—",
            "is_living_store_review": is_review,
            "consistency": consistency,
            "platform_connected": bool(
                is_merchant_store_platform_connected(store)
            ),
        }
    )
    return out


__all__ = [
    "REVIEW_EMAIL",
    "build_merchant_session_identity_v1",
]
