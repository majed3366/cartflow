# -*- coding: utf-8 -*-
"""
Admin-only WhatsApp Embedded Signup recovery (Phase 2B).

Re-authorize EXISTING CartFlow WABA + phone via Meta ES.
Does NOT register, delete, create, or deregister Meta assets.
Never logs or returns access tokens / app secrets.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from services.admin_whatsapp_meta_status_v1 import META_GRAPH_VERSION

logger = logging.getLogger(__name__)

# Hard targets — abort if ES returns anything else.
TARGET_WABA_ID = "1520530422625766"
TARGET_PHONE_NUMBER_ID = "1260388737156321"

FB_SDK_VERSION = "v21.0"
RECOVERY_MARKER = "whatsapp-es-recovery-v1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_first(*keys: str) -> str:
    for key in keys:
        val = (os.getenv(key) or "").strip()
        if val:
            return val
    return ""


def read_embedded_signup_env() -> dict[str, Any]:
    """Read ES env. Secret is never returned."""
    app_id = _env_first("META_WHATSAPP_APP_ID", "WHATSAPP_APP_ID", "META_APP_ID")
    configuration_id = _env_first(
        "META_WHATSAPP_CONFIGURATION_ID",
        "META_WHATSAPP_CONFIG_ID",
        "WHATSAPP_CONFIGURATION_ID",
    )
    secret_present = bool(
        _env_first("META_WHATSAPP_APP_SECRET", "META_APP_SECRET", "FACEBOOK_APP_SECRET")
    )
    return {
        "app_id": app_id,
        "configuration_id": configuration_id,
        "app_secret_configured": secret_present,
        "graph_version": META_GRAPH_VERSION,
        "fb_sdk_version": FB_SDK_VERSION,
        "target_waba_id": TARGET_WABA_ID,
        "target_phone_number_id": TARGET_PHONE_NUMBER_ID,
        "recovery_marker": RECOVERY_MARKER,
    }


def _app_secret() -> str:
    return _env_first("META_WHATSAPP_APP_SECRET", "META_APP_SECRET", "FACEBOOK_APP_SECRET")


def public_recovery_config() -> dict[str, Any]:
    """Admin bootstrap payload — never includes secrets."""
    env = read_embedded_signup_env()
    ready = bool(
        env["app_id"] and env["configuration_id"] and env["app_secret_configured"]
    )
    return {
        "ok": True,
        "ready": ready,
        "app_id": env["app_id"] or None,
        "configuration_id": env["configuration_id"] or None,
        "app_secret_configured": env["app_secret_configured"],
        "graph_version": env["graph_version"],
        "fb_sdk_version": env["fb_sdk_version"],
        "target_waba_id": TARGET_WABA_ID,
        "target_phone_number_id": TARGET_PHONE_NUMBER_ID,
        "register_allowed": False,
        "recovery_marker": RECOVERY_MARKER,
        "phase": "2b_embedded_signup_recovery",
        "stop_before_register": True,
    }


def assert_existing_assets(
    *,
    waba_id: str,
    phone_number_id: str,
) -> dict[str, Any]:
    """HARD ASSERT existing assets. Abort on any mismatch."""
    waba = (waba_id or "").strip()
    phone = (phone_number_id or "").strip()
    waba_ok = waba == TARGET_WABA_ID
    phone_ok = phone == TARGET_PHONE_NUMBER_ID
    if waba_ok and phone_ok:
        return {
            "ok": True,
            "aborted": False,
            "waba_id": waba,
            "phone_number_id": phone,
            "waba_match": True,
            "phone_match": True,
            "reason": None,
        }
    reason_parts = []
    if not waba_ok:
        reason_parts.append(
            f"waba_mismatch: got={waba or 'missing'} expected={TARGET_WABA_ID}"
        )
    if not phone_ok:
        reason_parts.append(
            f"phone_mismatch: got={phone or 'missing'} expected={TARGET_PHONE_NUMBER_ID}"
        )
    return {
        "ok": False,
        "aborted": True,
        "waba_id": waba or None,
        "phone_number_id": phone or None,
        "waba_match": waba_ok,
        "phone_match": phone_ok,
        "reason": "; ".join(reason_parts),
        "action": "ABORT — do not exchange further, do not register, do not create assets",
    }


def exchange_authorization_code(code: str) -> dict[str, Any]:
    """
    Server-side code → token exchange.
    Returns metadata only — never the access_token value.
    """
    code_s = (code or "").strip()
    if not code_s:
        return {"ok": False, "error": "missing_authorization_code", "token_obtained": False}

    env = read_embedded_signup_env()
    app_id = env["app_id"]
    secret = _app_secret()
    if not app_id or not secret:
        return {
            "ok": False,
            "error": "missing_app_id_or_secret",
            "token_obtained": False,
        }

    url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/oauth/access_token"
    try:
        resp = requests.get(
            url,
            params={
                "client_id": app_id,
                "client_secret": secret,
                "code": code_s,
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.warning("es_recovery_exchange_http_error")
        return {
            "ok": False,
            "error": f"http_error: {type(exc).__name__}",
            "token_obtained": False,
        }

    try:
        body = resp.json()
    except ValueError:
        logger.warning("es_recovery_exchange_non_json status=%s", resp.status_code)
        return {
            "ok": False,
            "error": "non_json_response",
            "http_status": resp.status_code,
            "token_obtained": False,
        }

    if not isinstance(body, dict):
        return {"ok": False, "error": "unexpected_response_shape", "token_obtained": False}

    err = body.get("error")
    if err:
        # Never include raw error payloads that might echo secrets; keep code/message only.
        err_obj = err if isinstance(err, dict) else {}
        logger.warning(
            "es_recovery_exchange_meta_error code=%s",
            err_obj.get("code"),
        )
        return {
            "ok": False,
            "error": "meta_oauth_error",
            "meta_error_code": err_obj.get("code"),
            "meta_error_type": err_obj.get("type"),
            "meta_error_message": str(err_obj.get("message") or "")[:180] or None,
            "http_status": resp.status_code,
            "token_obtained": False,
        }

    token = (body.get("access_token") or "").strip()
    if not token:
        return {
            "ok": False,
            "error": "missing_access_token_in_response",
            "http_status": resp.status_code,
            "token_obtained": False,
        }

    # Token intentionally discarded after presence check — not returned, not stored.
    return {
        "ok": True,
        "token_obtained": True,
        "token_type": (body.get("token_type") or None),
        "expires_in": body.get("expires_in"),
        "http_status": resp.status_code,
        "token_persisted": False,
        "token_logged": False,
    }


def _confirm_phone_access(token: str, phone_number_id: str) -> dict[str, Any]:
    """Optional Graph confirm with ephemeral token. Token never logged."""
    url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{phone_number_id}"
    try:
        resp = requests.get(
            url,
            params={"fields": "id,display_phone_number,verified_name"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        body = resp.json() if resp.content else {}
    except requests.RequestException as exc:
        return {"ok": False, "error": f"http_error: {type(exc).__name__}"}
    except ValueError:
        return {"ok": False, "error": "non_json_response"}

    if not isinstance(body, dict) or body.get("error"):
        err = body.get("error") if isinstance(body, dict) else None
        err_obj = err if isinstance(err, dict) else {}
        return {
            "ok": False,
            "error": "graph_phone_lookup_failed",
            "meta_error_code": err_obj.get("code"),
        }

    returned_id = str(body.get("id") or "").strip()
    return {
        "ok": returned_id == TARGET_PHONE_NUMBER_ID,
        "phone_number_id": returned_id or None,
        "display_phone_number": body.get("display_phone_number"),
        "verified_name": body.get("verified_name"),
        "matches_target": returned_id == TARGET_PHONE_NUMBER_ID,
    }


def complete_embedded_signup_recovery(
    *,
    code: str,
    waba_id: str,
    phone_number_id: str,
    business_id: str = "",
    session_event: str = "",
) -> dict[str, Any]:
    """
    Complete Phase 2B recovery:
    1) HARD ASSERT existing WABA + phone
    2) Exchange authorization code (ephemeral)
    3) Optionally confirm phone via Graph
    4) STOP — never call /register
    """
    base: dict[str, Any] = {
        "ok": False,
        "phase": "2b_embedded_signup_recovery",
        "recovery_marker": RECOVERY_MARKER,
        "register_called": False,
        "assets_created": False,
        "assets_deleted": False,
        "deregister_called": False,
        "token_persisted": False,
        "completed_at": _utc_now_iso(),
        "business_id": (business_id or "").strip() or None,
        "session_event": (session_event or "").strip() or None,
    }

    assertion = assert_existing_assets(waba_id=waba_id, phone_number_id=phone_number_id)
    base["assertion"] = assertion
    base["waba_id"] = assertion.get("waba_id")
    base["phone_number_id"] = assertion.get("phone_number_id")
    if assertion.get("aborted"):
        base["error"] = "asset_assertion_failed"
        base["aborted"] = True
        logger.warning(
            "es_recovery_assert_abort waba_match=%s phone_match=%s",
            assertion.get("waba_match"),
            assertion.get("phone_match"),
        )
        return base

    # Exchange — capture token only in local scope for optional confirm.
    code_s = (code or "").strip()
    if not code_s:
        base["error"] = "missing_authorization_code"
        base["aborted"] = True
        return base

    env = read_embedded_signup_env()
    app_id = env["app_id"]
    secret = _app_secret()
    if not app_id or not secret:
        base["error"] = "missing_app_id_or_secret"
        base["aborted"] = True
        return base

    url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/oauth/access_token"
    token: Optional[str] = None
    try:
        resp = requests.get(
            url,
            params={
                "client_id": app_id,
                "client_secret": secret,
                "code": code_s,
            },
            timeout=30,
        )
        body = resp.json() if resp.content else {}
    except requests.RequestException as exc:
        logger.warning("es_recovery_complete_http_error")
        base["error"] = f"exchange_http_error: {type(exc).__name__}"
        base["aborted"] = True
        return base
    except ValueError:
        logger.warning("es_recovery_complete_non_json")
        base["error"] = "exchange_non_json"
        base["aborted"] = True
        return base

    if not isinstance(body, dict):
        base["error"] = "exchange_unexpected_shape"
        base["aborted"] = True
        return base

    if body.get("error"):
        err_obj = body["error"] if isinstance(body["error"], dict) else {}
        logger.warning(
            "es_recovery_complete_meta_error code=%s",
            err_obj.get("code"),
        )
        base["error"] = "meta_oauth_error"
        base["meta_error_code"] = err_obj.get("code")
        base["meta_error_type"] = err_obj.get("type")
        base["meta_error_message"] = str(err_obj.get("message") or "")[:180] or None
        base["aborted"] = True
        return base

    token = (body.get("access_token") or "").strip() or None
    if not token:
        base["error"] = "missing_access_token"
        base["aborted"] = True
        return base

    phone_confirm = _confirm_phone_access(token, TARGET_PHONE_NUMBER_ID)
    # Drop token reference immediately after confirm.
    token = None
    del body  # may have contained access_token

    base["authorization_obtained"] = True
    base["phone_confirm"] = {
        "ok": bool(phone_confirm.get("ok")),
        "matches_target": bool(phone_confirm.get("matches_target")),
        "display_phone_number": phone_confirm.get("display_phone_number"),
        "verified_name": phone_confirm.get("verified_name"),
        "error": phone_confirm.get("error"),
    }
    if phone_confirm.get("ok") is False and phone_confirm.get("error"):
        # Authorization obtained; Graph confirm optional — still success for ES gate
        # if assert + token exchange succeeded. Surface confirm failure without aborting
        # the authorization evidence unless ID mismatched.
        if phone_confirm.get("phone_number_id") and not phone_confirm.get("matches_target"):
            base["ok"] = False
            base["aborted"] = True
            base["error"] = "phone_confirm_mismatch"
            return base

    base["ok"] = True
    base["aborted"] = False
    base["existing_waba_confirmed"] = True
    base["existing_phone_confirmed"] = True
    base["fresh_authorization_obtained"] = True
    base["duplicate_waba_created"] = False
    base["duplicate_phone_created"] = False
    base["next_phase"] = "STOP — do not call /register yet"
    logger.info(
        "es_recovery_phase2b_success waba=%s phone=%s register_called=false",
        TARGET_WABA_ID,
        TARGET_PHONE_NUMBER_ID,
    )
    return base


__all__ = [
    "TARGET_WABA_ID",
    "TARGET_PHONE_NUMBER_ID",
    "RECOVERY_MARKER",
    "assert_existing_assets",
    "complete_embedded_signup_recovery",
    "exchange_authorization_code",
    "public_recovery_config",
    "read_embedded_signup_env",
]
