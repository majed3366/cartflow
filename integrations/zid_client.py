# -*- coding: utf-8 -*-
"""
Zid API client — ‎OAuth‎، الويبهوك، بيانات المتجر. لا تسجيل لرموز الدخول أو الأسرار.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple, TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from starlette.requests import Request as StarletteRequest
else:
    StarletteRequest = Any

ZID_OAUTH_BASE = (os.getenv("ZID_OAUTH_BASE") or "https://oauth.zid.sa").rstrip("/")
OAUTH_REDIRECT_URI = (os.getenv("OAUTH_REDIRECT_URI") or "").strip() or (
    "https://smartreplyai.net/auth/callback"
)
ZID_API_BASE = (os.getenv("ZID_API_BASE") or "https://api.zid.sa/v1").rstrip("/")
ZID_PROFILE_API = os.getenv(
    "ZID_PROFILE_API_URL", "https://api.zid.sa/v1/managers/account/profile"
)
ZID_OAUTH_TOKEN_URL = f"{ZID_OAUTH_BASE}/oauth/token"
ZID_OAUTH_AUTHORIZE_URL = f"{ZID_OAUTH_BASE}/oauth/authorize"


def parse_zid_store_id_from_token(data: dict[str, Any]) -> Optional[str]:
    for key in ("zid_store_id", "store_id", "merchant_id"):
        v = data.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    store = data.get("store")
    if isinstance(store, dict) and store.get("id") is not None:
        return str(store["id"]).strip()
    user = data.get("user")
    if isinstance(user, dict) and user.get("store_id") is not None:
        return str(user["store_id"]).strip()
    return None


def fetch_zid_store_id_from_profile(access_token: str) -> Optional[str]:
    auth_bearer = (os.getenv("ZID_API_AUTHORIZATION") or "").strip()
    h: dict[str, str] = {
        "X-MANAGER-TOKEN": access_token,
        "Accept": "application/json",
        "Accept-Language": "en",
    }
    if auth_bearer:
        h["Authorization"] = f"Bearer {auth_bearer}"
    try:
        r = requests.get(ZID_PROFILE_API, headers=h, timeout=20)
    except requests.RequestException:
        return None
    if r.status_code // 100 != 2:
        return None
    j = r.json()
    if not isinstance(j, dict):
        return None
    for path in (
        ("data", "store", "id"),
        ("data", "store_id"),
        ("store", "id"),
        ("user", "store", "id"),
    ):
        cur: Any = j
        for p in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(p)
        if cur is not None and str(cur).strip():
            return str(cur).strip()
    return None


def persist_oauth_tokens_on_store_row(
    row: Any,
    token_response: dict[str, Any],
) -> bool:
    """Write OAuth tokens onto an existing Store row (no latest-store fallback)."""
    access = (token_response.get("access_token") or "").strip()
    if not access:
        return False
    zid = parse_zid_store_id_from_token(token_response) or fetch_zid_store_id_from_profile(
        access
    )
    refresh: Optional[str] = None
    r = token_response.get("refresh_token")
    if r is not None and str(r).strip():
        refresh = str(r).strip()
    exp: Optional[datetime] = None
    ei = token_response.get("expires_in")
    if isinstance(ei, (int, float)):
        exp = datetime.now(timezone.utc) + timedelta(seconds=float(ei))
    if zid:
        row.zid_store_id = zid
    row.access_token = access
    if refresh is not None:
        row.refresh_token = refresh
    row.token_expires_at = exp
    row.is_active = True
    try:
        attempts = int(getattr(row, "recovery_attempts", 0) or 0)
    except (TypeError, ValueError):
        attempts = 0
    if attempts < 1:
        row.recovery_attempts = 1
    return True


def zid_oauth_configured() -> bool:
    return bool((os.getenv("ZID_CLIENT_ID") or "").strip()) and bool(
        (os.getenv("ZID_CLIENT_SECRET") or "").strip()
    )


def build_zid_authorize_url(*, state: str = "") -> Tuple[Optional[str], Optional[dict]]:
    """
    Build Zid OAuth authorize redirect URL.
    Returns (url, error_payload) — error_payload when OAuth env is missing.
    """
    client_id = (os.getenv("ZID_CLIENT_ID") or "").strip()
    if not zid_oauth_configured():
        missing: list[str] = []
        if not client_id:
            missing.append("ZID_CLIENT_ID")
        if not (os.getenv("ZID_CLIENT_SECRET") or "").strip():
            missing.append("ZID_CLIENT_SECRET")
        return (
            None,
            {
                "error": "oauth_not_configured",
                "message_ar": "ميزة الربط قيد الإعداد",
                "missing_environment_variables": missing,
            },
        )
    from urllib.parse import urlencode

    q: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
    }
    st = (state or "").strip()
    if st:
        q["state"] = st
    return f"{ZID_OAUTH_AUTHORIZE_URL}?{urlencode(q)}", None


def exchange_code_for_token(code: str) -> Tuple[dict, int]:
    client_id = (os.getenv("ZID_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("ZID_CLIENT_SECRET") or "").strip()
    missing: list[str] = []
    if not client_id:
        missing.append("ZID_CLIENT_ID")
    if not client_secret:
        missing.append("ZID_CLIENT_SECRET")
    if missing:
        return (
            {
                "error": "OAuth is not configured: set the following in the server environment",
                "missing_environment_variables": missing,
            },
            500,
        )
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "code": code,
    }
    try:
        tr = requests.post(
            ZID_OAUTH_TOKEN_URL,
            data=payload,
            timeout=30,
        )
    except requests.RequestException as e:
        return (
            {
                "error": "Failed to reach Zid OAuth token endpoint",
                "detail": str(e),
            },
            502,
        )
    try:
        body: Any = tr.json()
    except Exception:
        return (
            {
                "error": "Zid returned a non-JSON response",
                "http_status": tr.status_code,
                "raw": (tr.text or "")[:4000],
            },
            tr.status_code,
        )
    if isinstance(body, dict):
        return (body, tr.status_code)
    return ({"response": body}, tr.status_code)


def _manager_headers(store_token: str) -> dict[str, str]:
    h: dict[str, str] = {
        "X-MANAGER-TOKEN": store_token,
        "Accept": "application/json",
        "Accept-Language": "en",
    }
    auth = (os.getenv("ZID_API_AUTHORIZATION") or "").strip()
    if auth:
        h["Authorization"] = f"Bearer {auth}"
    return h


def fetch_abandoned_carts(store: Any) -> Tuple[dict, int]:
    token = (getattr(store, "access_token", None) or "").strip()
    if not token:
        return ({"error": "store has no access token"}, 400)
    url = f"{ZID_API_BASE}/managers/store/abandoned-carts"
    try:
        r = requests.get(
            url,
            params={"page": 1, "page_size": 20},
            headers=_manager_headers(token),
            timeout=30,
        )
    except requests.RequestException as e:
        return ({"error": "request_failed", "detail": str(e)}, 502)
    try:
        body: Any = r.json()
    except Exception:
        return ({"raw": (r.text or "")[:2000], "http_status": r.status_code}, r.status_code)
    if isinstance(body, dict):
        return (body, r.status_code)
    return ({"data": body}, r.status_code)


def fetch_orders(store: Any) -> Tuple[dict, int]:
    token = (getattr(store, "access_token", None) or "").strip()
    if not token:
        return ({"error": "store has no access token"}, 400)
    url = f"{ZID_API_BASE}/managers/store/orders"
    try:
        r = requests.get(
            url,
            params={"page": 1, "page_size": 20},
            headers=_manager_headers(token),
            timeout=30,
        )
    except requests.RequestException as e:
        return ({"error": "request_failed", "detail": str(e)}, 502)
    try:
        body: Any = r.json()
    except Exception:
        return ({"raw": (r.text or "")[:2000], "http_status": r.status_code}, r.status_code)
    if isinstance(body, dict):
        return (body, r.status_code)
    return ({"data": body}, r.status_code)


def verify_webhook_signature(
    req: "StarletteRequest", raw_body: Optional[bytes] = None
) -> bool:
    if raw_body is not None:
        body = raw_body
    else:
        return False
    header_sig: Optional[str] = req.headers.get("X-Zid-Signature")
    secret = (os.getenv("ZID_WEBHOOK_SECRET") or "").strip()
    if not secret or not body or not (header_sig or "").strip():
        return False
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256)
    hexd = mac.hexdigest()
    b64d = base64.b64encode(mac.digest()).decode("ascii")
    s = header_sig.strip()
    if s.lower().startswith("sha256="):
        s = s[7:].strip()
    if hmac.compare_digest(hexd, s) or hmac.compare_digest(b64d, s):
        return True
    return False
