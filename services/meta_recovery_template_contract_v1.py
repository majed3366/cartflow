# -*- coding: utf-8 -*-
"""
Canonical Meta recovery template contract (CartFlow V1).

Single source of truth for:
- tools/meta/create_recovery_template_v1.py
- services/meta_template_operations_v1.py
- Meta send-time parameter mapping (store_name + checkout_url)

Template name remains cartflow_cart_reminder_ar_v1 (no new template name).
BODY text is frozen. BUTTONS: URL checkout + QUICK_REPLY support.
"""
from __future__ import annotations

import base64
import os
import re
from typing import Any, Optional
from urllib.parse import urlparse

from services.admin_whatsapp_meta_status_v1 import META_GRAPH_BASE, META_GRAPH_VERSION

TEMPLATE_NAME = "cartflow_cart_reminder_ar_v1"
TEMPLATE_LANGUAGE = "ar"
TEMPLATE_CATEGORY = "MARKETING"
TEMPLATE_BODY_TEXT = (
    "مرحبًا،\n\n"
    "لاحظنا أن لديك طلبًا لم يكتمل في {{1}}.\n\n"
    "سلتك ما زالت محفوظة، ويمكنك الرجوع لإكمال الطلب متى ما ناسبك."
)
# Body {{1}} — store display name (runtime: store_name)
TEMPLATE_STORE_NAME_EXAMPLE = "متجر الأمان"
# Backward-compatible alias
TEMPLATE_EXAMPLE_VALUE = TEMPLATE_STORE_NAME_EXAMPLE

BUTTON_URL_TEXT = "إكمال الشراء"
BUTTON_QUICK_REPLY_TEXT = "خدمة العملاء"
# Stable payload echoed on Meta button webhooks (send-time optional; match on text too)
BUTTON_QUICK_REPLY_PAYLOAD = "cartflow_customer_support_v1"

# Runtime semantic example for checkout_url (feeds URL button)
TEMPLATE_CHECKOUT_URL_EXAMPLE = "https://merchant.com/cart/restore/abc123"

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

# Body has one variable; URL button has one variable (separate Meta namespace).
META_RECOVERY_TEMPLATE_V1_BODY_PARAM_COUNT = 1


def public_base_url() -> str:
    raw = (
        (os.getenv("CARTFLOW_PUBLIC_BASE_URL") or "").strip()
        or (os.getenv("PUBLIC_BASE_URL") or "").strip()
        or "https://smartreplyai.net"
    )
    return raw.rstrip("/")


def button_checkout_url_with_variable() -> str:
    """
    Meta requires a fixed HTTPS prefix with {{1}} only at the end.
    CartFlow redirect resolves the variable to merchant checkout_url.
    """
    return public_base_url() + "/wa/checkout/{{1}}"


def encode_checkout_url_button_param(checkout_url: str) -> Optional[str]:
    """Encode full checkout_url as Meta URL-button {{1}} suffix (path-safe)."""
    u = (checkout_url or "").strip()
    if not u:
        return None
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    token = base64.urlsafe_b64encode(u.encode("utf-8")).decode("ascii").rstrip("=")
    if len(token) > 1800:
        return None
    return token


def decode_checkout_url_button_param(token: str) -> Optional[str]:
    """Decode URL-button path token back to checkout_url."""
    raw = (token or "").strip()
    if not raw or len(raw) > 2000:
        return None
    pad = "=" * ((4 - (len(raw) % 4)) % 4)
    try:
        decoded = base64.urlsafe_b64decode((raw + pad).encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    parsed = urlparse(decoded)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return decoded


def build_buttons_component() -> dict[str, Any]:
    from services.recovery_checkout_redirect_v1 import mint_checkout_redirect_token

    example_suffix = (
        mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="example_recovery",
            store_slug="example-store",
            template_name=TEMPLATE_NAME,
            provider="meta",
            now_ts=1_700_000_000,
        )
        or encode_checkout_url_button_param(TEMPLATE_CHECKOUT_URL_EXAMPLE)
        or "demo"
    )
    return {
        "type": "BUTTONS",
        "buttons": [
            {
                "type": "URL",
                "text": BUTTON_URL_TEXT,
                "url": button_checkout_url_with_variable(),
                "example": [example_suffix],
            },
            {
                "type": "QUICK_REPLY",
                "text": BUTTON_QUICK_REPLY_TEXT,
            },
        ],
    }


def build_template_payload() -> dict[str, Any]:
    """Approved template create payload: BODY + BUTTONS (URL + QUICK_REPLY)."""
    return {
        "name": TEMPLATE_NAME,
        "language": TEMPLATE_LANGUAGE,
        "category": TEMPLATE_CATEGORY,
        "components": [
            {
                "type": "BODY",
                "text": TEMPLATE_BODY_TEXT,
                "example": {
                    "body_text": [[TEMPLATE_STORE_NAME_EXAMPLE]],
                },
            },
            build_buttons_component(),
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
        "example_value": TEMPLATE_STORE_NAME_EXAMPLE,
        "store_name_example": TEMPLATE_STORE_NAME_EXAMPLE,
        "checkout_url_example": TEMPLATE_CHECKOUT_URL_EXAMPLE,
        "buttons": [
            {
                "type": "URL",
                "text": BUTTON_URL_TEXT,
                "url_template": button_checkout_url_with_variable(),
                "runtime_field": "checkout_url",
            },
            {
                "type": "QUICK_REPLY",
                "text": BUTTON_QUICK_REPLY_TEXT,
                "payload": BUTTON_QUICK_REPLY_PAYLOAD,
                "runtime_flag": "customer_requested_human_support",
            },
        ],
        "runtime_fields": ["store_name", "checkout_url"],
        "components": payload["components"],
        "forbidden": ["HEADER", "FOOTER", "media", "discounts", "dynamic_full_recovery_text"],
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
    if types.count("BODY") != 1:
        errors.append("expected_exactly_one_body_component")
    if types.count("BUTTONS") != 1:
        errors.append("expected_exactly_one_buttons_component")
    if len(components) != 2:
        errors.append("expected_body_and_buttons_only")

    body_components = [
        c
        for c in components
        if isinstance(c, dict) and str(c.get("type") or "").upper() == "BODY"
    ]
    if len(body_components) != 1:
        return errors

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
        and body_text_ex[0][0] == TEMPLATE_STORE_NAME_EXAMPLE
    ):
        errors.append("example_body_text_invalid")

    lowered = text.lower()
    if "http://" in lowered or "https://" in lowered or "www." in lowered:
        errors.append("url_forbidden_in_body")

    buttons_components = [
        c
        for c in components
        if isinstance(c, dict) and str(c.get("type") or "").upper() == "BUTTONS"
    ]
    if len(buttons_components) != 1:
        return errors

    buttons = buttons_components[0].get("buttons")
    if not isinstance(buttons, list) or len(buttons) != 2:
        errors.append("expected_exactly_two_buttons")
        return errors

    b0, b1 = buttons[0], buttons[1]
    if not isinstance(b0, dict) or not isinstance(b1, dict):
        errors.append("buttons_invalid_shape")
        return errors

    if str(b0.get("type") or "").upper() != "URL":
        errors.append("button1_must_be_url")
    if str(b0.get("text") or "") != BUTTON_URL_TEXT:
        errors.append("button1_text_mismatch")
    if str(b0.get("url") or "") != button_checkout_url_with_variable():
        errors.append("button1_url_mismatch")
    if "{{1}}" not in str(b0.get("url") or ""):
        errors.append("button1_url_missing_variable")

    if str(b1.get("type") or "").upper() != "QUICK_REPLY":
        errors.append("button2_must_be_quick_reply")
    if str(b1.get("text") or "") != BUTTON_QUICK_REPLY_TEXT:
        errors.append("button2_text_mismatch")

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
        elif ctype == "BUTTONS":
            buttons_in = c.get("buttons") if isinstance(c.get("buttons"), list) else []
            buttons_out: list[dict[str, Any]] = []
            for b in buttons_in:
                if not isinstance(b, dict):
                    continue
                btype = str(b.get("type") or "").upper()
                bout: dict[str, Any] = {
                    "type": btype,
                    "text": str(b.get("text") or ""),
                }
                if btype == "URL":
                    bout["url"] = str(b.get("url") or "")
                buttons_out.append(bout)
            entry["buttons"] = buttons_out
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
    if "HEADER" in types or "FOOTER" in types:
        return COMPARISON_DIFFERENT
    if types.count("BODY") != 1 or types.count("BUTTONS") != 1:
        return COMPARISON_DIFFERENT

    bodies = [c for c in comps if str(c.get("type") or "").upper() == "BODY"]
    if len(bodies) != 1:
        return COMPARISON_DIFFERENT
    if str(bodies[0].get("text") or "") != TEMPLATE_BODY_TEXT:
        return COMPARISON_DIFFERENT
    vars_found = re.findall(r"\{\{(\d+)\}\}", str(bodies[0].get("text") or ""))
    if vars_found != ["1"]:
        return COMPARISON_DIFFERENT

    buttons_comps = [c for c in comps if str(c.get("type") or "").upper() == "BUTTONS"]
    if len(buttons_comps) != 1:
        return COMPARISON_DIFFERENT
    buttons = buttons_comps[0].get("buttons") or []
    if len(buttons) != 2:
        return COMPARISON_DIFFERENT
    b0, b1 = buttons[0], buttons[1]
    if str(b0.get("type") or "").upper() != "URL":
        return COMPARISON_DIFFERENT
    if str(b0.get("text") or "") != BUTTON_URL_TEXT:
        return COMPARISON_DIFFERENT
    if str(b0.get("url") or "") != button_checkout_url_with_variable():
        return COMPARISON_DIFFERENT
    if str(b1.get("type") or "").upper() != "QUICK_REPLY":
        return COMPARISON_DIFFERENT
    if str(b1.get("text") or "") != BUTTON_QUICK_REPLY_TEXT:
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
        "ACTIVE": STATUS_APPROVED,
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


def is_customer_support_quick_reply(*, text: str = "", payload: str = "") -> bool:
    """True when inbound matches the support QUICK_REPLY button."""
    t = (text or "").strip()
    p = (payload or "").strip()
    if p and p == BUTTON_QUICK_REPLY_PAYLOAD:
        return True
    if t == BUTTON_QUICK_REPLY_TEXT:
        return True
    return False


__all__ = [
    "TEMPLATE_NAME",
    "TEMPLATE_LANGUAGE",
    "TEMPLATE_CATEGORY",
    "TEMPLATE_BODY_TEXT",
    "TEMPLATE_EXAMPLE_VALUE",
    "TEMPLATE_STORE_NAME_EXAMPLE",
    "TEMPLATE_CHECKOUT_URL_EXAMPLE",
    "BUTTON_URL_TEXT",
    "BUTTON_QUICK_REPLY_TEXT",
    "BUTTON_QUICK_REPLY_PAYLOAD",
    "META_RECOVERY_TEMPLATE_V1_BODY_PARAM_COUNT",
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
    "public_base_url",
    "button_checkout_url_with_variable",
    "encode_checkout_url_button_param",
    "decode_checkout_url_button_param",
    "build_buttons_component",
    "build_template_payload",
    "local_contract_summary",
    "validate_template_contract",
    "canonicalize_remote_template",
    "compare_remote_to_contract",
    "normalize_meta_template_status",
    "mask_waba_id",
    "template_endpoint_url",
    "is_customer_support_quick_reply",
]
