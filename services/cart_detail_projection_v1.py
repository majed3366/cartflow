# -*- coding: utf-8 -*-
"""
Cart Detail Projection v1 — presentation-only consumer of routed cart knowledge.

Routing owns eligibility and priority; Merchant Explanation owns narrative;
Decision Layer owns actions. This module prepares governed display blocks for UI.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.knowledge_routing_v1 import (
    ROUTING_VERSION,
    SURFACE_CART_DETAIL,
    route_cart_detail_knowledge_v1,
)
from services.merchant_daily_brief_v1 import _brief_action_ar
from services.merchant_decision_layer_v1 import LIFECYCLE_PUBLISHED, VERIFY_PASSED

PROJECTION_VERSION = "v1"

MODE_EXPLANATION = "explanation"
MODE_ARCHIVED = "archived"
MODE_LEGACY = "legacy"
MODE_UNAVAILABLE = "unavailable"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def _is_archived_row(row: Mapping[str, Any]) -> bool:
    if row.get("customer_lifecycle_is_archived_visual") is True:
        return True
    return _norm_lower(row.get("customer_lifecycle_state")) == "archived"


def _resolve_projection_mode(row: Mapping[str, Any]) -> str:
    if _is_archived_row(row):
        return MODE_ARCHIVED
    expl = row.get("merchant_explanation_v1")
    if isinstance(expl, Mapping) and _norm(expl.get("version")) == "v1":
        return MODE_EXPLANATION
    if _norm(row.get("customer_lifecycle_state")):
        return MODE_LEGACY
    return MODE_UNAVAILABLE


def _project_explanation_block(expl: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status_label_ar": _norm(expl.get("status_label_ar")),
        "what_happened_ar": _norm(expl.get("what_happened_ar")),
        "system_did_ar": _norm(expl.get("system_did_ar")),
        "what_next_ar": _norm(expl.get("what_next_ar")),
        "followup_line_ar": _norm(expl.get("followup_line_ar")),
        "merchant_action_needed_ar": _norm(expl.get("merchant_action_needed_ar")),
        "action_required": bool(expl.get("action_required")),
    }


def _project_legacy_explanation_block(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status_label_ar": _norm(row.get("customer_lifecycle_label_ar")),
        "what_happened_ar": _norm(row.get("customer_lifecycle_what_happened_ar")),
        "system_did_ar": _norm(row.get("customer_lifecycle_system_did_ar")),
        "what_next_ar": _norm(row.get("customer_lifecycle_what_next_ar")),
        "followup_line_ar": _norm(row.get("customer_lifecycle_next_followup_line_ar")),
        "merchant_action_needed_ar": _norm(row.get("customer_lifecycle_merchant_needed_ar")),
        "action_required": _norm(row.get("customer_lifecycle_merchant_needed_ar")) == "نعم",
    }


def _primary_routed_decision_payload(
    routed_feed: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    """Cart detail shows at most one primary routed decision (highest attention)."""
    attention = routed_feed.get("attention_items")
    if isinstance(attention, list) and attention:
        first = attention[0]
        if isinstance(first, Mapping):
            payload = first.get("knowledge_payload")
            if isinstance(payload, Mapping):
                return dict(payload)
    achievements = routed_feed.get("achievements")
    if isinstance(achievements, list) and achievements:
        first = achievements[0]
        if isinstance(first, Mapping):
            payload = first.get("knowledge_payload")
            if isinstance(payload, Mapping):
                return dict(payload)
    return None


def _project_suggested_action_v1(
    decision: Optional[Mapping[str, Any]],
    *,
    routed_item: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    if not isinstance(decision, Mapping):
        return {
            "visible": False,
            "label_ar": "",
            "decision_id": "",
            "action_key": "",
            "routing_priority": 0,
            "source_knowledge_id": "",
        }
    label = _brief_action_ar(decision)
    routing_priority = 0
    source_knowledge_id = _norm(decision.get("knowledge_id"))
    if isinstance(routed_item, Mapping):
        routing_priority = int(routed_item.get("routing_priority") or 0)
        pref = routed_item.get("producer_reference")
        if isinstance(pref, Mapping):
            source_knowledge_id = _norm(pref.get("representative_knowledge_id")) or source_knowledge_id
    return {
        "visible": bool(label),
        "label_ar": label,
        "decision_id": _norm(decision.get("decision_id")),
        "action_key": _norm(decision.get("action_key")),
        "routing_priority": routing_priority,
        "source_knowledge_id": source_knowledge_id,
    }


def _project_contact_action_v1(row: Mapping[str, Any]) -> dict[str, Any]:
    executable = bool(row.get("merchant_intervention_executable"))
    href = _norm(row.get("merchant_intervention_contact_href"))
    label = _norm(row.get("merchant_intervention_action_ar")) or "فتح واتساب"
    visible = executable and bool(href)
    return {
        "visible": visible,
        "href": href if visible else "",
        "label_ar": label if visible else "",
    }


def _project_lifecycle_ui_v1(row: Mapping[str, Any]) -> dict[str, Any]:
    rk = _norm(row.get("recovery_key"))
    act = _norm(row.get("customer_lifecycle_dashboard_action"))
    return {
        "recovery_key": rk,
        "archive_visible": bool(rk) and act == "archive",
        "reopen_visible": bool(rk) and act == "reopen",
    }


def _continuation_line_ar(row: Mapping[str, Any]) -> str:
    for key in (
        "customer_lifecycle_continuation_explanation_ar",
        "normal_recovery_continuation_explanation_ar",
    ):
        val = _norm(row.get(key))
        if val:
            return val
    return ""


def build_cart_detail_projection_v1(
    row: Mapping[str, Any],
    *,
    routed_feed: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Build cart_detail_projection_v1 display contract for one cart row."""
    mode = _resolve_projection_mode(row)
    expl = row.get("merchant_explanation_v1")
    decision_bundle = row.get("merchant_decisions_v1")

    if routed_feed is None:
        routed_feed = route_cart_detail_knowledge_v1(
            explanation=expl if isinstance(expl, Mapping) else None,
            decision_bundle=decision_bundle if isinstance(decision_bundle, Mapping) else None,
        )

    routed_item: Optional[Mapping[str, Any]] = None
    attention = routed_feed.get("attention_items")
    if isinstance(attention, list) and attention and isinstance(attention[0], Mapping):
        routed_item = attention[0]
    elif isinstance(routed_feed.get("achievements"), list) and routed_feed["achievements"]:
        first = routed_feed["achievements"][0]
        if isinstance(first, Mapping):
            routed_item = first

    decision_payload = _primary_routed_decision_payload(routed_feed)

    if mode == MODE_EXPLANATION and isinstance(expl, Mapping):
        explanation_block = _project_explanation_block(expl)
    elif mode == MODE_LEGACY:
        explanation_block = _project_legacy_explanation_block(row)
    elif mode == MODE_ARCHIVED:
        explanation_block = {
            "status_label_ar": "مؤرشفة",
            "what_happened_ar": "",
            "system_did_ar": "",
            "what_next_ar": "",
            "followup_line_ar": "",
            "merchant_action_needed_ar": "",
            "action_required": False,
        }
    else:
        explanation_block = {
            "status_label_ar": "— لا تتوفر حالة واضحة بعد —",
            "what_happened_ar": "",
            "system_did_ar": "",
            "what_next_ar": "",
            "followup_line_ar": "",
            "merchant_action_needed_ar": "",
            "action_required": False,
        }

    suggested = _project_suggested_action_v1(decision_payload, routed_item=routed_item)

    return {
        "version": PROJECTION_VERSION,
        "surface": SURFACE_CART_DETAIL,
        "routing_version": ROUTING_VERSION,
        "mode": mode,
        "explanation": explanation_block,
        "suggested_action": suggested,
        "contact_action": _project_contact_action_v1(row),
        "lifecycle_ui": _project_lifecycle_ui_v1(row),
        "continuation_line_ar": _continuation_line_ar(row),
        "followup_progress_ar": _norm(row.get("merchant_followup_progress_ar")),
        "knowledge_routing_v1": routed_feed,
        "observability": {
            "mode": mode,
            "routed_attention_groups": len(routed_feed.get("attention_items") or []),
            "routed_achievement_groups": len(routed_feed.get("achievements") or []),
            "primary_decision_published": bool(
                isinstance(decision_payload, Mapping)
                and _norm(decision_payload.get("lifecycle_state")) == LIFECYCLE_PUBLISHED
                and _norm(decision_payload.get("verification_status")) == VERIFY_PASSED
            ),
        },
    }


def attach_cart_detail_projection_v1(
    target: Mapping[str, Any] | dict[str, Any],
) -> None:
    """Attach cart detail projection to a normal-carts row (additive)."""
    if not isinstance(target, dict):
        return
    target["cart_detail_projection_v1"] = build_cart_detail_projection_v1(target)


__all__ = [
    "PROJECTION_VERSION",
    "MODE_ARCHIVED",
    "MODE_EXPLANATION",
    "MODE_LEGACY",
    "MODE_UNAVAILABLE",
    "attach_cart_detail_projection_v1",
    "build_cart_detail_projection_v1",
]
