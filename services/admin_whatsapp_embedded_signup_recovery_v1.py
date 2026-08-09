# -*- coding: utf-8 -*-
"""
Admin-only WhatsApp Embedded Signup recovery (Phase 2B).

Re-authorize EXISTING CartFlow WABA + phone via Meta ES.
Does NOT register, delete, create, or deregister Meta assets.
Never logs or returns access tokens / app secrets.

Resolution paths:
1) Browser WA_EMBEDDED_SIGNUP session IDs (hard-asserted)
2) Server shared-WABA fallback after OAuth code exchange when session IDs are missing
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from services.admin_whatsapp_meta_status_v1 import META_GRAPH_VERSION, read_whatsapp_meta_env

logger = logging.getLogger(__name__)

# Hard targets — abort if ES returns anything else.
TARGET_WABA_ID = "1520530422625766"
TARGET_PHONE_NUMBER_ID = "1260388737156321"

FB_SDK_VERSION = "v21.0"
RECOVERY_MARKER = "whatsapp-es-recovery-v1"
RESOLUTION_BROWSER = "browser_session"
RESOLUTION_FALLBACK = "server_shared_waba_fallback"


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
    business_portfolio_id = _env_first(
        "META_BUSINESS_PORTFOLIO_ID",
        "META_BUSINESS_ID",
        "WHATSAPP_BUSINESS_PORTFOLIO_ID",
        "FACEBOOK_BUSINESS_ID",
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
        "business_portfolio_id_configured": bool(business_portfolio_id),
    }


def _app_secret() -> str:
    return _env_first("META_WHATSAPP_APP_SECRET", "META_APP_SECRET", "FACEBOOK_APP_SECRET")


def _app_access_token() -> str:
    """App token for debug_token only — never logged/returned."""
    app_id = _env_first("META_WHATSAPP_APP_ID", "WHATSAPP_APP_ID", "META_APP_ID")
    secret = _app_secret()
    if not app_id or not secret:
        return ""
    return f"{app_id}|{secret}"


def _partner_business_id(hint: str = "") -> str:
    hint_s = (hint or "").strip()
    if hint_s:
        return hint_s
    return _env_first(
        "META_BUSINESS_PORTFOLIO_ID",
        "META_BUSINESS_ID",
        "WHATSAPP_BUSINESS_PORTFOLIO_ID",
        "FACEBOOK_BUSINESS_ID",
    )


def _platform_system_token() -> str:
    """Path A platform token (optional) for partner BM shared-WABA list. Never logged."""
    return (read_whatsapp_meta_env().get("access_token") or "").strip()


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
        "shared_waba_fallback_enabled": True,
        "business_portfolio_id_configured": env["business_portfolio_id_configured"],
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


def _graph_get(
    *,
    path: str,
    token: str,
    params: Optional[dict[str, Any]] = None,
    use_bearer: bool = True,
) -> tuple[Optional[int], Any, Optional[str]]:
    url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{path.lstrip('/')}"
    query = dict(params or {})
    headers: dict[str, str] = {}
    if use_bearer:
        headers["Authorization"] = f"Bearer {token}"
    else:
        query["access_token"] = token
    try:
        resp = requests.get(url, params=query, headers=headers or None, timeout=30)
    except requests.RequestException as exc:
        return None, None, f"http_error: {type(exc).__name__}"
    try:
        body = resp.json() if resp.content else {}
    except ValueError:
        return resp.status_code, None, "non_json_response"
    return resp.status_code, body, None


def _safe_meta_error(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {}
    err = body.get("error")
    if not isinstance(err, dict):
        return {}
    return {
        "meta_error_code": err.get("code"),
        "meta_error_type": err.get("type"),
        "meta_error_subcode": err.get("error_subcode"),
        "meta_error_message": str(err.get("message") or "")[:180] or None,
    }


def exchange_authorization_code(code: str) -> dict[str, Any]:
    """
    Server-side code → token exchange.
    Returns metadata only — never the access_token value.
    """
    token, meta = _exchange_code_internal(code)
    if not token:
        return meta
    return {
        "ok": True,
        "token_obtained": True,
        "token_type": meta.get("token_type"),
        "expires_in": meta.get("expires_in"),
        "http_status": meta.get("http_status"),
        "token_persisted": False,
        "token_logged": False,
    }


def _exchange_code_internal(code: str) -> tuple[Optional[str], dict[str, Any]]:
    code_s = (code or "").strip()
    if not code_s:
        return None, {"ok": False, "error": "missing_authorization_code", "token_obtained": False}

    env = read_embedded_signup_env()
    app_id = env["app_id"]
    secret = _app_secret()
    if not app_id or not secret:
        return None, {
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
        status = resp.status_code
        body = resp.json() if resp.content else {}
    except requests.RequestException as exc:
        logger.warning("es_recovery_exchange_http_error")
        return None, {
            "ok": False,
            "error": f"http_error: {type(exc).__name__}",
            "token_obtained": False,
        }
    except ValueError:
        logger.warning("es_recovery_exchange_non_json")
        return None, {
            "ok": False,
            "error": "non_json_response",
            "token_obtained": False,
        }

    if not isinstance(body, dict):
        return None, {"ok": False, "error": "unexpected_response_shape", "token_obtained": False}

    if body.get("error"):
        err_meta = _safe_meta_error(body)
        logger.warning(
            "es_recovery_exchange_meta_error code=%s",
            err_meta.get("meta_error_code"),
        )
        return None, {
            "ok": False,
            "error": "meta_oauth_error",
            **err_meta,
            "http_status": status,
            "token_obtained": False,
        }

    token = (body.get("access_token") or "").strip()
    if not token:
        return None, {
            "ok": False,
            "error": "missing_access_token_in_response",
            "http_status": status,
            "token_obtained": False,
        }

    return token, {
        "ok": True,
        "token_obtained": True,
        "token_type": body.get("token_type"),
        "expires_in": body.get("expires_in"),
        "http_status": status,
    }


def debug_token_inspect(input_token: str) -> dict[str, Any]:
    """
    Validate/debug an ES user/business token.
    Never returns the input token or app token.
    """
    app_token = _app_access_token()
    if not app_token:
        return {"ok": False, "error": "missing_app_access_token"}

    status, body, transport_err = _graph_get(
        path="debug_token",
        token=app_token,
        params={"input_token": input_token},
        use_bearer=False,
    )
    if transport_err:
        return {"ok": False, "error": transport_err}
    if not isinstance(body, dict):
        return {"ok": False, "error": "unexpected_response_shape", "http_status": status}
    if body.get("error"):
        return {"ok": False, "error": "debug_token_meta_error", **_safe_meta_error(body)}

    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    scopes = [str(s) for s in (data.get("scopes") or []) if s]
    granular = data.get("granular_scopes") if isinstance(data.get("granular_scopes"), list) else []

    waba_candidates: list[str] = []
    scope_summaries: list[dict[str, Any]] = []
    has_business_management = "business_management" in scopes
    has_waba_mgmt = "whatsapp_business_management" in scopes
    has_waba_messaging = "whatsapp_business_messaging" in scopes

    for item in granular:
        if not isinstance(item, dict):
            continue
        scope = str(item.get("scope") or "")
        target_ids = [str(t) for t in (item.get("target_ids") or []) if t]
        scope_summaries.append(
            {
                "scope": scope,
                "target_id_count": len(target_ids),
                "contains_target_waba": TARGET_WABA_ID in target_ids,
            }
        )
        if "whatsapp_business" in scope:
            for tid in target_ids:
                if tid not in waba_candidates:
                    waba_candidates.append(tid)

    return {
        "ok": True,
        "is_valid": bool(data.get("is_valid")),
        "type": data.get("type"),
        "scopes": scopes,
        "has_business_management": has_business_management,
        "has_whatsapp_business_management": has_waba_mgmt,
        "has_whatsapp_business_messaging": has_waba_messaging,
        "granular_scope_summaries": scope_summaries,
        "waba_candidates_from_granular": waba_candidates,
        "target_waba_in_granular": TARGET_WABA_ID in waba_candidates,
        "app_id": str(data.get("app_id") or "") or None,
        "http_status": status,
    }


def _list_client_whatsapp_business_accounts(
    *,
    business_id: str,
    auth_token: str,
) -> dict[str, Any]:
    status, body, transport_err = _graph_get(
        path=f"{business_id}/client_whatsapp_business_accounts",
        token=auth_token,
        params={"fields": "id,name", "limit": 100},
        use_bearer=True,
    )
    if transport_err:
        return {"ok": False, "error": transport_err}
    if not isinstance(body, dict):
        return {"ok": False, "error": "unexpected_response_shape", "http_status": status}
    if body.get("error"):
        return {
            "ok": False,
            "error": "client_waba_list_meta_error",
            **_safe_meta_error(body),
            "http_status": status,
        }

    rows = body.get("data") if isinstance(body.get("data"), list) else []
    ids: list[str] = []
    for row in rows:
        if isinstance(row, dict) and row.get("id"):
            ids.append(str(row["id"]))
    return {
        "ok": True,
        "waba_ids": ids,
        "count": len(ids),
        "contains_target_waba": TARGET_WABA_ID in ids,
        "http_status": status,
    }


def _list_waba_phone_numbers(*, waba_id: str, auth_token: str) -> dict[str, Any]:
    status, body, transport_err = _graph_get(
        path=f"{waba_id}/phone_numbers",
        token=auth_token,
        params={"fields": "id,display_phone_number,verified_name", "limit": 50},
        use_bearer=True,
    )
    if transport_err:
        return {"ok": False, "error": transport_err}
    if not isinstance(body, dict):
        return {"ok": False, "error": "unexpected_response_shape", "http_status": status}
    if body.get("error"):
        return {
            "ok": False,
            "error": "waba_phone_list_meta_error",
            **_safe_meta_error(body),
            "http_status": status,
        }

    rows = body.get("data") if isinstance(body.get("data"), list) else []
    phone_ids: list[str] = []
    matched_display = None
    matched_name = None
    for row in rows:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        pid = str(row["id"])
        phone_ids.append(pid)
        if pid == TARGET_PHONE_NUMBER_ID:
            matched_display = row.get("display_phone_number")
            matched_name = row.get("verified_name")
    return {
        "ok": True,
        "phone_number_ids": phone_ids,
        "count": len(phone_ids),
        "contains_target_phone": TARGET_PHONE_NUMBER_ID in phone_ids,
        "display_phone_number": matched_display,
        "verified_name": matched_name,
        "http_status": status,
    }


def resolve_shared_waba_fallback(
    *,
    access_token: str,
    business_id_hint: str = "",
) -> dict[str, Any]:
    """
    After OAuth exchange, resolve EXISTING target WABA/phone without browser session IDs.
    Token is used only in-process and never returned.
    """
    out: dict[str, Any] = {
        "ok": False,
        "resolution_source": RESOLUTION_FALLBACK,
        "register_called": False,
        "aborted": True,
    }

    debug = debug_token_inspect(access_token)
    out["debug_token"] = {
        k: debug.get(k)
        for k in (
            "ok",
            "is_valid",
            "type",
            "scopes",
            "has_business_management",
            "has_whatsapp_business_management",
            "has_whatsapp_business_messaging",
            "granular_scope_summaries",
            "target_waba_in_granular",
            "app_id",
            "error",
            "meta_error_code",
            "meta_error_message",
        )
        if k in debug or debug.get(k) is not None
    }
    # Never echo candidate ID list beyond whether target matched + count
    out["debug_token"]["waba_candidate_count"] = len(
        debug.get("waba_candidates_from_granular") or []
    )

    waba_found = bool(debug.get("target_waba_in_granular"))
    client_list_meta: dict[str, Any] = {"attempted": False}

    business_id = _partner_business_id(business_id_hint)
    out["business_id_used"] = business_id or None

    if not waba_found and business_id:
        client_list_meta["attempted"] = True
        # Prefer platform system token for partner BM shared list; fall back to ES token.
        auth_candidates = []
        sys_tok = _platform_system_token()
        if sys_tok:
            auth_candidates.append(("platform_system_token", sys_tok))
        auth_candidates.append(("es_business_token", access_token))

        for label, tok in auth_candidates:
            listed = _list_client_whatsapp_business_accounts(
                business_id=business_id, auth_token=tok
            )
            client_list_meta["auth_used"] = label
            client_list_meta["ok"] = listed.get("ok")
            client_list_meta["error"] = listed.get("error")
            client_list_meta["meta_error_code"] = listed.get("meta_error_code")
            client_list_meta["meta_error_message"] = listed.get("meta_error_message")
            client_list_meta["count"] = listed.get("count")
            client_list_meta["contains_target_waba"] = listed.get("contains_target_waba")
            if listed.get("ok") and listed.get("contains_target_waba"):
                waba_found = True
                break
            if listed.get("ok"):
                # List succeeded but target absent — stop trying other tokens.
                break
    elif not waba_found and not business_id:
        client_list_meta["skipped_reason"] = "no_business_portfolio_id"

    out["client_whatsapp_business_accounts"] = client_list_meta

    if not waba_found:
        out["error"] = "target_waba_not_shared"
        out["waba_id"] = None
        out["phone_number_id"] = None
        logger.warning("es_recovery_fallback_target_waba_not_shared")
        return out

    phones = _list_waba_phone_numbers(waba_id=TARGET_WABA_ID, auth_token=access_token)
    out["phone_lookup"] = {
        "ok": phones.get("ok"),
        "error": phones.get("error"),
        "meta_error_code": phones.get("meta_error_code"),
        "meta_error_message": phones.get("meta_error_message"),
        "count": phones.get("count"),
        "contains_target_phone": phones.get("contains_target_phone"),
        "display_phone_number": phones.get("display_phone_number"),
        "verified_name": phones.get("verified_name"),
    }

    if not phones.get("ok") or not phones.get("contains_target_phone"):
        out["error"] = "target_phone_not_confirmed"
        out["waba_id"] = TARGET_WABA_ID
        out["phone_number_id"] = None
        logger.warning("es_recovery_fallback_target_phone_not_confirmed")
        return out

    out["ok"] = True
    out["aborted"] = False
    out["error"] = None
    out["waba_id"] = TARGET_WABA_ID
    out["phone_number_id"] = TARGET_PHONE_NUMBER_ID
    out["existing_waba_confirmed"] = True
    out["existing_phone_confirmed"] = True
    out["fresh_authorization_obtained"] = True
    out["duplicate_waba_created"] = False
    out["duplicate_phone_created"] = False
    out["assets_created"] = False
    out["assets_deleted"] = False
    out["deregister_called"] = False
    out["token_persisted"] = False
    out["next_phase"] = "STOP — do not call /register yet"
    return out


def _confirm_phone_access(token: str, phone_number_id: str) -> dict[str, Any]:
    """Optional Graph confirm with ephemeral token. Token never logged."""
    status, body, transport_err = _graph_get(
        path=phone_number_id,
        token=token,
        params={"fields": "id,display_phone_number,verified_name"},
        use_bearer=True,
    )
    if transport_err:
        return {"ok": False, "error": transport_err}
    if not isinstance(body, dict) or body.get("error"):
        return {
            "ok": False,
            "error": "graph_phone_lookup_failed",
            **_safe_meta_error(body if isinstance(body, dict) else {}),
            "http_status": status,
        }

    returned_id = str(body.get("id") or "").strip()
    return {
        "ok": returned_id == TARGET_PHONE_NUMBER_ID,
        "phone_number_id": returned_id or None,
        "display_phone_number": body.get("display_phone_number"),
        "verified_name": body.get("verified_name"),
        "matches_target": returned_id == TARGET_PHONE_NUMBER_ID,
    }


def _success_base(**extra: Any) -> dict[str, Any]:
    payload = {
        "ok": True,
        "aborted": False,
        "phase": "2b_embedded_signup_recovery",
        "recovery_marker": RECOVERY_MARKER,
        "register_called": False,
        "assets_created": False,
        "assets_deleted": False,
        "deregister_called": False,
        "token_persisted": False,
        "existing_waba_confirmed": True,
        "existing_phone_confirmed": True,
        "fresh_authorization_obtained": True,
        "duplicate_waba_created": False,
        "duplicate_phone_created": False,
        "waba_id": TARGET_WABA_ID,
        "phone_number_id": TARGET_PHONE_NUMBER_ID,
        "next_phase": "STOP — do not call /register yet",
        "completed_at": _utc_now_iso(),
    }
    payload.update(extra)
    return payload


def complete_embedded_signup_recovery(
    *,
    code: str,
    waba_id: str = "",
    phone_number_id: str = "",
    business_id: str = "",
    session_event: str = "",
    allow_shared_waba_fallback: bool = False,
) -> dict[str, Any]:
    """
    Complete Phase 2B recovery:
    - If browser session IDs present: HARD ASSERT then exchange.
    - If IDs missing and fallback allowed: exchange then shared-WABA resolve.
    - STOP — never call /register.
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

    waba = (waba_id or "").strip()
    phone = (phone_number_id or "").strip()
    session_ids_present = bool(waba and phone)
    session_ids_partial = bool(waba or phone) and not session_ids_present

    # Wrong IDs from browser → abort (do not "fix" via fallback).
    if session_ids_present:
        assertion = assert_existing_assets(waba_id=waba, phone_number_id=phone)
        base["assertion"] = assertion
        base["waba_id"] = assertion.get("waba_id")
        base["phone_number_id"] = assertion.get("phone_number_id")
        if assertion.get("aborted"):
            base["error"] = "asset_assertion_failed"
            base["aborted"] = True
            base["resolution_source"] = RESOLUTION_BROWSER
            logger.warning(
                "es_recovery_assert_abort waba_match=%s phone_match=%s",
                assertion.get("waba_match"),
                assertion.get("phone_match"),
            )
            return base
    elif session_ids_partial:
        base["error"] = "incomplete_session_asset_ids"
        base["aborted"] = True
        base["waba_id"] = waba or None
        base["phone_number_id"] = phone or None
        return base
    elif not allow_shared_waba_fallback:
        base["error"] = "missing_session_asset_ids"
        base["aborted"] = True
        return base

    token, exchange_meta = _exchange_code_internal(code)
    if not token:
        base.update({k: v for k, v in exchange_meta.items() if k != "ok"})
        base["ok"] = False
        base["aborted"] = True
        base["error"] = exchange_meta.get("error") or "exchange_failed"
        return base

    base["authorization_obtained"] = True

    # Path A — browser session IDs already asserted.
    if session_ids_present:
        phone_confirm = _confirm_phone_access(token, TARGET_PHONE_NUMBER_ID)
        token = None
        base["resolution_source"] = RESOLUTION_BROWSER
        base["phone_confirm"] = {
            "ok": bool(phone_confirm.get("ok")),
            "matches_target": bool(phone_confirm.get("matches_target")),
            "display_phone_number": phone_confirm.get("display_phone_number"),
            "verified_name": phone_confirm.get("verified_name"),
            "error": phone_confirm.get("error"),
        }
        if phone_confirm.get("phone_number_id") and not phone_confirm.get("matches_target"):
            base["ok"] = False
            base["aborted"] = True
            base["error"] = "phone_confirm_mismatch"
            return base

        result = _success_base(
            resolution_source=RESOLUTION_BROWSER,
            session_event=base.get("session_event"),
            business_id=base.get("business_id"),
            phone_confirm=base.get("phone_confirm"),
            authorization_obtained=True,
        )
        logger.info(
            "es_recovery_phase2b_success source=%s register_called=false",
            RESOLUTION_BROWSER,
        )
        return result

    # Path B — shared WABA fallback (session IDs missing).
    fallback = resolve_shared_waba_fallback(
        access_token=token,
        business_id_hint=(business_id or ""),
    )
    token = None

    if not fallback.get("ok"):
        base["ok"] = False
        base["aborted"] = True
        base["error"] = fallback.get("error") or "shared_waba_fallback_failed"
        base["resolution_source"] = RESOLUTION_FALLBACK
        base["waba_id"] = fallback.get("waba_id")
        base["phone_number_id"] = fallback.get("phone_number_id")
        base["debug_token"] = fallback.get("debug_token")
        base["client_whatsapp_business_accounts"] = fallback.get(
            "client_whatsapp_business_accounts"
        )
        base["phone_lookup"] = fallback.get("phone_lookup")
        base["business_id_used"] = fallback.get("business_id_used")
        return base

    result = _success_base(
        resolution_source=RESOLUTION_FALLBACK,
        session_event=base.get("session_event"),
        business_id=base.get("business_id"),
        authorization_obtained=True,
        debug_token=fallback.get("debug_token"),
        client_whatsapp_business_accounts=fallback.get(
            "client_whatsapp_business_accounts"
        ),
        phone_lookup=fallback.get("phone_lookup"),
        business_id_used=fallback.get("business_id_used"),
    )
    logger.info(
        "es_recovery_phase2b_success source=%s register_called=false",
        RESOLUTION_FALLBACK,
    )
    return result


__all__ = [
    "TARGET_WABA_ID",
    "TARGET_PHONE_NUMBER_ID",
    "RECOVERY_MARKER",
    "RESOLUTION_BROWSER",
    "RESOLUTION_FALLBACK",
    "assert_existing_assets",
    "complete_embedded_signup_recovery",
    "debug_token_inspect",
    "exchange_authorization_code",
    "public_recovery_config",
    "read_embedded_signup_env",
    "resolve_shared_waba_fallback",
]
