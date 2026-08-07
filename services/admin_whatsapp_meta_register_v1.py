# -*- coding: utf-8 -*-
"""Admin-only Meta Cloud API phone registration (no message send)."""
from __future__ import annotations

from typing import Any, Optional

import requests

from services.admin_whatsapp_meta_status_v1 import (
    META_GRAPH_BASE,
    PLACEHOLDER_TOKENS,
    _utc_now_iso,
    fetch_whatsapp_meta_status,
    read_whatsapp_meta_env,
)

ALLOWED_REGISTER_PHONE_IDS = frozenset({"1260388737156321"})


def _safe_meta_error(body: Any, status_code: int) -> dict[str, Any]:
    err: dict[str, Any] = {
        "http_status": status_code,
        "error_code": None,
        "error_subcode": None,
        "error_message_safe": f"meta_http_{status_code}",
        "error_type": None,
        "fbtrace_id": None,
    }
    if not isinstance(body, dict):
        return err
    obj = body.get("error")
    if not isinstance(obj, dict):
        return err
    msg = str(obj.get("message") or obj.get("type") or "meta_api_error")
    if "access token" in msg.lower() or "oauth" in msg.lower():
        msg = "meta_auth_or_token_error"
    err["error_code"] = obj.get("code")
    err["error_subcode"] = obj.get("error_subcode")
    err["error_message_safe"] = msg[:300]
    err["error_type"] = obj.get("type")
    err["fbtrace_id"] = obj.get("fbtrace_id")
    return err


def register_whatsapp_phone(
    *,
    phone_number_id: str,
    pin: str,
    session: Optional[requests.Session] = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    POST /{PHONE_NUMBER_ID}/register for an allowlisted production phone.
    Never returns or echoes the PIN.
    """
    phone_id = (phone_number_id or "").strip()
    pin_digits = "".join(ch for ch in str(pin or "") if ch.isdigit())
    out: dict[str, Any] = {
        "ok": False,
        "operation": "register",
        "phone_number_id": phone_id or None,
        "registration_response": None,
        "after_status": None,
        "http_status": None,
        "error_code": None,
        "error_subcode": None,
        "error_message_safe": None,
        "fbtrace_id": None,
        "verified_at": _utc_now_iso(),
    }

    if phone_id not in ALLOWED_REGISTER_PHONE_IDS:
        out["error_message_safe"] = "phone_number_id_not_allowlisted"
        return out
    if len(pin_digits) != 6:
        out["error_message_safe"] = "pin_must_be_6_digits"
        return out

    env = read_whatsapp_meta_env()
    token = (env.get("access_token") or "").strip()
    if not token or token.lower() in PLACEHOLDER_TOKENS:
        out["error_message_safe"] = "access_token_missing"
        return out

    url = f"{META_GRAPH_BASE}/{phone_id}/register"
    payload = {"messaging_product": "whatsapp", "pin": pin_digits}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    http = session or requests

    try:
        resp = http.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        out["error_message_safe"] = f"http_error: {exc}"
        return out

    try:
        body = resp.json()
    except ValueError:
        out["http_status"] = resp.status_code
        out["error_message_safe"] = "invalid_json_response"
        return out

    out["http_status"] = resp.status_code

    if resp.status_code != 200 or (isinstance(body, dict) and body.get("error")):
        err = _safe_meta_error(body, resp.status_code)
        out.update(err)
        out["registration_response"] = {
            "success": False,
            **{k: err[k] for k in ("http_status", "error_code", "error_subcode", "error_message_safe", "fbtrace_id")},
        }
        return out

    success = bool(isinstance(body, dict) and body.get("success") is True)
    out["registration_response"] = {"success": success}
    out["ok"] = success

    # Immediate post-register verify (explicit phone id; no env mutation).
    after = fetch_whatsapp_meta_status(
        session=session,
        phone_number_id=phone_id,
        timeout=timeout,
    )
    out["after_status"] = {
        "phone_number_id": after.get("phone_number_id"),
        "display_phone_number": after.get("display_phone_number"),
        "verified_name": after.get("verified_name"),
        "registration_status": after.get("registration_status"),
        "platform_type": after.get("platform_type"),
        "is_pin_enabled": after.get("is_pin_enabled"),
        "code_verification_status": after.get("code_verification_status"),
        "name_status": after.get("name_status"),
        "cloud_api_registered": after.get("cloud_api_registered"),
        "health_can_send_message": None,
        "meta_response_ok": after.get("meta_response_ok"),
        "error": after.get("error"),
    }
    extras = after.get("diagnostic_extras") if isinstance(after.get("diagnostic_extras"), dict) else {}
    health = extras.get("health_status") if isinstance(extras, dict) else None
    if isinstance(health, dict):
        out["after_status"]["health_can_send_message"] = health.get("can_send_message")
        out["after_status"]["health_status"] = health

    return out
