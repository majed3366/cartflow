# -*- coding: utf-8 -*-
"""Admin-only Meta WhatsApp Cloud API hello_world template test send."""
from __future__ import annotations

from typing import Any, Optional

import requests

from services.admin_whatsapp_meta_status_v1 import (
    META_GRAPH_BASE,
    PLACEHOLDER_TOKENS,
    read_whatsapp_meta_env,
)

HELLO_WORLD_TEMPLATE = {
    "name": "hello_world",
    "language": {"code": "en_US"},
}


def normalize_whatsapp_to(phone: str) -> str:
    """E.164 digits only (no +), matching Graph API recipient format."""
    d = (phone or "").replace("+", "").replace(" ", "").replace("-", "")
    for ch in d:
        if ch.isdigit():
            continue
        return ""
    if len(d) < 8:
        return ""
    return d


def _safe_meta_error(body: Any, status_code: int) -> str:
    if isinstance(body, dict):
        err_obj = body.get("error")
        if isinstance(err_obj, dict):
            return str(
                err_obj.get("message") or err_obj.get("type") or "meta_api_error"
            )
        if body.get("error"):
            return str(body.get("error"))
    return f"meta_http_{status_code}"


def send_meta_whatsapp_test_message(
    to: str,
    *,
    session: Optional[requests.Session] = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Send hello_world template via Meta Cloud API.
    Never exposes access token in the returned dict.
    """
    recipient = normalize_whatsapp_to(to)
    if not recipient:
        return {
            "ok": False,
            "provider": "meta",
            "message_id": None,
            "error": "invalid_to",
        }

    env = read_whatsapp_meta_env()
    token = env.get("access_token") or ""
    phone_id = env.get("phone_number_id") or ""

    if not token or token.lower() in PLACEHOLDER_TOKENS:
        return {
            "ok": False,
            "provider": "meta",
            "message_id": None,
            "error": "access_token_missing",
        }
    if not phone_id or phone_id.lower() in PLACEHOLDER_TOKENS:
        return {
            "ok": False,
            "provider": "meta",
            "message_id": None,
            "error": "phone_number_id_missing",
        }

    url = f"{META_GRAPH_BASE}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": HELLO_WORLD_TEMPLATE,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    http = session or requests

    try:
        resp = http.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        return {
            "ok": False,
            "provider": "meta",
            "message_id": None,
            "error": f"http_error: {exc}",
        }

    try:
        body = resp.json()
    except ValueError:
        return {
            "ok": False,
            "provider": "meta",
            "message_id": None,
            "error": "invalid_json_response",
        }

    if resp.status_code != 200:
        return {
            "ok": False,
            "provider": "meta",
            "message_id": None,
            "error": _safe_meta_error(body, resp.status_code),
        }

    if isinstance(body, dict) and body.get("error"):
        return {
            "ok": False,
            "provider": "meta",
            "message_id": None,
            "error": _safe_meta_error(body, resp.status_code),
        }

    message_id = None
    if isinstance(body, dict):
        messages = body.get("messages")
        if isinstance(messages, list) and messages:
            first = messages[0]
            if isinstance(first, dict) and first.get("id"):
                message_id = str(first.get("id"))

    if not message_id:
        return {
            "ok": False,
            "provider": "meta",
            "message_id": None,
            "error": "message_id_missing_in_response",
        }

    return {
        "ok": True,
        "provider": "meta",
        "message_id": message_id,
        "error": None,
    }
