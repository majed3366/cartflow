# -*- coding: utf-8 -*-
"""
Zid API client — ‎OAuth‎، الويبهوك، بيانات المتجر. لا تسجيل لرموز الدخول أو الأسرار.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
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
ZID_OAUTH_TOKEN_URL = f"{ZID_OAUTH_BASE}/oauth/token"


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
