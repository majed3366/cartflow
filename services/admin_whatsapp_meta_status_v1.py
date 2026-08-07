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

# Registration / eligibility fields for Cloud API verify (never secrets).
PHONE_STATUS_FIELDS = (
    "id,"
    "verified_name,"
    "display_phone_number,"
    "quality_rating,"
    "code_verification_status,"
    "name_status,"
    "new_name_status,"
    "status,"
    "platform_type,"
    "messaging_limit_tier,"
    "account_mode,"
    "last_onboarded_time,"
    "is_official_business_account,"
    "is_pin_enabled,"
    "throughput,"
    "webhook_configuration"
)

# Extra diagnostic fields requested one-by-one if core GET succeeds (unknown → omitted).
PHONE_DIAGNOSTIC_EXTRA_FIELDS = (
    "health_status",
    "eligibility_status",
    "onboarding_status",
    "display_name_status",
    "certificate",
    "certificate_status",
    "registration_state",
    "pending_reason",
    "search_visibility",
)


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
        "registration_status": None,
        "quality_rating": None,
        "code_verification_status": None,
        "name_status": None,
        "new_name_status": None,
        "platform_type": None,
        "messaging_limit_tier": None,
        "account_mode": None,
        "last_onboarded_time": None,
        "is_official_business_account": None,
        "is_pin_enabled": None,
        "throughput": None,
        "webhook_configuration": None,
        "diagnostic_extras": {},
        "diagnostic_unavailable_fields": [],
        "cloud_api_registered": False,
        "meta_response_ok": False,
        "error": None,
        "verified_at": _utc_now_iso(),
    }


def _graph_get_json(
    *,
    url: str,
    token: str,
    fields: str,
    session: Optional[requests.Session],
    timeout: float,
) -> tuple[Optional[int], Any, Optional[str]]:
    headers = {"Authorization": f"Bearer {token}"}
    http = session or requests
    try:
        resp = http.get(url, params={"fields": fields}, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        return None, None, f"http_error: {exc}"
    try:
        body = resp.json()
    except ValueError:
        return resp.status_code, None, "invalid_json_response"
    return resp.status_code, body, None


def fetch_whatsapp_meta_status(
    *,
    session: Optional[requests.Session] = None,
    timeout: float = 20.0,
    phone_number_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Call Meta Graph API for the configured phone number id (or an explicit override).
    Never exposes the access token in the returned dict.
    """
    env = read_whatsapp_meta_env()
    out = _empty_status(env)
    token = env.get("access_token") or ""
    phone_id = (phone_number_id or env.get("phone_number_id") or "").strip()
    if phone_number_id:
        out["phone_number_id"] = phone_id or None

    if not token or token.lower() in PLACEHOLDER_TOKENS:
        out["error"] = "access_token_missing"
        return out
    if not phone_id or phone_id.lower() in PLACEHOLDER_TOKENS:
        out["error"] = "phone_number_id_missing"
        return out

    url = f"{META_GRAPH_BASE}/{phone_id}"
    status_code, body, transport_err = _graph_get_json(
        url=url,
        token=token,
        fields=PHONE_STATUS_FIELDS,
        session=session,
        timeout=timeout,
    )
    if transport_err:
        out["error"] = transport_err
        return out
    assert body is not None

    if status_code != 200:
        err_obj = body.get("error") if isinstance(body, dict) else None
        if isinstance(err_obj, dict):
            out["error"] = str(err_obj.get("message") or err_obj.get("type") or "meta_http_error")
            out["error_code"] = err_obj.get("code")
            out["error_subcode"] = err_obj.get("error_subcode")
            out["error_type"] = err_obj.get("type")
            out["fbtrace_id"] = err_obj.get("fbtrace_id")
        else:
            out["error"] = f"meta_http_{status_code}"
        return out

    if isinstance(body, dict) and body.get("error"):
        err_obj = body.get("error")
        if isinstance(err_obj, dict):
            out["error"] = str(err_obj.get("message") or err_obj.get("type") or "meta_api_error")
            out["error_code"] = err_obj.get("code")
            out["error_subcode"] = err_obj.get("error_subcode")
            out["error_type"] = err_obj.get("type")
            out["fbtrace_id"] = err_obj.get("fbtrace_id")
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

    status_raw = body.get("status") if isinstance(body, dict) else None
    out["registration_status"] = str(status_raw) if status_raw is not None else None
    out["quality_rating"] = body.get("quality_rating") if isinstance(body, dict) else None
    out["code_verification_status"] = (
        body.get("code_verification_status") if isinstance(body, dict) else None
    )
    out["name_status"] = body.get("name_status") if isinstance(body, dict) else None
    out["new_name_status"] = body.get("new_name_status") if isinstance(body, dict) else None
    out["platform_type"] = body.get("platform_type") if isinstance(body, dict) else None
    out["messaging_limit_tier"] = (
        body.get("messaging_limit_tier") if isinstance(body, dict) else None
    )
    out["account_mode"] = body.get("account_mode") if isinstance(body, dict) else None
    out["last_onboarded_time"] = (
        body.get("last_onboarded_time") if isinstance(body, dict) else None
    )
    out["is_official_business_account"] = (
        body.get("is_official_business_account") if isinstance(body, dict) else None
    )
    out["is_pin_enabled"] = body.get("is_pin_enabled") if isinstance(body, dict) else None
    out["throughput"] = body.get("throughput") if isinstance(body, dict) else None
    out["webhook_configuration"] = (
        body.get("webhook_configuration") if isinstance(body, dict) else None
    )

    extras: dict[str, Any] = {}
    unavailable: list[str] = []
    for field in PHONE_DIAGNOSTIC_EXTRA_FIELDS:
        sc, extra_body, extra_err = _graph_get_json(
            url=url,
            token=token,
            fields=field,
            session=session,
            timeout=timeout,
        )
        if extra_err or sc != 200 or not isinstance(extra_body, dict) or extra_body.get("error"):
            unavailable.append(field)
            continue
        if field in extra_body:
            extras[field] = extra_body.get(field)
        else:
            unavailable.append(field)
    out["diagnostic_extras"] = extras
    out["diagnostic_unavailable_fields"] = unavailable

    status_norm = (out["registration_status"] or "").strip().upper()
    out["cloud_api_registered"] = status_norm == "CONNECTED"
    # Legacy admin card: Graph reachable. Prefer CONNECTED when status present.
    out["connected"] = out["cloud_api_registered"] if status_norm else True
    out["error"] = None
    return out


WABA_PHONE_LIST_FIELDS = (
    "id,display_phone_number,verified_name,status,platform_type,quality_rating"
)


def _normalize_phone_digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def fetch_waba_phone_numbers(
    *,
    session: Optional[requests.Session] = None,
    timeout: float = 20.0,
    waba_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Enumerate WhatsApp Business phone numbers on the configured (or given) WABA.
    Never exposes the access token.
    """
    env = read_whatsapp_meta_env()
    token = env.get("access_token") or ""
    resolved_waba = (waba_id or env.get("waba_id") or "").strip()
    out: dict[str, Any] = {
        "waba_id": resolved_waba or None,
        "phones": [],
        "meta_response_ok": False,
        "error": None,
        "verified_at": _utc_now_iso(),
    }

    if not token or token.lower() in PLACEHOLDER_TOKENS:
        out["error"] = "access_token_missing"
        return out
    if not resolved_waba or resolved_waba.lower() in PLACEHOLDER_TOKENS:
        out["error"] = "waba_id_missing"
        return out

    url = f"{META_GRAPH_BASE}/{resolved_waba}/phone_numbers"
    params = {"fields": WABA_PHONE_LIST_FIELDS}
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

    rows = body.get("data") if isinstance(body, dict) else None
    phones: list[dict[str, Any]] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            status_raw = row.get("status")
            phones.append(
                {
                    "phone_number_id": str(row["id"]) if row.get("id") is not None else None,
                    "display_phone_number": row.get("display_phone_number"),
                    "verified_name": row.get("verified_name"),
                    "registration_status": str(status_raw) if status_raw is not None else None,
                    "platform_type": row.get("platform_type"),
                    "quality_rating": row.get("quality_rating"),
                }
            )

    out["phones"] = phones
    out["meta_response_ok"] = True
    out["error"] = None
    return out


def find_phone_by_display_digits(
    phones: list[dict[str, Any]],
    target_digits: str,
) -> Optional[dict[str, Any]]:
    """Match a phone row by digit-only display number (ignores spaces/dashes)."""
    want = _normalize_phone_digits(target_digits)
    if not want:
        return None
    for row in phones:
        got = _normalize_phone_digits(row.get("display_phone_number"))
        if got == want or got.endswith(want) or want.endswith(got):
            return row
    return None
