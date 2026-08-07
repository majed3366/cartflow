# -*- coding: utf-8 -*-
"""
Meta Dispatch Request Evidence V1 — sanitized wire-level capture.

Captures the outbound Graph payload immediately before HTTP POST.
Never stores access tokens, Authorization headers, or raw checkout tokens.
Does not alter send behavior.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

_LOCK = threading.Lock()
_LAST: Optional[dict[str, Any]] = None

_EVIDENCE_DIR = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "architecture"
    / "meta_dispatch_request_evidence_v1"
)

_TOKEN_LIKE = re.compile(r"^[A-Za-z0-9_\-]{20,}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask_recipient_e164(digits: str) -> str:
    """Mask to +966********11 style (keep country hint + last 2)."""
    d = "".join(c for c in str(digits or "") if c.isdigit())
    if not d:
        return ""
    if len(d) <= 4:
        return "+" + ("*" * len(d))
    # Prefer +CC********XX when starts with 966
    if d.startswith("966") and len(d) >= 5:
        return f"+966{'*' * max(1, len(d) - 5)}{d[-2:]}"
    return f"+{d[:3]}{'*' * max(1, len(d) - 5)}{d[-2:]}"


def _redact_param_text(text: str) -> str:
    t = str(text or "")
    if not t:
        return t
    # Checkout redirect tokens / JWT-ish / long opaque suffixes
    if "eyJ" in t or _TOKEN_LIKE.match(t) or len(t) > 40:
        return "[redacted]"
    return t


def _sanitize_components(components: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(components, list):
        return out
    for comp in components:
        if not isinstance(comp, dict):
            continue
        c = {
            "type": comp.get("type"),
            "sub_type": comp.get("sub_type"),
            "index": comp.get("index"),
        }
        params_in = comp.get("parameters")
        params_out: list[dict[str, Any]] = []
        if isinstance(params_in, list):
            for p in params_in:
                if not isinstance(p, dict):
                    continue
                po: dict[str, Any] = {"type": p.get("type")}
                if "text" in p:
                    po["text"] = _redact_param_text(str(p.get("text") or ""))
                if "payload" in p:
                    # Static quick-reply payload is non-secret contract id — keep
                    po["payload"] = str(p.get("payload") or "")[:128]
                params_out.append(po)
        c["parameters"] = params_out
        c["parameter_count"] = len(params_out)
        c["parameter_types"] = [str(x.get("type") or "") for x in params_out]
        out.append(c)
    return out


def _token_env_source() -> str:
    for key in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_API_TOKEN",
        "WHATSAPP_CLOUD_API_TOKEN",
        "META_WHATSAPP_TOKEN",
    ):
        if (os.getenv(key) or "").strip():
            return key
    return "none"


def _phone_id_env_source() -> str:
    for key in ("WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_PHONE_ID"):
        if (os.getenv(key) or "").strip():
            return key
    return "none"


def _waba_env_source() -> str:
    for key in ("WHATSAPP_BUSINESS_ACCOUNT_ID", "WABA_ID"):
        if (os.getenv(key) or "").strip():
            return key
    return "none"


def _meta_app_id() -> Optional[str]:
    for key in ("META_APP_ID", "WHATSAPP_APP_ID", "FACEBOOK_APP_ID"):
        v = (os.getenv(key) or "").strip()
        if v:
            return v[:64]
    return None


def _component_summary(sanitized_components: list[dict[str, Any]]) -> dict[str, Any]:
    body = next((c for c in sanitized_components if c.get("type") == "body"), None)
    url_btn = next(
        (
            c
            for c in sanitized_components
            if c.get("type") == "button" and c.get("sub_type") == "url"
        ),
        None,
    )
    qr_btn = next(
        (
            c
            for c in sanitized_components
            if c.get("type") == "button" and c.get("sub_type") == "quick_reply"
        ),
        None,
    )
    return {
        "body": {
            "present": body is not None,
            "parameter_count": (body or {}).get("parameter_count"),
            "parameter_types": (body or {}).get("parameter_types"),
            "sanitized_values": [
                p.get("text") for p in ((body or {}).get("parameters") or [])
            ],
        },
        "url_button": {
            "present": url_btn is not None,
            "index": (url_btn or {}).get("index"),
            "sub_type": (url_btn or {}).get("sub_type"),
            "parameter_count": (url_btn or {}).get("parameter_count"),
            "sanitized_values": [
                p.get("text") for p in ((url_btn or {}).get("parameters") or [])
            ],
        },
        "quick_reply": {
            "present": qr_btn is not None,
            "index": (qr_btn or {}).get("index"),
            "sub_type": (qr_btn or {}).get("sub_type"),
            "parameter_count": (qr_btn or {}).get("parameter_count"),
            "sanitized_values": [
                p.get("payload") or p.get("text")
                for p in ((qr_btn or {}).get("parameters") or [])
            ],
        },
    }


def verify_dispatch_evidence(
    evidence: dict[str, Any],
    *,
    expected_template: str = "cartflow_cart_reminder_ar_v2",
    expected_language: str = "ar",
    expected_body_param_count: int = 1,
) -> dict[str, Any]:
    req = evidence.get("request") if isinstance(evidence.get("request"), dict) else {}
    phone_id = str(evidence.get("resolved_phone_number_id") or "")
    endpoint = str(req.get("graph_endpoint") or "")
    tpl = req.get("template") if isinstance(req.get("template"), dict) else {}
    lang = tpl.get("language") if isinstance(tpl.get("language"), dict) else {}
    comps = req.get("template_components") if isinstance(req.get("template_components"), list) else []
    summary = _component_summary(comps)
    checks = {
        "phone_number_id_in_endpoint": bool(phone_id) and f"/{phone_id}/messages" in endpoint,
        "template_name_ok": str(tpl.get("name") or "") == expected_template,
        "language_ok": str(lang.get("code") or "") == expected_language,
        "body_param_count_ok": summary["body"].get("parameter_count")
        == expected_body_param_count,
        "url_button_present": bool(summary["url_button"].get("present")),
        "quick_reply_present": bool(summary["quick_reply"].get("present")),
        "provider_is_meta": str(evidence.get("resolved_whatsapp_provider") or "") == "meta",
    }
    return {"checks": checks, "all_passed": all(checks.values()), "component_summary": summary}


def sanitize_graph_response(body: Any, *, status_code: int) -> dict[str, Any]:
    """Safe Graph response snapshot — never tokens."""
    out: dict[str, Any] = {"http_status": int(status_code)}
    if not isinstance(body, dict):
        out["body_type"] = type(body).__name__
        return out
    if "messages" in body and isinstance(body.get("messages"), list):
        msgs = []
        for m in body["messages"][:3]:
            if isinstance(m, dict):
                msgs.append({"id": str(m.get("id") or "")[:80] or None})
        out["messages"] = msgs
        out["accepted"] = True
    err = body.get("error")
    if isinstance(err, dict):
        msg = str(err.get("message") or err.get("type") or "")[:300]
        if "access token" in msg.lower() or "oauth" in msg.lower():
            msg = "meta_auth_or_token_error"
        out["error"] = {
            "code": err.get("code"),
            "error_subcode": err.get("error_subcode"),
            "message_safe": msg,
            "fbtrace_id": str(err.get("fbtrace_id") or "")[:128] or None,
            "type": str(err.get("type") or "")[:64] or None,
        }
        out["accepted"] = False
    return out


def build_sanitized_dispatch_evidence(
    *,
    graph_endpoint: str,
    graph_version: str,
    phone_number_id: str,
    payload: dict[str, Any],
    resolved_whatsapp_provider: str = "meta",
    recovery_key: Optional[str] = None,
) -> dict[str, Any]:
    """Build sanitized evidence from the exact outbound URL + JSON body."""
    from services.admin_whatsapp_meta_status_v1 import read_whatsapp_meta_env  # noqa: PLC0415

    env = read_whatsapp_meta_env()
    pl = deepcopy(payload) if isinstance(payload, dict) else {}
    to_raw = str(pl.get("to") or "")
    tpl = pl.get("template") if isinstance(pl.get("template"), dict) else {}
    comps = _sanitize_components(tpl.get("components"))
    request_obj = {
        "graph_endpoint": str(graph_endpoint or "")[:500],
        "graph_version": str(graph_version or "")[:32],
        "phone_number_id": str(phone_number_id or "")[:64],
        "messaging_product": pl.get("messaging_product"),
        "recipient_type": pl.get("recipient_type"),  # often absent on Cloud API
        "to": mask_recipient_e164(to_raw),
        "type": pl.get("type"),
        "template": {
            "name": tpl.get("name"),
            "language": {"code": (tpl.get("language") or {}).get("code")}
            if isinstance(tpl.get("language"), dict)
            else tpl.get("language"),
        },
        "template_components": comps,
    }
    evidence: dict[str, Any] = {
        "captured_at": _utc_now(),
        "recovery_key": (recovery_key or "")[:120] or None,
        "resolved_whatsapp_provider": resolved_whatsapp_provider,
        "resolved_phone_number_id": str(phone_number_id or env.get("phone_number_id") or "")[
            :64
        ],
        "resolved_template_name": str(tpl.get("name") or "")[:128] or None,
        "resolved_waba_id": (env.get("waba_id") or None),
        "resolved_waba_source": _waba_env_source(),
        "resolved_token_env_key": _token_env_source(),
        "resolved_phone_number_id_source": _phone_id_env_source(),
        "meta_app_id": _meta_app_id(),
        "waba_id": (env.get("waba_id") or None),
        "graph_api_version": str(graph_version or "")[:32],
        "http_phone_number_id": str(phone_number_id or "")[:64],
        "http_template_name": str(tpl.get("name") or "")[:128] or None,
        "request": request_obj,
        "response": None,
    }
    evidence["verification"] = verify_dispatch_evidence(evidence)
    return evidence


def record_meta_dispatch_request(
    *,
    graph_endpoint: str,
    graph_version: str,
    phone_number_id: str,
    payload: dict[str, Any],
    recovery_key: Optional[str] = None,
) -> dict[str, Any]:
    """Store latest sanitized request evidence (pre-HTTP)."""
    evidence = build_sanitized_dispatch_evidence(
        graph_endpoint=graph_endpoint,
        graph_version=graph_version,
        phone_number_id=phone_number_id,
        payload=payload,
        recovery_key=recovery_key,
    )
    with _LOCK:
        global _LAST
        _LAST = evidence
    _try_write_files(evidence)
    return evidence


def record_meta_dispatch_response(
    *,
    status_code: int,
    body: Any,
) -> Optional[dict[str, Any]]:
    """Attach sanitized Graph response to the latest capture."""
    with _LOCK:
        global _LAST
        if not isinstance(_LAST, dict):
            return None
        updated = deepcopy(_LAST)
        updated["response"] = sanitize_graph_response(body, status_code=status_code)
        updated["response_captured_at"] = _utc_now()
        _LAST = updated
        out = deepcopy(updated)
    _try_write_files(out)
    return out


def get_last_meta_dispatch_evidence() -> Optional[dict[str, Any]]:
    with _LOCK:
        return deepcopy(_LAST) if isinstance(_LAST, dict) else None


def clear_meta_dispatch_evidence_for_tests() -> None:
    with _LOCK:
        global _LAST
        _LAST = None


def _try_write_files(evidence: dict[str, Any]) -> None:
    try:
        _EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        payload_path = _EVIDENCE_DIR / "request_payload.json"
        payload_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        summary = _render_summary_md(evidence)
        (_EVIDENCE_DIR / "request_summary.md").write_text(summary, encoding="utf-8")
    except OSError as exc:
        log.debug("meta dispatch evidence write skipped: %s", exc)


def _render_summary_md(evidence: dict[str, Any]) -> str:
    req = evidence.get("request") or {}
    tpl = req.get("template") or {}
    ver = evidence.get("verification") or {}
    checks = ver.get("checks") or {}
    resp = evidence.get("response") or {}
    lines = [
        "# Meta Dispatch Request Evidence V1",
        "",
        f"- captured_at: `{evidence.get('captured_at')}`",
        f"- recovery_key: `{evidence.get('recovery_key')}`",
        f"- provider: `{evidence.get('resolved_whatsapp_provider')}`",
        f"- phone_number_id: `{evidence.get('resolved_phone_number_id')}`",
        f"- template: `{tpl.get('name')}`",
        f"- language: `{(tpl.get('language') or {}).get('code')}`",
        f"- graph_endpoint: `{req.get('graph_endpoint')}`",
        f"- to (masked): `{req.get('to')}`",
        f"- verification_all_passed: `{ver.get('all_passed')}`",
        "",
        "## Checks",
        "",
    ]
    for k, v in checks.items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(["", "## Response", ""])
    if resp:
        lines.append(f"- http_status: `{resp.get('http_status')}`")
        if resp.get("error"):
            err = resp["error"]
            lines.append(f"- error.code: `{err.get('code')}`")
            lines.append(f"- error.error_subcode: `{err.get('error_subcode')}`")
            lines.append(f"- error.message_safe: `{err.get('message_safe')}`")
            lines.append(f"- error.fbtrace_id: `{err.get('fbtrace_id')}`")
        if resp.get("messages"):
            lines.append(f"- messages: `{resp.get('messages')}`")
    else:
        lines.append("- (none yet)")
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "build_sanitized_dispatch_evidence",
    "clear_meta_dispatch_evidence_for_tests",
    "get_last_meta_dispatch_evidence",
    "mask_recipient_e164",
    "record_meta_dispatch_request",
    "record_meta_dispatch_response",
    "sanitize_graph_response",
    "verify_dispatch_evidence",
]
