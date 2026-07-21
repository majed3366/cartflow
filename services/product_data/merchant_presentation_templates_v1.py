# -*- coding: utf-8 -*-
"""Merchant Presentation Foundation V1 — deterministic template registry."""
from __future__ import annotations

from typing import Any

from services.product_data.merchant_presentation_types_v1 import (
    LANGUAGE_CODE_V1,
    TEMPLATE_REGISTRY_VERSION_V1,
    TYPE_ABSTENTION,
    TYPE_DECISION_PROMPT,
    TYPE_EVIDENCE_GAP,
    TYPE_EXECUTIVE_SUMMARY,
    TYPE_MONITORING,
    TYPE_OPERATIONAL_NOTICE,
)


def _tpl(
    *,
    key: str,
    presentation_type: str,
    headline: str,
    primary: str,
    supporting: str,
    relevance: str,
    required: tuple[str, ...],
    optional: tuple[str, ...] = (),
    max_len: int = 280,
    version: str,
) -> dict[str, Any]:
    return {
        "template_key": key,
        "presentation_type": presentation_type,
        "language_code": LANGUAGE_CODE_V1,
        "headline_template": headline,
        "primary_template": primary,
        "supporting_template": supporting,
        "relevance_template": relevance,
        "required_variables": list(required),
        "optional_variables": list(optional),
        "prohibited_variables": ["root_cause", "revenue_impact", "discount_amount"],
        "fallback_behavior": "failed_missing_variable",
        "max_content_length": max_len,
        "template_version": version,
        "registry_version": TEMPLATE_REGISTRY_VERSION_V1,
        "active": True,
    }


TEMPLATE_REGISTRY_V1: dict[str, dict[str, Any]] = {
    "tpl_exec_investigate_v1": _tpl(
        key="tpl_exec_investigate_v1",
        presentation_type=TYPE_EXECUTIVE_SUMMARY,
        headline="Cart activity needs a closer look",
        primary=(
            "Some products are being added to carts without enough completed purchases."
        ),
        supporting="Review the path from cart to checkout when you have a moment.",
        relevance="Worth knowing now as an awareness summary.",
        required=(),
        version="mtpl_exec_investigate_v1",
    ),
    "tpl_decision_investigate_v1": _tpl(
        key="tpl_decision_investigate_v1",
        presentation_type=TYPE_DECISION_PROMPT,
        headline="Review the conversion path",
        primary=(
            "Cart intent is visible, but purchase completion is not yet established "
            "in the available evidence."
        ),
        supporting=(
            "Use the known facts below for review. The evidence does not identify "
            "a specific cause."
        ),
        relevance="This item needs merchant reasoning in the decision workspace.",
        required=(),
        version="mtpl_decision_investigate_v1",
    ),
    "tpl_ops_investigate_v1": _tpl(
        key="tpl_ops_investigate_v1",
        presentation_type=TYPE_OPERATIONAL_NOTICE,
        headline="Cart progression needs attention",
        primary=(
            "This product shows cart activity without enough completed purchases."
        ),
        supporting="Inspect the cart progression around this product.",
        relevance="Operational attention for carts.",
        required=(),
        version="mtpl_ops_investigate_v1",
    ),
    "tpl_monitor_v1": _tpl(
        key="tpl_monitor_v1",
        presentation_type=TYPE_MONITORING,
        headline="New pattern under observation",
        primary="A pattern has newly appeared. Continue observing before acting.",
        supporting="No commercial change is justified yet.",
        relevance="Monitoring only — no urgency.",
        required=(),
        version="mtpl_monitor_v1",
    ),
    "tpl_gap_v1": _tpl(
        key="tpl_gap_v1",
        presentation_type=TYPE_EVIDENCE_GAP,
        headline="Evidence is still limited",
        primary=(
            "A missing evidence area limits stronger commercial conclusions."
        ),
        supporting="Verify the gap before drawing a stronger conclusion.",
        relevance="Data completeness matters before stronger guidance.",
        required=(),
        version="mtpl_gap_v1",
    ),
    "tpl_abstain_v1": _tpl(
        key="tpl_abstain_v1",
        presentation_type=TYPE_ABSTENTION,
        headline="No reliable recommendation yet",
        primary="Evidence is not yet sufficient for commercial guidance.",
        supporting="Observation can continue without inventing a next action.",
        relevance="Calm status — not a platform failure.",
        required=(),
        version="mtpl_abstain_v1",
    ),
    "tpl_defer_v1": _tpl(
        key="tpl_defer_v1",
        presentation_type=TYPE_MONITORING,
        headline="Guidance deferred for more evidence",
        primary="Stronger commercial guidance is premature right now.",
        supporting="Defer action until additional evidence is available.",
        relevance="Deferred observation state.",
        required=(),
        version="mtpl_defer_v1",
    ),
    "tpl_continue_v1": _tpl(
        key="tpl_continue_v1",
        presentation_type=TYPE_MONITORING,
        headline="Continue observing",
        primary="A pattern exists, but it does not yet justify commercial change.",
        supporting="Keep observing calmly.",
        relevance="Awareness without urgency.",
        required=(),
        version="mtpl_continue_v1",
    ),
    "tpl_review_cart_ops_v1": _tpl(
        key="tpl_review_cart_ops_v1",
        presentation_type=TYPE_OPERATIONAL_NOTICE,
        headline="Review cart progression",
        primary="Customers are reaching the cart; completion behavior needs review.",
        supporting="Inspect cart progression without assuming a cause.",
        relevance="Operational carts attention.",
        required=(),
        version="mtpl_review_cart_ops_v1",
    ),
}


def get_template_v1(template_key: str) -> dict[str, Any] | None:
    entry = TEMPLATE_REGISTRY_V1.get(str(template_key or ""))
    if not entry or not entry.get("active"):
        return None
    return dict(entry)


def render_template_text_v1(template: str, variables: dict[str, str]) -> str:
    text = str(template or "")
    for key, value in sorted(variables.items()):
        text = text.replace("{" + key + "}", str(value))
    return text


def template_registry_valid_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not TEMPLATE_REGISTRY_V1:
        errors.append("empty_template_registry")
    for key, entry in TEMPLATE_REGISTRY_V1.items():
        if entry.get("template_key") != key:
            errors.append(f"key_mismatch:{key}")
        if not entry.get("template_version"):
            errors.append(f"missing_version:{key}")
    return (len(errors) == 0, errors)


__all__ = [
    "TEMPLATE_REGISTRY_V1",
    "get_template_v1",
    "render_template_text_v1",
    "template_registry_valid_v1",
]
