# -*- coding: utf-8 -*-
"""Meta Cloud API WhatsApp provider (template / session_text). Never logs secrets."""
from __future__ import annotations

import logging
from typing import Any, Optional

import requests

from services.admin_whatsapp_meta_status_v1 import (
    META_GRAPH_BASE,
    PLACEHOLDER_TOKENS,
    read_whatsapp_meta_env,
)
from services.whatsapp_providers.contracts import (
    MODE_SESSION_TEXT,
    MODE_TEMPLATE,
    PROVIDER_META,
    WhatsAppProviderRequest,
    WhatsAppProviderResult,
    empty_provider_result,
)

logger = logging.getLogger(__name__)

# Graph version is governed by admin Meta status module (v23.0).
META_PROVIDER_GRAPH_BASE = META_GRAPH_BASE

_RETRYABLE_META_CODES = frozenset(
    {
        "1",  # API Unknown / temporary
        "2",  # API Service
        "4",  # API Too Many Calls
        "17",  # API User Too Many Calls
        "80007",  # rate limit-ish
    }
)


def normalize_meta_recipient(phone: str) -> str:
    """E.164 digits only (no +), matching Graph API recipient format."""
    d = (phone or "").replace("+", "").replace(" ", "").replace("-", "")
    if not d or not d.isdigit() or len(d) < 8:
        return ""
    return d


def build_meta_template_payload(
    *,
    to_digits: str,
    template_name: str,
    template_language: str,
    template_parameters: list[str],
    template_button_url_param: Optional[str] = None,
    quick_reply_payload: Optional[str] = None,
) -> dict[str, Any]:
    """Construct Meta template message body (no secrets)."""
    template: dict[str, Any] = {
        "name": template_name,
        "language": {"code": template_language},
    }
    components: list[dict[str, Any]] = []
    params = [str(p) for p in (template_parameters or []) if str(p).strip() != ""]
    if params:
        components.append(
            {
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in params],
            }
        )
    url_param = (template_button_url_param or "").strip()
    if url_param:
        # Button index 0 = URL (إكمال الشراء) on approved contract
        components.append(
            {
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [{"type": "text", "text": url_param}],
            }
        )
    qr_payload = (quick_reply_payload or "").strip()
    if qr_payload:
        # Button index 1 = QUICK_REPLY (خدمة العملاء)
        components.append(
            {
                "type": "button",
                "sub_type": "quick_reply",
                "index": "1",
                "parameters": [{"type": "payload", "payload": qr_payload}],
            }
        )
    if components:
        template["components"] = components
    return {
        "messaging_product": "whatsapp",
        "to": to_digits,
        "type": "template",
        "template": template,
    }


def build_meta_session_text_payload(*, to_digits: str, body_text: str) -> dict[str, Any]:
    return {
        "messaging_product": "whatsapp",
        "to": to_digits,
        "type": "text",
        "text": {"preview_url": False, "body": body_text},
    }


def _safe_meta_error_fields(
    body: Any, status_code: int
) -> tuple[Optional[str], Optional[str], str, bool, Optional[str]]:
    """
    Return (error_code, error_subcode, safe_message, retryable, fbtrace_id).

    Never includes tokens / Authorization.
    """
    if isinstance(body, dict):
        err_obj = body.get("error")
        if isinstance(err_obj, dict):
            code = err_obj.get("code")
            sub = err_obj.get("error_subcode")
            code_s = str(code) if code is not None else None
            sub_s = str(sub) if sub is not None else None
            msg = str(err_obj.get("message") or err_obj.get("type") or "meta_api_error")
            # Strip anything that looks like a token fragment
            if "access token" in msg.lower() or "oauth" in msg.lower():
                msg = "meta_auth_or_token_error"
            retryable = bool(code_s and code_s in _RETRYABLE_META_CODES)
            if status_code in (429, 500, 502, 503, 504):
                retryable = True
            trace_raw = err_obj.get("fbtrace_id")
            trace_s = None
            if trace_raw is not None:
                t = str(trace_raw).strip()
                # fbtrace_id is opaque alphanumeric — keep short, never headers
                if t and len(t) <= 128 and all(c.isalnum() or c in "-_" for c in t):
                    trace_s = t
            return code_s, sub_s, msg[:300], retryable, trace_s
    return (
        str(status_code),
        None,
        f"meta_http_{status_code}",
        status_code in (429, 500, 502, 503, 504),
        None,
    )


def _extract_message_id(body: Any) -> Optional[str]:
    if not isinstance(body, dict):
        return None
    messages = body.get("messages")
    if isinstance(messages, list) and messages:
        first = messages[0]
        if isinstance(first, dict) and first.get("id"):
            return str(first.get("id"))
    return None


def send_via_meta(
    req: WhatsAppProviderRequest,
    *,
    session: Optional[requests.Session] = None,
    timeout: Optional[float] = None,
) -> dict[str, Any]:
    """
    Send via Meta Graph Cloud API.

    Template mode is the recovery default. session_text must be pre-authorized
    by the provider boundary (proven 24h window) — this function does not invent window truth.
    """
    mode = (req.message_mode or MODE_TEMPLATE).strip().lower()
    if mode not in (MODE_TEMPLATE, MODE_SESSION_TEXT):
        return empty_provider_result(
            PROVIDER_META,
            error_code="unsupported_message_mode",
            error_message_safe=f"unsupported_message_mode:{mode}",
            message_mode=mode,
        ).to_legacy_wa_dict()

    env = read_whatsapp_meta_env()
    token = env.get("access_token") or ""
    phone_id = env.get("phone_number_id") or ""

    if not token or token.lower() in PLACEHOLDER_TOKENS:
        return empty_provider_result(
            PROVIDER_META,
            error_code="meta_access_token_missing",
            error_message_safe="meta_access_token_missing",
            message_mode=mode,
        ).to_legacy_wa_dict()
    if not phone_id or phone_id.lower() in PLACEHOLDER_TOKENS:
        return empty_provider_result(
            PROVIDER_META,
            error_code="meta_phone_number_id_missing",
            error_message_safe="meta_phone_number_id_missing",
            message_mode=mode,
        ).to_legacy_wa_dict()

    to_digits = normalize_meta_recipient(req.to_phone)
    if not to_digits:
        return empty_provider_result(
            PROVIDER_META,
            error_code="invalid_phone",
            error_message_safe="invalid_phone",
            message_mode=mode,
        ).to_legacy_wa_dict()

    if mode == MODE_TEMPLATE:
        name = (req.template_name or "").strip()
        lang = (req.template_language or "").strip() or "ar"
        if not name:
            return empty_provider_result(
                PROVIDER_META,
                error_code="meta_template_name_missing",
                error_message_safe="meta_template_name_missing",
                message_mode=mode,
            ).to_legacy_wa_dict()
        from services.meta_recovery_template_contract_v1 import (  # noqa: PLC0415
            BUTTON_QUICK_REPLY_PAYLOAD,
            TEMPLATE_NAME as RECOVERY_TPL,
            encode_checkout_url_button_param,
        )

        url_param = (req.template_button_url_param or "").strip() or None
        if not url_param and (req.checkout_url or "").strip():
            url_param = encode_checkout_url_button_param(str(req.checkout_url))
        qr_payload = None
        if name == RECOVERY_TPL:
            qr_payload = BUTTON_QUICK_REPLY_PAYLOAD
        payload = build_meta_template_payload(
            to_digits=to_digits,
            template_name=name,
            template_language=lang,
            template_parameters=list(req.template_parameters or []),
            template_button_url_param=url_param,
            quick_reply_payload=qr_payload,
        )
    else:
        body = (req.body_text or "").strip()
        if not body:
            return empty_provider_result(
                PROVIDER_META,
                error_code="empty_message",
                error_message_safe="empty_message",
                message_mode=mode,
            ).to_legacy_wa_dict()
        payload = build_meta_session_text_payload(to_digits=to_digits, body_text=body)

    if timeout is None:
        try:
            from services.provider_send_timeout_v1 import provider_send_timeout_seconds

            timeout = float(provider_send_timeout_seconds())
        except Exception:  # noqa: BLE001
            timeout = 30.0

    url = f"{META_PROVIDER_GRAPH_BASE}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    http = session or requests

    try:
        resp = http.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.Timeout:
        return empty_provider_result(
            PROVIDER_META,
            error_code="provider_timeout",
            error_message_safe="provider_timeout",
            retryable=True,
            message_mode=mode,
        ).to_legacy_wa_dict()
    except requests.RequestException as exc:
        # Never include request headers/token in the safe message
        return empty_provider_result(
            PROVIDER_META,
            error_code="http_error",
            error_message_safe=f"http_error:{type(exc).__name__}",
            retryable=True,
            message_mode=mode,
        ).to_legacy_wa_dict()

    try:
        body = resp.json()
    except ValueError:
        return empty_provider_result(
            PROVIDER_META,
            error_code="invalid_json_response",
            error_message_safe="invalid_json_response",
            message_mode=mode,
        ).to_legacy_wa_dict()

    if resp.status_code != 200 or (isinstance(body, dict) and body.get("error")):
        code, sub, msg, retryable, trace_id = _safe_meta_error_fields(
            body, resp.status_code
        )
        return empty_provider_result(
            PROVIDER_META,
            error_code=code or "meta_api_error",
            error_subcode=sub,
            error_message_safe=msg,
            error_trace_id=trace_id,
            retryable=retryable,
            message_mode=mode,
            provider_status=f"http_{int(resp.status_code)}",
        ).to_legacy_wa_dict()

    message_id = _extract_message_id(body)
    if not message_id:
        return empty_provider_result(
            PROVIDER_META,
            error_code="message_id_missing_in_response",
            error_message_safe="message_id_missing_in_response",
            message_mode=mode,
        ).to_legacy_wa_dict()

    result = WhatsAppProviderResult(
        provider=PROVIDER_META,
        accepted=True,
        external_message_id=message_id,
        provider_status="accepted",
        error_code=None,
        error_subcode=None,
        error_message_safe=None,
        retryable=False,
        raw_payload_stored=False,
        message_mode=mode,
    )
    return result.to_legacy_wa_dict()
