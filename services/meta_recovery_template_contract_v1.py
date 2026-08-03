# -*- coding: utf-8 -*-
"""
Canonical Meta recovery template contract (CartFlow V1).

Single source of truth for:
- tools/meta/create_recovery_template_v1.py
- services/meta_template_operations_v1.py
"""
from __future__ import annotations

import re
from typing import Any, Optional

from services.admin_whatsapp_meta_status_v1 import META_GRAPH_BASE, META_GRAPH_VERSION

TEMPLATE_NAME = "cartflow_cart_reminder_ar_v1"
TEMPLATE_LANGUAGE = "ar"
TEMPLATE_CATEGORY = "MARKETING"
TEMPLATE_BODY_TEXT = (
    "مرحبًا،\n\n"
    "لاحظنا أن لديك طلبًا لم يكتمل في {{1}}.\n\n"
    "سلتك ما زالت محفوظة، ويمكنك الرجوع لإكمال الطلب متى ما ناسبك."
)
TEMPLATE_EXAMPLE_VALUE = "متجر الأمان"

COMPARISON_SAME = "SAME"
COMPARISON_DIFFERENT = "DIFFERENT"
COMPARISON_NOT_AVAILABLE = "NOT_AVAILABLE"
COMPARISON_ERROR = "ERROR"

STATUS_NOT_CREATED = "NOT_CREATED"
STATUS_PENDING = "PENDING"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_PAUSED = "PAUSED"
STATUS_DISABLED = "DISABLED"
STATUS_UNKNOWN = "UNKNOWN"

HTTP_TIMEOUT_SECONDS = 30.0


def build_template_payload() -> dict[str, Any]:
    """Exact approved template create payload (BODY only)."""
    return {
        "name": TEMPLATE_NAME,
        "language": TEMPLATE_LANGUAGE,
        "category": TEMPLATE_CATEGORY,
        "components": [
            {
                "type": "BODY",
                "text": TEMPLATE_BODY_TEXT,
                "example": {
                    "body_text": [[TEMPLATE_EXAMPLE_VALUE]],
                },
            }
        ],
    }


def local_contract_summary() -> dict[str, Any]:
    """Safe local contract view for admin UI (no secrets)."""
    payload = build_template_payload()
    return {
        "template_name": TEMPLATE_NAME,
        "language": TEMPLATE_LANGUAGE,
        "category": TEMPLATE_CATEGORY,
        "body_text": TEMPLATE_BODY_TEXT,
        "example_value": TEMPLATE_EXAMPLE_VALUE,
        "components": payload["components"],
        "forbidden": ["HEADER", "FOOTER", "buttons", "media", "URLs", "discounts"],
        "graph_version": META_GRAPH_VERSION,
    }


def validate_template_contract(payload: dict[str, Any]) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload_not_object"]

    if payload.get("name") != TEMPLATE_NAME:
        errors.append("template_name_mismatch")
    if payload.get("language") != TEMPLATE_LANGUAGE:
        errors.append("language_mismatch")
    if payload.get("category") != TEMPLATE_CATEGORY:
        errors.append("category_mismatch")

    components = payload.get("components")
    if not isinstance(components, list) or not components:
        errors.append("components_missing")
        return errors

    types = [str(c.get("type") or "").upper() for c in components if isinstance(c, dict)]
    if any(t == "HEADER" for t in types):
        errors.append("header_component_forbidden")
    if any(t == "FOOTER" for t in types):
        errors.append("footer_component_forbidden")
    if any(t == "BUTTONS" for t in types):
        errors.append("buttons_component_forbidden")

    body_components = [
        c
        for c in components
        if isinstance(c, dict) and str(c.get("type") or "").upper() == "BODY"
    ]
    if len(body_components) != 1:
        errors.append("expected_exactly_one_body_component")
        return errors
    if len(components) != 1:
        errors.append("expected_body_only_components")

    body = body_components[0]
    text = str(body.get("text") or "")
    if text != TEMPLATE_BODY_TEXT:
        errors.append("body_text_mismatch")

    vars_found = re.findall(r"\{\{(\d+)\}\}", text)
    if vars_found != ["1"]:
        errors.append("expected_exactly_one_body_variable_1")

    example = body.get("example") if isinstance(body.get("example"), dict) else {}
    body_text_ex = example.get("body_text") if isinstance(example, dict) else None
    if not (
        isinstance(body_text_ex, list)
        and len(body_text_ex) == 1
        and isinstance(body_text_ex[0], list)
        and len(body_text_ex[0]) == 1
        and body_text_ex[0][0] == TEMPLATE_EXAMPLE_VALUE
    ):
        errors.append("example_body_text_invalid")

    lowered = text.lower()
    if "http://" in lowered or "https://" in lowered or "www." in lowered:
        errors.append("url_forbidden_in_body")

    return errors


def canonicalize_remote_template(remote: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Graph template object for contract comparison."""
    components_in = (
        remote.get("components") if isinstance(remote.get("components"), list) else []
    )
    components_out: list[dict[str, Any]] = []
    for c in components_in:
        if not isinstance(c, dict):
            continue
        ctype = str(c.get("type") or "").upper()
        entry: dict[str, Any] = {"type": ctype}
        if ctype == "BODY":
            entry["text"] = str(c.get("text") or "")
            ex = c.get("example")
            if isinstance(ex, dict) and ex.get("body_text") is not None:
                entry["example"] = ex
        components_out.append(entry)
    return {
        "name": str(remote.get("name") or ""),
        "language": str(remote.get("language") or remote.get("language_code") or ""),
        "category": str(remote.get("category") or "").upper(),
        "components": components_out,
    }


def compare_remote_to_contract(remote: dict[str, Any]) -> str:
    """Return SAME / DIFFERENT for an existing template vs approved contract."""
    canon = canonicalize_remote_template(remote)
    expected = build_template_payload()
    if canon.get("name") != expected["name"]:
        return COMPARISON_DIFFERENT
    if canon.get("language") != expected["language"]:
        return COMPARISON_DIFFERENT
    if canon.get("category") != expected["category"]:
        return COMPARISON_DIFFERENT

    comps = canon.get("components") or []
    types = [str(c.get("type") or "").upper() for c in comps]
    if "HEADER" in types or "FOOTER" in types or "BUTTONS" in types:
        return COMPARISON_DIFFERENT
    bodies = [c for c in comps if str(c.get("type") or "").upper() == "BODY"]
    if len(bodies) != 1:
        return COMPARISON_DIFFERENT
    if str(bodies[0].get("text") or "") != TEMPLATE_BODY_TEXT:
        return COMPARISON_DIFFERENT
    vars_found = re.findall(r"\{\{(\d+)\}\}", str(bodies[0].get("text") or ""))
    if vars_found != ["1"]:
        return COMPARISON_DIFFERENT
    return COMPARISON_SAME


def normalize_meta_template_status(raw: Optional[str]) -> str:
    """Normalize Meta template status to CartFlow vocabulary."""
    if raw is None or str(raw).strip() == "":
        return STATUS_UNKNOWN
    s = str(raw).strip().upper()
    mapping = {
        "PENDING": STATUS_PENDING,
        "IN_APPEAL": STATUS_PENDING,
        "APPROVED": STATUS_APPROVED,
        "REJECTED": STATUS_REJECTED,
        "PAUSED": STATUS_PAUSED,
        "DISABLED": STATUS_DISABLED,
        "FLAGGED": STATUS_DISABLED,
    }
    return mapping.get(s, STATUS_UNKNOWN)


def mask_waba_id(waba_id: str) -> str:
    digits = (waba_id or "").strip()
    if not digits:
        return "—"
    if len(digits) <= 6:
        return "****"
    return f"{digits[:3]}…{digits[-3:]}"


def template_endpoint_url(waba_id: str) -> str:
    return f"{META_GRAPH_BASE}/{waba_id}/message_templates"


__all__ = [
    "TEMPLATE_NAME",
    "TEMPLATE_LANGUAGE",
    "TEMPLATE_CATEGORY",
    "TEMPLATE_BODY_TEXT",
    "TEMPLATE_EXAMPLE_VALUE",
    "COMPARISON_SAME",
    "COMPARISON_DIFFERENT",
    "COMPARISON_NOT_AVAILABLE",
    "COMPARISON_ERROR",
    "STATUS_NOT_CREATED",
    "STATUS_PENDING",
    "STATUS_APPROVED",
    "STATUS_REJECTED",
    "STATUS_PAUSED",
    "STATUS_DISABLED",
    "STATUS_UNKNOWN",
    "HTTP_TIMEOUT_SECONDS",
    "META_GRAPH_BASE",
    "META_GRAPH_VERSION",
    "build_template_payload",
    "local_contract_summary",
    "validate_template_contract",
    "canonicalize_remote_template",
    "compare_remote_to_contract",
    "normalize_meta_template_status",
    "mask_waba_id",
    "template_endpoint_url",
]
