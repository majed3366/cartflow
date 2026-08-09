# -*- coding: utf-8 -*-
"""
Admin-only WhatsApp Control Number Embedded Signup (Phase C2).

Authorize a NEW clean control phone onto the EXISTING CartFlow WABA.
Isolated from production ES recovery and register allowlist.

Does NOT:
- call /register
- overwrite WHATSAPP_PHONE_NUMBER_ID / WHATSAPP_BUSINESS_ACCOUNT_ID
- persist tokens or mutate merchant DB
- accept the production Phone Number ID
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from services.admin_whatsapp_embedded_signup_recovery_v1 import (
    TARGET_WABA_ID as PRODUCTION_WABA_ID,
    _exchange_code_internal,
    read_embedded_signup_env,
)
from services.admin_whatsapp_meta_status_v1 import META_GRAPH_VERSION

logger = logging.getLogger(__name__)

# Production assets — immutable; abort if control flow resolves to these.
PRODUCTION_PHONE_NUMBER_ID = "1260388737156321"
PRODUCTION_PHONE_E164 = "+966579706669"

# Control targets
CONTROL_WABA_ID = PRODUCTION_WABA_ID  # same WABA required
CONTROL_PHONE_E164 = "+966533132601"
CONTROL_PHONE_DISPLAY_HINT = "+966 53 313 2601"

# Dedicated C2 Login for Business configuration (WhatsApp ES template).
# Never fall back to META_WHATSAPP_CONFIGURATION_ID (Phase 2B recovery).
CONTROL_CONFIGURATION_ENV_KEY = "META_WHATSAPP_CONTROL_CONFIGURATION_ID"

RECOVERY_MARKER = "control-number-es-v1"
PHASE = "c2_control_number_es"
RESOLUTION_BROWSER = "browser_session"
RESOLUTION_FALLBACK = "server_waba_phone_lookup"

FB_SDK_VERSION = "v21.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_control_configuration_id() -> str:
    """C2-only config_id. Does not read META_WHATSAPP_CONFIGURATION_ID."""
    return (os.getenv(CONTROL_CONFIGURATION_ENV_KEY) or "").strip()


def normalize_e164(raw: Any) -> str:
    """Normalize display / E.164-ish strings to +digits only."""
    s = str(raw or "").strip()
    if not s:
        return ""
    digits = re.sub(r"\D", "", s)
    if not digits:
        return ""
    if s.startswith("+") or digits.startswith("966") or digits.startswith("00"):
        if digits.startswith("00"):
            digits = digits[2:]
        return f"+{digits}"
    return f"+{digits}"


def public_control_config() -> dict[str, Any]:
    """Admin bootstrap — secrets never included.

    configuration_id comes ONLY from META_WHATSAPP_CONTROL_CONFIGURATION_ID.
    Phase 2B META_WHATSAPP_CONFIGURATION_ID is intentionally unused here.
    """
    env = read_embedded_signup_env()
    control_configuration_id = read_control_configuration_id()
    ready = bool(
        env["app_id"] and control_configuration_id and env["app_secret_configured"]
    )
    return {
        "ok": True,
        "ready": ready,
        "app_id": env["app_id"] or None,
        "configuration_id": control_configuration_id or None,
        "configuration_id_env": CONTROL_CONFIGURATION_ENV_KEY,
        "configuration_id_source": CONTROL_CONFIGURATION_ENV_KEY,
        "uses_recovery_configuration_id": False,
        "app_secret_configured": env["app_secret_configured"],
        "graph_version": env["graph_version"],
        "fb_sdk_version": FB_SDK_VERSION,
        "control_waba_id": CONTROL_WABA_ID,
        "control_phone_e164": CONTROL_PHONE_E164,
        "control_phone_display": CONTROL_PHONE_DISPLAY_HINT,
        "production_phone_number_id": PRODUCTION_PHONE_NUMBER_ID,
        "production_phone_e164": PRODUCTION_PHONE_E164,
        "register_allowed": False,
        "register_called": False,
        "recovery_marker": RECOVERY_MARKER,
        "phase": PHASE,
        "stop_before_register": True,
        "isolates_production_env": True,
        "shared_waba_phone_fallback_enabled": True,
    }


def assert_control_assets(
    *,
    waba_id: str,
    phone_number_id: str,
    display_phone_number: str = "",
) -> dict[str, Any]:
    """
    HARD ASSERT control path.
    - WABA must be production WABA
    - Phone Number ID must NOT be production phone
    - If display provided, normalized E.164 must match control
    """
    waba = (waba_id or "").strip()
    phone = (phone_number_id or "").strip()
    display_norm = normalize_e164(display_phone_number) if display_phone_number else ""

    waba_ok = waba == CONTROL_WABA_ID
    not_production_phone = bool(phone) and phone != PRODUCTION_PHONE_NUMBER_ID
    e164_ok = (not display_norm) or (display_norm == CONTROL_PHONE_E164)

    if waba_ok and not_production_phone and e164_ok:
        return {
            "ok": True,
            "aborted": False,
            "waba_id": waba,
            "phone_number_id": phone,
            "display_phone_normalized": display_norm or None,
            "waba_match": True,
            "phone_is_not_production": True,
            "e164_match": True if display_norm else None,
            "reason": None,
        }

    reason_parts: list[str] = []
    if not waba_ok:
        if not waba:
            reason_parts.append(f"waba_missing: expected={CONTROL_WABA_ID}")
        elif waba != CONTROL_WABA_ID:
            reason_parts.append(
                f"waba_mismatch_or_new_waba: got={waba} expected={CONTROL_WABA_ID} — ABORT"
            )
    if not phone:
        reason_parts.append("phone_number_id_missing")
    elif phone == PRODUCTION_PHONE_NUMBER_ID:
        reason_parts.append(
            f"production_phone_id_appeared: {PRODUCTION_PHONE_NUMBER_ID} — ABORT"
        )
    if display_norm and display_norm != CONTROL_PHONE_E164:
        reason_parts.append(
            f"phone_e164_mismatch: got={display_norm} expected={CONTROL_PHONE_E164}"
        )

    return {
        "ok": False,
        "aborted": True,
        "waba_id": waba or None,
        "phone_number_id": phone or None,
        "display_phone_normalized": display_norm or None,
        "waba_match": waba_ok,
        "phone_is_not_production": not_production_phone,
        "e164_match": e164_ok if display_norm else None,
        "reason": "; ".join(reason_parts) or "control_assertion_failed",
        "action": (
            "ABORT — do not register, do not overwrite production env, "
            "do not accept other WABA without owner approval"
        ),
    }


def _graph_get(
    *,
    path: str,
    token: str,
    params: Optional[dict[str, Any]] = None,
) -> tuple[Optional[int], Any, Optional[str]]:
    url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(url, params=dict(params or {}), headers=headers, timeout=30)
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


def _confirm_phone_access(token: str, phone_number_id: str) -> dict[str, Any]:
    status, body, transport_err = _graph_get(
        path=phone_number_id,
        token=token,
        params={"fields": "id,display_phone_number,verified_name"},
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
    display = body.get("display_phone_number")
    return {
        "ok": bool(returned_id),
        "phone_number_id": returned_id or None,
        "display_phone_number": display,
        "display_phone_normalized": normalize_e164(display),
        "verified_name": body.get("verified_name"),
    }


def _list_waba_phones(*, waba_id: str, auth_token: str) -> dict[str, Any]:
    status, body, transport_err = _graph_get(
        path=f"{waba_id}/phone_numbers",
        token=auth_token,
        params={"fields": "id,display_phone_number,verified_name", "limit": 50},
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
    phones: list[dict[str, Any]] = []
    control_match: Optional[dict[str, Any]] = None
    production_present = False
    for row in rows:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        pid = str(row["id"])
        display = row.get("display_phone_number")
        norm = normalize_e164(display)
        entry = {
            "id": pid,
            "display_phone_number": display,
            "display_phone_normalized": norm,
            "verified_name": row.get("verified_name"),
            "is_production": pid == PRODUCTION_PHONE_NUMBER_ID,
            "is_control_e164": norm == CONTROL_PHONE_E164,
        }
        phones.append(entry)
        if pid == PRODUCTION_PHONE_NUMBER_ID:
            production_present = True
        if norm == CONTROL_PHONE_E164 and pid != PRODUCTION_PHONE_NUMBER_ID:
            control_match = entry

    return {
        "ok": True,
        "count": len(phones),
        "production_phone_present": production_present,
        "control_phone_found": control_match is not None,
        "control_phone": control_match,
        # Sanitize: ids + norms only, no tokens
        "phone_summaries": [
            {
                "id": p["id"],
                "display_phone_normalized": p["display_phone_normalized"],
                "is_production": p["is_production"],
                "is_control_e164": p["is_control_e164"],
            }
            for p in phones
        ],
        "http_status": status,
    }


def resolve_control_phone_fallback(*, access_token: str) -> dict[str, Any]:
    """
    When browser session IDs are missing: list phones on CONTROL_WABA_ID and
    find the control E.164. Never accepts production Phone Number ID.
    """
    out: dict[str, Any] = {
        "ok": False,
        "resolution_source": RESOLUTION_FALLBACK,
        "register_called": False,
        "aborted": True,
        "waba_id": CONTROL_WABA_ID,
    }
    phones = _list_waba_phones(waba_id=CONTROL_WABA_ID, auth_token=access_token)
    out["phone_lookup"] = {
        "ok": phones.get("ok"),
        "error": phones.get("error"),
        "meta_error_code": phones.get("meta_error_code"),
        "meta_error_message": phones.get("meta_error_message"),
        "count": phones.get("count"),
        "production_phone_present": phones.get("production_phone_present"),
        "control_phone_found": phones.get("control_phone_found"),
        "phone_summaries": phones.get("phone_summaries"),
    }
    if not phones.get("ok"):
        out["error"] = phones.get("error") or "waba_phone_list_failed"
        return out

    match = phones.get("control_phone")
    if not match:
        out["error"] = "control_phone_not_found_on_waba"
        return out

    pid = str(match.get("id") or "")
    if pid == PRODUCTION_PHONE_NUMBER_ID:
        out["error"] = "production_phone_id_appeared"
        out["new_phone_number_id"] = pid
        return out

    out["ok"] = True
    out["aborted"] = False
    out["error"] = None
    out["new_phone_number_id"] = pid
    out["display_phone_number"] = match.get("display_phone_number")
    out["display_phone_normalized"] = match.get("display_phone_normalized")
    out["verified_name"] = match.get("verified_name")
    out["production_phone_untouched"] = True
    return out


def _success_payload(
    *,
    new_phone_number_id: str,
    resolution_source: str,
    display_phone_number: Any = None,
    verified_name: Any = None,
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "ok": True,
        "aborted": False,
        "phase": PHASE,
        "recovery_marker": RECOVERY_MARKER,
        "control_phone": CONTROL_PHONE_E164,
        "waba_id": CONTROL_WABA_ID,
        "new_phone_number_id": new_phone_number_id,
        "production_phone_number_id": PRODUCTION_PHONE_NUMBER_ID,
        "production_phone_untouched": True,
        "register_called": False,
        "register_allowed": False,
        "token_persisted": False,
        "env_mutated": False,
        "db_mutated": False,
        "runtime_switched": False,
        "assets_deleted": False,
        "deregister_called": False,
        "resolution_source": resolution_source,
        "display_phone_number": display_phone_number,
        "display_phone_normalized": normalize_e164(display_phone_number)
        if display_phone_number
        else CONTROL_PHONE_E164,
        "verified_name": verified_name,
        "next_phase": "STOP — do not call /register yet",
        "completed_at": _utc_now_iso(),
    }
    payload.update(extra)
    return payload


def complete_control_number_es(
    *,
    code: str,
    waba_id: str = "",
    phone_number_id: str = "",
    business_id: str = "",
    session_event: str = "",
    display_phone_number: str = "",
    allow_waba_phone_fallback: bool = False,
    dialog_redirect_uri: str = "",
    spawn_page_uri: str = "",
) -> dict[str, Any]:
    """
    Complete Phase C2 control ES:
    - Assert same WABA, control E.164, non-production Phone Number ID
    - Ephemeral code exchange
    - STOP before /register
    """
    base: dict[str, Any] = {
        "ok": False,
        "phase": PHASE,
        "recovery_marker": RECOVERY_MARKER,
        "control_phone": CONTROL_PHONE_E164,
        "register_called": False,
        "register_allowed": False,
        "token_persisted": False,
        "env_mutated": False,
        "db_mutated": False,
        "runtime_switched": False,
        "production_phone_untouched": True,
        "completed_at": _utc_now_iso(),
        "business_id": (business_id or "").strip() or None,
        "session_event": (session_event or "").strip() or None,
    }

    waba = (waba_id or "").strip()
    phone = (phone_number_id or "").strip()
    display_hint = (display_phone_number or "").strip()
    session_ids_present = bool(waba and phone)
    session_ids_partial = bool(waba or phone) and not session_ids_present

    # Immediate abort if production phone ID appears anywhere in session.
    if phone == PRODUCTION_PHONE_NUMBER_ID:
        base["error"] = "production_phone_id_appeared"
        base["aborted"] = True
        base["waba_id"] = waba or None
        base["new_phone_number_id"] = phone
        base["assertion"] = assert_control_assets(
            waba_id=waba, phone_number_id=phone, display_phone_number=display_hint
        )
        logger.warning("control_es_abort production_phone_id_appeared")
        return base

    if session_ids_present:
        assertion = assert_control_assets(
            waba_id=waba,
            phone_number_id=phone,
            display_phone_number=display_hint,
        )
        base["assertion"] = assertion
        base["waba_id"] = assertion.get("waba_id")
        base["new_phone_number_id"] = assertion.get("phone_number_id")
        if assertion.get("aborted"):
            base["error"] = "asset_assertion_failed"
            base["aborted"] = True
            base["resolution_source"] = RESOLUTION_BROWSER
            logger.warning(
                "control_es_assert_abort waba_match=%s not_prod=%s e164=%s",
                assertion.get("waba_match"),
                assertion.get("phone_is_not_production"),
                assertion.get("e164_match"),
            )
            return base
    elif session_ids_partial:
        # New WABA without phone, or phone without WABA — abort (no inventing).
        if waba and waba != CONTROL_WABA_ID:
            base["error"] = "waba_mismatch_or_new_waba"
            base["aborted"] = True
            base["waba_id"] = waba
            return base
        base["error"] = "incomplete_session_asset_ids"
        base["aborted"] = True
        base["waba_id"] = waba or None
        base["new_phone_number_id"] = phone or None
        return base
    elif not allow_waba_phone_fallback:
        base["error"] = "missing_session_asset_ids"
        base["aborted"] = True
        return base

    token, exchange_meta = _exchange_code_internal(
        code,
        dialog_redirect_uri=dialog_redirect_uri,
        spawn_page_uri=spawn_page_uri,
    )
    if exchange_meta.get("oauth_exchange"):
        base["oauth_exchange"] = exchange_meta["oauth_exchange"]
    if exchange_meta.get("graph_endpoint"):
        base["graph_endpoint"] = exchange_meta["graph_endpoint"]
    if not token:
        base.update(
            {
                k: v
                for k, v in exchange_meta.items()
                if k not in ("ok", "oauth_exchange", "graph_endpoint")
            }
        )
        base["ok"] = False
        base["aborted"] = True
        base["error"] = exchange_meta.get("error") or "exchange_failed"
        base["token_obtained"] = False
        return base

    base["authorization_obtained"] = True
    base["token_obtained"] = True

    if session_ids_present:
        phone_confirm = _confirm_phone_access(token, phone)
        token = None
        base["resolution_source"] = RESOLUTION_BROWSER
        display_norm = phone_confirm.get("display_phone_normalized") or ""
        base["phone_confirm"] = {
            "ok": bool(phone_confirm.get("ok")),
            "phone_number_id": phone_confirm.get("phone_number_id"),
            "display_phone_number": phone_confirm.get("display_phone_number"),
            "display_phone_normalized": display_norm or None,
            "verified_name": phone_confirm.get("verified_name"),
            "error": phone_confirm.get("error"),
        }

        confirmed_id = str(phone_confirm.get("phone_number_id") or phone).strip()
        if confirmed_id == PRODUCTION_PHONE_NUMBER_ID:
            base["ok"] = False
            base["aborted"] = True
            base["error"] = "production_phone_id_appeared"
            base["new_phone_number_id"] = confirmed_id
            return base

        if display_norm and display_norm != CONTROL_PHONE_E164:
            base["ok"] = False
            base["aborted"] = True
            base["error"] = "phone_e164_mismatch"
            base["new_phone_number_id"] = confirmed_id
            return base

        # Prefer Graph-confirmed display; if Graph failed but session asserted, still require E.164 later.
        if phone_confirm.get("ok") is False and not display_hint:
            # Without display we cannot prove control E.164 — abort.
            base["ok"] = False
            base["aborted"] = True
            base["error"] = "phone_confirm_failed_no_e164"
            return base

        if not display_norm and display_hint:
            display_norm = normalize_e164(display_hint)
            if display_norm != CONTROL_PHONE_E164:
                base["ok"] = False
                base["aborted"] = True
                base["error"] = "phone_e164_mismatch"
                return base

        if display_norm and display_norm != CONTROL_PHONE_E164:
            base["ok"] = False
            base["aborted"] = True
            base["error"] = "phone_e164_mismatch"
            return base

        # Final hard assert on confirmed id
        final = assert_control_assets(
            waba_id=CONTROL_WABA_ID,
            phone_number_id=confirmed_id,
            display_phone_number=display_norm or CONTROL_PHONE_E164,
        )
        if final.get("aborted"):
            base["ok"] = False
            base["aborted"] = True
            base["error"] = "asset_assertion_failed"
            base["assertion"] = final
            return base

        result = _success_payload(
            new_phone_number_id=confirmed_id,
            resolution_source=RESOLUTION_BROWSER,
            display_phone_number=phone_confirm.get("display_phone_number")
            or CONTROL_PHONE_DISPLAY_HINT,
            verified_name=phone_confirm.get("verified_name"),
            session_event=base.get("session_event"),
            business_id=base.get("business_id"),
            phone_confirm=base.get("phone_confirm"),
            authorization_obtained=True,
            token_obtained=True,
            oauth_exchange=base.get("oauth_exchange"),
            graph_endpoint=base.get("graph_endpoint"),
        )
        logger.info(
            "control_es_c2_success source=%s new_phone_id=%s register_called=false",
            RESOLUTION_BROWSER,
            confirmed_id,
        )
        return result

    # Fallback: discover control phone on same WABA
    fallback = resolve_control_phone_fallback(access_token=token)
    token = None
    base["resolution_source"] = RESOLUTION_FALLBACK
    base["phone_lookup"] = fallback.get("phone_lookup")

    if not fallback.get("ok"):
        base["ok"] = False
        base["aborted"] = True
        base["error"] = fallback.get("error") or "control_phone_fallback_failed"
        base["waba_id"] = CONTROL_WABA_ID
        base["new_phone_number_id"] = fallback.get("new_phone_number_id")
        return base

    new_id = str(fallback.get("new_phone_number_id") or "")
    final = assert_control_assets(
        waba_id=CONTROL_WABA_ID,
        phone_number_id=new_id,
        display_phone_number=fallback.get("display_phone_normalized")
        or CONTROL_PHONE_E164,
    )
    if final.get("aborted"):
        base["ok"] = False
        base["aborted"] = True
        base["error"] = "asset_assertion_failed"
        base["assertion"] = final
        return base

    result = _success_payload(
        new_phone_number_id=new_id,
        resolution_source=RESOLUTION_FALLBACK,
        display_phone_number=fallback.get("display_phone_number"),
        verified_name=fallback.get("verified_name"),
        session_event=base.get("session_event"),
        business_id=base.get("business_id"),
        phone_lookup=fallback.get("phone_lookup"),
        authorization_obtained=True,
        token_obtained=True,
        oauth_exchange=base.get("oauth_exchange"),
        graph_endpoint=base.get("graph_endpoint"),
    )
    logger.info(
        "control_es_c2_success source=%s new_phone_id=%s register_called=false",
        RESOLUTION_FALLBACK,
        new_id,
    )
    return result


__all__ = [
    "CONTROL_CONFIGURATION_ENV_KEY",
    "CONTROL_PHONE_E164",
    "CONTROL_WABA_ID",
    "PHASE",
    "PRODUCTION_PHONE_NUMBER_ID",
    "RECOVERY_MARKER",
    "assert_control_assets",
    "complete_control_number_es",
    "normalize_e164",
    "public_control_config",
    "read_control_configuration_id",
]
