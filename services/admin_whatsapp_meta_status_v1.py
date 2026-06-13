# -*- coding: utf-8 -*-
"""Live Meta Graph API verification for platform WhatsApp credentials (admin only)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

import requests

META_GRAPH_VERSION = "v23.0"
META_GRAPH_BASE = f"https://graph.facebook.com/{META_GRAPH_VERSION}"
PLACEHOLDER_TOKENS = frozenset({"your_token", "your_id", "changeme", "placeholder"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_whatsapp_meta_env() -> dict[str, str]:
    """Read platform WhatsApp env vars (never returns secrets)."""
    token = (
        (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip()
        or (os.getenv("WHATSAPP_API_TOKEN") or "").strip()
        or (os.getenv("WHATSAPP_CLOUD_API_TOKEN") or "").strip()
        or (os.getenv("META_WHATSAPP_TOKEN") or "").strip()
    )
    phone_id = (
        (os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
        or (os.getenv("WHATSAPP_PHONE_ID") or "").strip()
    )
    waba_id = (
        (os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID") or "").strip()
        or (os.getenv("WABA_ID") or "").strip()
    )
    return {
        "access_token": token,
        "phone_number_id": phone_id,
        "waba_id": waba_id,
    }


def _empty_status(env: dict[str, str]) -> dict[str, Any]:
    return {
        "connected": False,
        "phone_number_id": env.get("phone_number_id") or None,
        "verified_name": None,
        "display_phone_number": None,
        "waba_id": env.get("waba_id") or None,
        "meta_response_ok": False,
        "error": None,
        "verified_at": _utc_now_iso(),
    }


def fetch_whatsapp_meta_status(
    *,
    session: Optional[requests.Session] = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """
    Call Meta Graph API for the configured phone number id.
    Never exposes the access token in the returned dict.
    """
    env = read_whatsapp_meta_env()
    out = _empty_status(env)
    token = env.get("access_token") or ""
    phone_id = env.get("phone_number_id") or ""

    if not token or token.lower() in PLACEHOLDER_TOKENS:
        out["error"] = "access_token_missing"
        return out
    if not phone_id or phone_id.lower() in PLACEHOLDER_TOKENS:
        out["error"] = "phone_number_id_missing"
        return out

    url = f"{META_GRAPH_BASE}/{phone_id}"
    params = {"fields": "verified_name,display_phone_number,id"}
    headers = {"Authorization": f"Bearer {token}"}
    http = session or requests

    try:
        resp = http.get(url, params=params, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        out["error"] = f"http_error: {exc}"
        return out

    try:
        body = resp.json()
    except ValueError:
        out["error"] = "invalid_json_response"
        return out

    if resp.status_code != 200:
        err_obj = body.get("error") if isinstance(body, dict) else None
        if isinstance(err_obj, dict):
            out["error"] = str(err_obj.get("message") or err_obj.get("type") or "meta_http_error")
        else:
            out["error"] = f"meta_http_{resp.status_code}"
        return out

    if isinstance(body, dict) and body.get("error"):
        err_obj = body.get("error")
        if isinstance(err_obj, dict):
            out["error"] = str(err_obj.get("message") or err_obj.get("type") or "meta_api_error")
        else:
            out["error"] = "meta_api_error"
        return out

    out["meta_response_ok"] = True
    out["verified_name"] = body.get("verified_name") if isinstance(body, dict) else None
    out["display_phone_number"] = (
        body.get("display_phone_number") if isinstance(body, dict) else None
    )
    api_id = body.get("id") if isinstance(body, dict) else None
    if api_id:
        out["phone_number_id"] = str(api_id)
    out["connected"] = out["meta_response_ok"] is True
    out["error"] = None
    return out
