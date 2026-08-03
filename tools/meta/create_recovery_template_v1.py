# -*- coding: utf-8 -*-
"""
Controlled tool: submit CartFlow Arabic recovery WhatsApp template via Meta Graph API.

Default mode is DRY RUN (no HTTP). Real submission requires explicit --execute.

Contract source of truth: services/meta_recovery_template_contract_v1.py
Does not send WhatsApp messages. Does not switch WHATSAPP_PROVIDER.
Never logs access tokens or Authorization headers.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

import requests

from services.meta_recovery_template_contract_v1 import (
    COMPARISON_DIFFERENT,
    COMPARISON_SAME,
    HTTP_TIMEOUT_SECONDS,
    META_GRAPH_BASE,
    TEMPLATE_BODY_TEXT,
    TEMPLATE_CATEGORY,
    TEMPLATE_EXAMPLE_VALUE,
    TEMPLATE_LANGUAGE,
    TEMPLATE_NAME,
    build_template_payload,
    canonicalize_remote_template,
    compare_remote_to_contract,
    mask_waba_id,
    template_endpoint_url,
    validate_template_contract,
)


def resolve_access_token() -> Optional[str]:
    """CLI tool: WHATSAPP_ACCESS_TOKEN only (explicit ops contract)."""
    tok = (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip()
    if not tok or tok.lower() in ("your_token", "changeme", "placeholder"):
        return None
    return tok


def resolve_waba_id() -> tuple[Optional[str], str]:
    primary = (os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID") or "").strip()
    if primary and primary.lower() not in ("your_id", "changeme", "placeholder"):
        return primary, "WHATSAPP_BUSINESS_ACCOUNT_ID"
    legacy = (os.getenv("WABA_ID") or "").strip()
    if legacy and legacy.lower() not in ("your_id", "changeme", "placeholder"):
        return legacy, "WABA_ID"
    return None, "missing"


def template_create_url(waba_id: str) -> str:
    return template_endpoint_url(waba_id)


def template_list_url(waba_id: str) -> str:
    return template_endpoint_url(waba_id)


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


def _result(
    *,
    ok: bool,
    template_id: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    error_code: Optional[str] = None,
    error_subcode: Optional[str] = None,
    error_message_safe: Optional[str] = None,
    dry_run: bool = False,
    existing_comparison: Optional[str] = None,
    waba_source: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": bool(ok),
        "template_id": template_id,
        "status": status,
        "category": category or TEMPLATE_CATEGORY,
        "error_code": error_code,
        "error_subcode": error_subcode,
        "error_message_safe": error_message_safe,
        "dry_run": bool(dry_run),
        "template_name": TEMPLATE_NAME,
        "language": TEMPLATE_LANGUAGE,
        "existing_comparison": existing_comparison,
        "waba_source": waba_source,
    }
    if extra:
        out.update(extra)
    for k in list(out.keys()):
        if "token" in k.lower() or "authorization" in k.lower():
            out.pop(k, None)
    return out


def fetch_templates_by_name(
    *,
    waba_id: str,
    access_token: str,
    name: str,
    session: Optional[requests.Session] = None,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    url = template_list_url(waba_id)
    params = {
        "name": name,
        "fields": "name,status,category,language,components,id",
    }
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
    templates = [t for t in templates if str(t.get("name") or "") == name]
    return {"ok": True, "templates": templates}


def submit_template_create(
    *,
    waba_id: str,
    access_token: str,
    payload: dict[str, Any],
    session: Optional[requests.Session] = None,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    url = template_create_url(waba_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    http = session or requests
    try:
        resp = http.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.Timeout:
        return _result(
            ok=False,
            error_code="provider_timeout",
            error_message_safe="provider_timeout",
        )
    except requests.RequestException as exc:
        return _result(
            ok=False,
            error_code="http_error",
            error_message_safe=f"http_error:{type(exc).__name__}",
        )

    try:
        body = resp.json()
    except ValueError:
        return _result(
            ok=False,
            error_code="invalid_json_response",
            error_message_safe="invalid_json_response",
        )

    if resp.status_code not in (200, 201):
        code, sub, msg = _safe_meta_error(body, resp.status_code)
        return _result(
            ok=False,
            error_code=code,
            error_subcode=sub,
            error_message_safe=msg,
        )

    if not isinstance(body, dict):
        return _result(
            ok=False,
            error_code="invalid_response_shape",
            error_message_safe="invalid_response_shape",
        )

    template_id = body.get("id")
    status = body.get("status")
    category = body.get("category") or TEMPLATE_CATEGORY
    return _result(
        ok=True,
        template_id=str(template_id) if template_id is not None else None,
        status=str(status) if status is not None else "PENDING",
        category=str(category),
    )


def run_create_recovery_template(
    *,
    execute: bool = False,
    session: Optional[requests.Session] = None,
) -> dict[str, Any]:
    payload = build_template_payload()
    contract_errors = validate_template_contract(payload)
    if contract_errors:
        return _result(
            ok=False,
            dry_run=not execute,
            error_code="template_contract_invalid",
            error_message_safe=",".join(contract_errors),
            extra={"contract_errors": contract_errors},
        )

    waba_id, waba_source = resolve_waba_id()
    token = resolve_access_token()

    if not execute:
        endpoint = (
            template_create_url(waba_id)
            if waba_id
            else f"{META_GRAPH_BASE}/{{WABA_ID}}/message_templates"
        )
        masked_endpoint = (
            template_create_url(mask_waba_id(waba_id)) if waba_id else endpoint
        )
        print("[META TEMPLATE DRY RUN]", flush=True)
        print(f"endpoint={masked_endpoint}", flush=True)
        print(f"waba_source={waba_source}", flush=True)
        print(f"waba_id_masked={mask_waba_id(waba_id) if waba_id else 'missing'}", flush=True)
        print(f"template_name={TEMPLATE_NAME}", flush=True)
        print(f"language={TEMPLATE_LANGUAGE}", flush=True)
        print(f"category={TEMPLATE_CATEGORY}", flush=True)
        print("payload=", flush=True)
        print(json.dumps(payload, ensure_ascii=True, indent=2), flush=True)
        print("access_token=REDACTED", flush=True)
        print("execute=false (pass --execute to submit)", flush=True)
        return _result(
            ok=True,
            dry_run=True,
            status="DRY_RUN",
            waba_source=waba_source,
            extra={
                "endpoint_masked": masked_endpoint,
                "payload": payload,
                "credential_configured": bool(token),
                "waba_configured": bool(waba_id),
            },
        )

    if not token:
        return _result(
            ok=False,
            dry_run=False,
            error_code="meta_access_token_missing",
            error_message_safe="meta_access_token_missing",
            waba_source=waba_source,
        )
    if not waba_id:
        return _result(
            ok=False,
            dry_run=False,
            error_code="meta_waba_id_missing",
            error_message_safe="meta_waba_id_missing",
            waba_source=waba_source,
        )

    existing = fetch_templates_by_name(
        waba_id=waba_id,
        access_token=token,
        name=TEMPLATE_NAME,
        session=session,
    )
    if existing.get("ok") is not True:
        return _result(
            ok=False,
            dry_run=False,
            error_code=str(existing.get("error_code") or "template_lookup_failed"),
            error_subcode=str(existing.get("error_subcode") or "") or None,
            error_message_safe=str(
                existing.get("error_message_safe") or "template_lookup_failed"
            ),
            waba_source=waba_source,
        )

    templates = existing.get("templates") or []
    if templates:
        remote = templates[0]
        comparison = compare_remote_to_contract(remote)
        print("[META TEMPLATE EXISTS]", flush=True)
        print(f"template_name={TEMPLATE_NAME}", flush=True)
        print(f"comparison={comparison}", flush=True)
        print(f"remote_status={remote.get('status')}", flush=True)
        print("action=STOP (no delete/overwrite)", flush=True)
        return _result(
            ok=False,
            dry_run=False,
            template_id=str(remote.get("id") or "") or None,
            status=str(remote.get("status") or "EXISTS"),
            category=str(remote.get("category") or TEMPLATE_CATEGORY),
            error_code="template_already_exists",
            error_message_safe=f"template_already_exists:{comparison}",
            existing_comparison=comparison,
            waba_source=waba_source,
        )

    created = submit_template_create(
        waba_id=waba_id,
        access_token=token,
        payload=payload,
        session=session,
    )
    created["dry_run"] = False
    created["waba_source"] = waba_source
    return created


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create CartFlow Meta recovery template cartflow_cart_reminder_ar_v1. "
            "Default is dry-run; pass --execute to submit."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually POST the template to Meta Graph API (default: dry-run).",
    )
    args = parser.parse_args(argv)
    result = run_create_recovery_template(execute=bool(args.execute))
    safe = {
        k: result.get(k)
        for k in (
            "ok",
            "dry_run",
            "template_name",
            "language",
            "category",
            "status",
            "template_id",
            "error_code",
            "error_subcode",
            "error_message_safe",
            "existing_comparison",
            "waba_source",
            "endpoint_masked",
            "credential_configured",
            "waba_configured",
            "contract_errors",
            "payload",
        )
        if k in result and result.get(k) is not None
    }
    print(json.dumps(safe, ensure_ascii=True, indent=2), flush=True)
    if result.get("dry_run") is True:
        return 0
    return 0 if result.get("ok") is True else 2 if result.get("error_code") == "template_already_exists" else 1


if __name__ == "__main__":
    sys.exit(main())
