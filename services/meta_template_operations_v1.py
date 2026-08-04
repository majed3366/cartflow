# -*- coding: utf-8 -*-
"""
Admin Meta message-template operations (list / inspect / create recovery contract).

Never logs or returns access tokens. Never calls WhatsApp /messages send.
Does not switch WHATSAPP_PROVIDER.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from services.admin_whatsapp_meta_status_v1 import PLACEHOLDER_TOKENS, read_whatsapp_meta_env
from services.meta_recovery_template_contract_v1 import (
    COMPARISON_DIFFERENT,
    COMPARISON_ERROR,
    COMPARISON_NOT_AVAILABLE,
    COMPARISON_SAME,
    HTTP_TIMEOUT_SECONDS,
    STATUS_NOT_CREATED,
    STATUS_UNKNOWN,
    TEMPLATE_CATEGORY,
    TEMPLATE_LANGUAGE,
    TEMPLATE_NAME,
    TEMPLATE_NAME_V1,
    build_template_payload,
    compare_remote_to_contract,
    local_contract_summary,
    mask_waba_id,
    normalize_meta_template_status,
    template_endpoint_url,
    validate_template_contract,
)

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def resolve_meta_template_credentials() -> dict[str, Any]:
    """
    Access token via existing platform env chain (read_whatsapp_meta_env).
    WABA via WHATSAPP_BUSINESS_ACCOUNT_ID → WABA_ID (same as read_whatsapp_meta_env).
    """
    env = read_whatsapp_meta_env()
    token = (env.get("access_token") or "").strip()
    waba = (env.get("waba_id") or "").strip()
    if token and token.lower() in PLACEHOLDER_TOKENS:
        token = ""
    if waba and waba.lower() in PLACEHOLDER_TOKENS:
        waba = ""
    waba_source = "missing"
    import os

    if (os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID") or "").strip() and waba:
        waba_source = "WHATSAPP_BUSINESS_ACCOUNT_ID"
    elif (os.getenv("WABA_ID") or "").strip() and waba:
        waba_source = "WABA_ID"
    return {
        "access_token": token or None,
        "waba_id": waba or None,
        "waba_source": waba_source,
        "waba_masked": mask_waba_id(waba) if waba else "—",
        "credential_configured": bool(token),
        "waba_configured": bool(waba),
    }


def _scrub(result: dict[str, Any]) -> dict[str, Any]:
    for k in list(result.keys()):
        lk = k.lower()
        if "token" in lk or "authorization" in lk or "secret" in lk:
            result.pop(k, None)
    return result


def _base_result(
    *,
    ok: bool,
    operation: str,
    trace_id: str,
    template_name: str = TEMPLATE_NAME,
    template_id: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    comparison: Optional[str] = None,
    error_code: Optional[str] = None,
    error_subcode: Optional[str] = None,
    error_message_safe: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": bool(ok),
        "operation": operation,
        "template_name": template_name,
        "template_id": template_id,
        "status": status,
        "category": category,
        "language": language or TEMPLATE_LANGUAGE,
        "comparison": comparison,
        "error_code": error_code,
        "error_subcode": error_subcode,
        "error_message_safe": error_message_safe,
        "trace_id": trace_id,
        "checked_at": _utc_now_iso(),
    }
    if extra:
        out.update(extra)
    return _scrub(out)


def _safe_meta_error(body: Any, status_code: int) -> tuple[Optional[str], Optional[str], str]:
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            code = err.get("code")
            sub = err.get("error_subcode")
            msg = str(err.get("message") or err.get("type") or "meta_api_error")
            if "access token" in msg.lower() or "oauth" in msg.lower():
                msg = "meta_auth_or_token_error"
            return (
                str(code) if code is not None else None,
                str(sub) if sub is not None else None,
                msg[:300],
            )
    return str(status_code), None, f"meta_http_{status_code}"


def _log_op(
    *,
    operation: str,
    template_name: str,
    waba_masked: str,
    status: str,
    error_code: Optional[str],
    error_subcode: Optional[str],
    trace_id: str,
) -> None:
    line = (
        f"[META TEMPLATE OPS] operation={operation} template_name={template_name} "
        f"waba={waba_masked} status={status} error_code={error_code or '-'} "
        f"error_subcode={error_subcode or '-'} trace_id={trace_id}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    logger.info("%s", line)


def _cred_gate(operation: str, trace_id: str) -> tuple[Optional[dict[str, Any]], dict[str, Any]]:
    creds = resolve_meta_template_credentials()
    if not creds.get("access_token"):
        out = _base_result(
            ok=False,
            operation=operation,
            trace_id=trace_id,
            status=STATUS_UNKNOWN,
            comparison=COMPARISON_ERROR,
            error_code="meta_access_token_missing",
            error_message_safe="meta_access_token_missing",
            extra={
                "waba_masked": creds.get("waba_masked"),
                "waba_source": creds.get("waba_source"),
                "credential_configured": False,
                "waba_configured": creds.get("waba_configured"),
            },
        )
        _log_op(
            operation=operation,
            template_name=TEMPLATE_NAME,
            waba_masked=str(creds.get("waba_masked") or "—"),
            status="failed",
            error_code="meta_access_token_missing",
            error_subcode=None,
            trace_id=trace_id,
        )
        return out, creds
    if not creds.get("waba_id"):
        out = _base_result(
            ok=False,
            operation=operation,
            trace_id=trace_id,
            status=STATUS_UNKNOWN,
            comparison=COMPARISON_ERROR,
            error_code="meta_waba_id_missing",
            error_message_safe="meta_waba_id_missing",
            extra={
                "waba_masked": "—",
                "waba_source": creds.get("waba_source"),
                "credential_configured": True,
                "waba_configured": False,
            },
        )
        _log_op(
            operation=operation,
            template_name=TEMPLATE_NAME,
            waba_masked="—",
            status="failed",
            error_code="meta_waba_id_missing",
            error_subcode=None,
            trace_id=trace_id,
        )
        return out, creds
    return None, creds


def _graph_get_templates(
    *,
    waba_id: str,
    access_token: str,
    name: Optional[str] = None,
    session: Optional[requests.Session] = None,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    url = template_endpoint_url(waba_id)
    params: dict[str, Any] = {
        "fields": "name,status,category,language,components,id",
        "limit": 100,
    }
    if name:
        params["name"] = name
    headers = {"Authorization": f"Bearer {access_token}"}
    http = session or requests
    try:
        resp = http.get(url, params=params, headers=headers, timeout=timeout)
    except requests.Timeout:
        return {"ok": False, "error_code": "provider_timeout", "templates": []}
    except requests.RequestException as exc:
        return {
            "ok": False,
            "error_code": "http_error",
            "error_message_safe": f"http_error:{type(exc).__name__}",
            "templates": [],
        }
    try:
        body = resp.json()
    except ValueError:
        return {"ok": False, "error_code": "invalid_json_response", "templates": []}
    if resp.status_code != 200:
        code, sub, msg = _safe_meta_error(body, resp.status_code)
        return {
            "ok": False,
            "error_code": code,
            "error_subcode": sub,
            "error_message_safe": msg,
            "templates": [],
        }
    data = body.get("data") if isinstance(body, dict) else None
    templates = [t for t in data if isinstance(t, dict)] if isinstance(data, list) else []
    if name:
        templates = [t for t in templates if str(t.get("name") or "") == name]
    return {"ok": True, "templates": templates}


def _graph_create_template(
    *,
    waba_id: str,
    access_token: str,
    payload: dict[str, Any],
    session: Optional[requests.Session] = None,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    url = template_endpoint_url(waba_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    http = session or requests
    try:
        resp = http.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.Timeout:
        return {"ok": False, "error_code": "provider_timeout", "error_message_safe": "provider_timeout"}
    except requests.RequestException as exc:
        return {
            "ok": False,
            "error_code": "http_error",
            "error_message_safe": f"http_error:{type(exc).__name__}",
        }
    try:
        body = resp.json()
    except ValueError:
        return {
            "ok": False,
            "error_code": "invalid_json_response",
            "error_message_safe": "invalid_json_response",
        }
    if resp.status_code not in (200, 201):
        code, sub, msg = _safe_meta_error(body, resp.status_code)
        return {
            "ok": False,
            "error_code": code,
            "error_subcode": sub,
            "error_message_safe": msg,
        }
    if not isinstance(body, dict):
        return {
            "ok": False,
            "error_code": "invalid_response_shape",
            "error_message_safe": "invalid_response_shape",
        }
    return {
        "ok": True,
        "template_id": str(body.get("id") or "") or None,
        "status": normalize_meta_template_status(str(body.get("status") or "PENDING")),
        "category": str(body.get("category") or TEMPLATE_CATEGORY),
    }


def _public_template_row(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "template_id": str(t.get("id") or "") or None,
        "template_name": str(t.get("name") or ""),
        "status": normalize_meta_template_status(str(t.get("status") or "")),
        "status_raw": str(t.get("status") or ""),
        "category": str(t.get("category") or ""),
        "language": str(t.get("language") or t.get("language_code") or ""),
    }


def list_meta_templates(
    *,
    session: Optional[requests.Session] = None,
) -> dict[str, Any]:
    trace_id = _new_trace_id()
    gated, creds = _cred_gate("list_templates", trace_id)
    if gated is not None:
        return gated

    fetched = _graph_get_templates(
        waba_id=str(creds["waba_id"]),
        access_token=str(creds["access_token"]),
        session=session,
    )
    if fetched.get("ok") is not True:
        out = _base_result(
            ok=False,
            operation="list_templates",
            trace_id=trace_id,
            status=STATUS_UNKNOWN,
            comparison=COMPARISON_ERROR,
            error_code=str(fetched.get("error_code") or "list_failed"),
            error_subcode=str(fetched.get("error_subcode") or "") or None,
            error_message_safe=str(fetched.get("error_message_safe") or "list_failed"),
            extra={
                "waba_masked": creds.get("waba_masked"),
                "waba_source": creds.get("waba_source"),
                "credential_configured": True,
                "waba_configured": True,
                "templates": [],
            },
        )
        _log_op(
            operation="list_templates",
            template_name="*",
            waba_masked=str(creds.get("waba_masked")),
            status="failed",
            error_code=out.get("error_code"),
            error_subcode=out.get("error_subcode"),
            trace_id=trace_id,
        )
        return out

    rows = [_public_template_row(t) for t in (fetched.get("templates") or [])]
    out = _base_result(
        ok=True,
        operation="list_templates",
        trace_id=trace_id,
        status="OK",
        comparison=COMPARISON_NOT_AVAILABLE,
        extra={
            "waba_masked": creds.get("waba_masked"),
            "waba_source": creds.get("waba_source"),
            "credential_configured": True,
            "waba_configured": True,
            "templates": rows,
            "count": len(rows),
        },
    )
    _log_op(
        operation="list_templates",
        template_name="*",
        waba_masked=str(creds.get("waba_masked")),
        status="ok",
        error_code=None,
        error_subcode=None,
        trace_id=trace_id,
    )
    return out


def get_recovery_template_status(
    *,
    session: Optional[requests.Session] = None,
) -> dict[str, Any]:
    """Inspect cartflow_cart_reminder_ar_v1 vs local contract."""
    trace_id = _new_trace_id()
    contract = local_contract_summary()
    gated, creds = _cred_gate("recovery_template_status", trace_id)
    if gated is not None:
        gated["local_contract"] = contract
        gated["comparison"] = COMPARISON_NOT_AVAILABLE
        gated["meta_connection_ok"] = False
        gated["can_create"] = False
        gated["exists"] = False
        return gated

    fetched = _graph_get_templates(
        waba_id=str(creds["waba_id"]),
        access_token=str(creds["access_token"]),
        name=TEMPLATE_NAME,
        session=session,
    )
    if fetched.get("ok") is not True:
        out = _base_result(
            ok=False,
            operation="recovery_template_status",
            trace_id=trace_id,
            status=STATUS_UNKNOWN,
            category=TEMPLATE_CATEGORY,
            language=TEMPLATE_LANGUAGE,
            comparison=COMPARISON_ERROR,
            error_code=str(fetched.get("error_code") or "lookup_failed"),
            error_subcode=str(fetched.get("error_subcode") or "") or None,
            error_message_safe=str(fetched.get("error_message_safe") or "lookup_failed"),
            extra={
                "waba_masked": creds.get("waba_masked"),
                "waba_source": creds.get("waba_source"),
                "credential_configured": True,
                "waba_configured": True,
                "local_contract": contract,
                "meta_connection_ok": False,
                "can_create": False,
            },
        )
        _log_op(
            operation="recovery_template_status",
            template_name=TEMPLATE_NAME,
            waba_masked=str(creds.get("waba_masked")),
            status="failed",
            error_code=out.get("error_code"),
            error_subcode=out.get("error_subcode"),
            trace_id=trace_id,
        )
        return out

    templates = fetched.get("templates") or []
    if not templates:
        out = _base_result(
            ok=True,
            operation="recovery_template_status",
            trace_id=trace_id,
            status=STATUS_NOT_CREATED,
            category=TEMPLATE_CATEGORY,
            language=TEMPLATE_LANGUAGE,
            comparison=COMPARISON_NOT_AVAILABLE,
            extra={
                "waba_masked": creds.get("waba_masked"),
                "waba_source": creds.get("waba_source"),
                "credential_configured": True,
                "waba_configured": True,
                "local_contract": contract,
                "meta_connection_ok": True,
                "exists": False,
                "can_create": True,
                "historical_template_name_v1": TEMPLATE_NAME_V1,
                "preserves_v1": True,
            },
        )
        _log_op(
            operation="recovery_template_status",
            template_name=TEMPLATE_NAME,
            waba_masked=str(creds.get("waba_masked")),
            status=STATUS_NOT_CREATED,
            error_code=None,
            error_subcode=None,
            trace_id=trace_id,
        )
        return out

    remote = templates[0]
    comparison = compare_remote_to_contract(remote)
    status = normalize_meta_template_status(str(remote.get("status") or ""))
    out = _base_result(
        ok=True,
        operation="recovery_template_status",
        trace_id=trace_id,
        template_id=str(remote.get("id") or "") or None,
        status=status,
        category=str(remote.get("category") or TEMPLATE_CATEGORY),
        language=str(remote.get("language") or TEMPLATE_LANGUAGE),
        comparison=comparison,
        extra={
            "waba_masked": creds.get("waba_masked"),
            "waba_source": creds.get("waba_source"),
            "credential_configured": True,
            "waba_configured": True,
            "local_contract": contract,
            "meta_connection_ok": True,
            "exists": True,
            "can_create": False,
            "status_raw": str(remote.get("status") or ""),
            "historical_template_name_v1": TEMPLATE_NAME_V1,
            "preserves_v1": True,
        },
    )
    _log_op(
        operation="recovery_template_status",
        template_name=TEMPLATE_NAME,
        waba_masked=str(creds.get("waba_masked")),
        status=f"{status}:{comparison}",
        error_code=None,
        error_subcode=None,
        trace_id=trace_id,
    )
    return out


def compare_recovery_template_contract(
    *,
    session: Optional[requests.Session] = None,
) -> dict[str, Any]:
    """Alias focused on comparison — same Graph lookup as status."""
    status = get_recovery_template_status(session=session)
    status["operation"] = "compare_recovery_template_contract"
    return status


def create_recovery_template(
    *,
    confirm: bool,
    template_name: str,
    session: Optional[requests.Session] = None,
) -> dict[str, Any]:
    """
    Create approved recovery template once.

    Requires confirm=True and exact template_name.
    Blocks if template already exists (SAME or DIFFERENT).
    """
    trace_id = _new_trace_id()
    name = (template_name or "").strip()
    if confirm is not True:
        return _base_result(
            ok=False,
            operation="create_recovery_template",
            trace_id=trace_id,
            error_code="confirmation_required",
            error_message_safe="confirmation_required",
            comparison=COMPARISON_NOT_AVAILABLE,
        )
    if name == TEMPLATE_NAME_V1:
        return _base_result(
            ok=False,
            operation="create_recovery_template",
            trace_id=trace_id,
            error_code="v1_immutable",
            error_message_safe="v1_immutable_never_overwrite_or_delete",
            comparison=COMPARISON_NOT_AVAILABLE,
            extra={"historical_template_name_v1": TEMPLATE_NAME_V1},
        )
    if name != TEMPLATE_NAME:
        return _base_result(
            ok=False,
            operation="create_recovery_template",
            trace_id=trace_id,
            error_code="template_name_mismatch",
            error_message_safe="template_name_mismatch",
            comparison=COMPARISON_NOT_AVAILABLE,
        )

    payload = build_template_payload()
    contract_errors = validate_template_contract(payload)
    if contract_errors:
        return _base_result(
            ok=False,
            operation="create_recovery_template",
            trace_id=trace_id,
            error_code="template_contract_invalid",
            error_message_safe=",".join(contract_errors),
            comparison=COMPARISON_ERROR,
            extra={"contract_errors": contract_errors},
        )

    gated, creds = _cred_gate("create_recovery_template", trace_id)
    if gated is not None:
        return gated

    fetched = _graph_get_templates(
        waba_id=str(creds["waba_id"]),
        access_token=str(creds["access_token"]),
        name=TEMPLATE_NAME,
        session=session,
    )
    if fetched.get("ok") is not True:
        out = _base_result(
            ok=False,
            operation="create_recovery_template",
            trace_id=trace_id,
            comparison=COMPARISON_ERROR,
            error_code=str(fetched.get("error_code") or "lookup_failed"),
            error_subcode=str(fetched.get("error_subcode") or "") or None,
            error_message_safe=str(fetched.get("error_message_safe") or "lookup_failed"),
            extra={
                "waba_masked": creds.get("waba_masked"),
                "waba_source": creds.get("waba_source"),
            },
        )
        _log_op(
            operation="create_recovery_template",
            template_name=TEMPLATE_NAME,
            waba_masked=str(creds.get("waba_masked")),
            status="lookup_failed",
            error_code=out.get("error_code"),
            error_subcode=out.get("error_subcode"),
            trace_id=trace_id,
        )
        return out

    existing = fetched.get("templates") or []
    if existing:
        remote = existing[0]
        comparison = compare_remote_to_contract(remote)
        status = normalize_meta_template_status(str(remote.get("status") or ""))
        out = _base_result(
            ok=False,
            operation="create_recovery_template",
            trace_id=trace_id,
            template_id=str(remote.get("id") or "") or None,
            status=status,
            category=str(remote.get("category") or TEMPLATE_CATEGORY),
            language=str(remote.get("language") or TEMPLATE_LANGUAGE),
            comparison=comparison,
            error_code="template_already_exists",
            error_message_safe=f"template_already_exists:{comparison}",
            extra={
                "waba_masked": creds.get("waba_masked"),
                "waba_source": creds.get("waba_source"),
                "created": False,
                "can_create": False,
            },
        )
        _log_op(
            operation="create_recovery_template",
            template_name=TEMPLATE_NAME,
            waba_masked=str(creds.get("waba_masked")),
            status=f"blocked_exists:{comparison}",
            error_code="template_already_exists",
            error_subcode=None,
            trace_id=trace_id,
        )
        return out

    created = _graph_create_template(
        waba_id=str(creds["waba_id"]),
        access_token=str(creds["access_token"]),
        payload=payload,
        session=session,
    )
    if created.get("ok") is not True:
        out = _base_result(
            ok=False,
            operation="create_recovery_template",
            trace_id=trace_id,
            comparison=COMPARISON_NOT_AVAILABLE,
            error_code=str(created.get("error_code") or "create_failed"),
            error_subcode=str(created.get("error_subcode") or "") or None,
            error_message_safe=str(created.get("error_message_safe") or "create_failed"),
            extra={
                "waba_masked": creds.get("waba_masked"),
                "waba_source": creds.get("waba_source"),
                "created": False,
            },
        )
        _log_op(
            operation="create_recovery_template",
            template_name=TEMPLATE_NAME,
            waba_masked=str(creds.get("waba_masked")),
            status="create_failed",
            error_code=out.get("error_code"),
            error_subcode=out.get("error_subcode"),
            trace_id=trace_id,
        )
        return out

    out = _base_result(
        ok=True,
        operation="create_recovery_template",
        trace_id=trace_id,
        template_id=created.get("template_id"),
        status=created.get("status") or STATUS_PENDING,
        category=created.get("category") or TEMPLATE_CATEGORY,
        language=TEMPLATE_LANGUAGE,
        comparison=COMPARISON_NOT_AVAILABLE,
        extra={
            "waba_masked": creds.get("waba_masked"),
            "waba_source": creds.get("waba_source"),
            "created": True,
            "note": "Graph accepted create — PENDING is not APPROVED",
        },
    )
    _log_op(
        operation="create_recovery_template",
        template_name=TEMPLATE_NAME,
        waba_masked=str(creds.get("waba_masked")),
        status=str(out.get("status")),
        error_code=None,
        error_subcode=None,
        trace_id=trace_id,
    )
    return out


__all__ = [
    "list_meta_templates",
    "get_recovery_template_status",
    "compare_recovery_template_contract",
    "create_recovery_template",
    "resolve_meta_template_credentials",
    "local_contract_summary",
]
