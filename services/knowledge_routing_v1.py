# -*- coding: utf-8 -*-
"""
Knowledge Routing v1 — platform-owned routing layer (domain-neutral).

Consumes standardized published knowledge items only.
Assigns routing_priority, surface eligibility, aggregation, and lifetime.
Does not create truth, decisions, explanations, or business-domain rules.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional

from services.knowledge_producer_metadata_v1 import (
    NARRATIVE_ACHIEVEMENT,
    NARRATIVE_ATTENTION,
    NARRATIVE_CLOSURE,
    NARRATIVE_TREND,
    validate_knowledge_metadata_v1,
)
from services.merchant_daily_brief_v1 import MAX_BRIEF_ITEMS

ROUTING_VERSION = "v1"

SURFACE_DAILY_BRIEF = "daily_brief"
SURFACE_CART_DETAIL = "cart_detail"
SURFACE_KNOWLEDGE_LAYER = "knowledge_layer"
SURFACE_MERCHANT_HOME = "merchant_home"

SECTION_ACHIEVEMENT = "achievement"
SECTION_ATTENTION = "attention"

_ATTENTION_RANK = {
    "urgent": 400,
    "attention": 300,
    "informational": 200,
    "none": 100,
}
_CONFIDENCE_RANK = {
    "high": 30,
    "medium": 20,
    "low": 10,
    "insufficient": 0,
}
_NARRATIVE_RANK = {
    NARRATIVE_ATTENTION: 50,
    NARRATIVE_ACHIEVEMENT: 40,
    NARRATIVE_TREND: 30,
    "fact": 20,
    NARRATIVE_CLOSURE: 10,
    "diagnostic": 5,
}

_AGGREGATION_REASON = "routing:aggregation_key+narrative_role+surface"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _norm_lower(value) in ("true", "1", "yes", "merchant_dashboard")


def is_published_knowledge_item(item: Mapping[str, Any]) -> bool:
    """Item conforms to producer metadata contract (routing input gate)."""
    return not validate_knowledge_metadata_v1(item)


def compute_routing_priority_v1(item: Mapping[str, Any]) -> int:
    """
    Deterministic platform priority from metadata only — no domain branching.
    """
    attn = _ATTENTION_RANK.get(_norm_lower(item.get("attention_level")), 100)
    conf = _CONFIDENCE_RANK.get(_norm_lower(item.get("confidence")), 0)
    role = _NARRATIVE_RANK.get(_norm_lower(item.get("narrative_role")), 0)
    return int(attn + conf + role)


def assign_routing_section_v1(item: Mapping[str, Any]) -> str:
    """
    Map item to brief section using narrative_role + attention_level metadata only.
    """
    role = _norm_lower(item.get("narrative_role"))
    attn = _norm_lower(item.get("attention_level"))
    if role in (NARRATIVE_ATTENTION, "diagnostic"):
        return SECTION_ATTENTION
    if role in (NARRATIVE_ACHIEVEMENT, NARRATIVE_CLOSURE, NARRATIVE_TREND):
        return SECTION_ACHIEVEMENT
    if attn in ("urgent", "attention"):
        return SECTION_ATTENTION
    if bool(item.get("action_required")):
        return SECTION_ATTENTION
    return SECTION_ACHIEVEMENT


def is_surface_eligible_v1(item: Mapping[str, Any], surface: str) -> bool:
    surfaces = item.get("eligible_surfaces")
    if not isinstance(surfaces, list):
        return False
    normalized = {_norm_lower(s) for s in surfaces}
    return _norm_lower(surface) in normalized


def is_merchant_visible_v1(item: Mapping[str, Any]) -> bool:
    return _as_bool(item.get("merchant_visibility"))


def extract_knowledge_items_from_decision_bundles_v1(
    bundles: Iterable[Mapping[str, Any] | None],
) -> list[dict[str, Any]]:
    """Collect standardized decision knowledge items from merchant_decisions_v1 bundles."""
    out: list[dict[str, Any]] = []
    for bundle in bundles:
        if not isinstance(bundle, Mapping):
            continue
        decisions = bundle.get("decisions")
        if not isinstance(decisions, list):
            continue
        for raw in decisions:
            if not isinstance(raw, Mapping):
                continue
            if not _norm(raw.get("knowledge_id")):
                continue
            if not is_published_knowledge_item(raw):
                continue
            item = dict(raw)
            item.setdefault("producer", "merchant_decision_layer_v1")
            out.append(item)
    return out


def extract_knowledge_items_from_kl_insights_v1(
    insights: Iterable[Mapping[str, Any] | None],
) -> list[dict[str, Any]]:
    """Collect standardized insight knowledge items."""
    out: list[dict[str, Any]] = []
    for raw in insights or []:
        if not isinstance(raw, Mapping):
            continue
        if not _norm(raw.get("knowledge_id")):
            continue
        if not is_published_knowledge_item(raw):
            continue
        item = dict(raw)
        item.setdefault("producer", "knowledge_layer_v1")
        out.append(item)
    return out


def collect_routing_input_items_v1(
    *,
    decision_bundles: Iterable[Mapping[str, Any] | None] = (),
    kl_insights: Iterable[Mapping[str, Any] | None] = (),
) -> list[dict[str, Any]]:
    """Merge routing inputs from supported producers (dedupe by knowledge_id)."""
    merged: dict[str, dict[str, Any]] = {}
    for item in (
        extract_knowledge_items_from_decision_bundles_v1(decision_bundles)
        + extract_knowledge_items_from_kl_insights_v1(kl_insights)
    ):
        kid = _norm(item.get("knowledge_id"))
        if kid and kid not in merged:
            merged[kid] = item
    return list(merged.values())


def _representative_item(group: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        group,
        key=lambda it: (
            compute_routing_priority_v1(it),
            _norm(it.get("knowledge_id")),
        ),
    )


def _build_routed_item_v1(
    *,
    surface: str,
    section: str,
    group: list[dict[str, Any]],
    aggregation_key: str,
) -> dict[str, Any]:
    rep = _representative_item(group)
    member_ids = sorted({_norm(it.get("knowledge_id")) for it in group if _norm(it.get("knowledge_id"))})
    priority = max(compute_routing_priority_v1(it) for it in group)
    trace = rep.get("traceability")
    routed_trace: dict[str, Any] = {
        "routed_at": _utc_now_iso(),
        "routing_version": ROUTING_VERSION,
        "surface": surface,
        "section": section,
        "aggregation_key": aggregation_key,
        "member_knowledge_ids": member_ids,
        "routing_priority_basis": {
            "attention_level": _norm(rep.get("attention_level")),
            "confidence": _norm(rep.get("confidence")),
            "narrative_role": _norm(rep.get("narrative_role")),
        },
    }
    if isinstance(trace, Mapping):
        routed_trace["producer_traceability"] = dict(trace)

    route_id = f"route:{surface}:{section}:{aggregation_key}"
    return {
        "knowledge_id": route_id,
        "routing_priority": priority,
        "eligible_surfaces": list(rep.get("eligible_surfaces") or []),
        "merchant_visibility": rep.get("merchant_visibility"),
        "admin_visibility": rep.get("admin_visibility"),
        "attention_level": rep.get("attention_level"),
        "aggregation_key": aggregation_key,
        "narrative_role": rep.get("narrative_role"),
        "expiration_rule": rep.get("expiration_rule") or {},
        "traceability": routed_trace,
        "producer_reference": {
            "producer": _norm(rep.get("producer")) or "unknown",
            "source_knowledge_ids": member_ids,
            "representative_knowledge_id": _norm(rep.get("knowledge_id")),
        },
        "knowledge_payload": rep,
        "routing_version": ROUTING_VERSION,
        "section": section,
        "member_count": len(group),
        "member_knowledge_ids": member_ids,
        "member_payloads": group,
        "confidence": _norm(rep.get("confidence")),
    }


def route_knowledge_for_surface_v1(
    items: Iterable[Mapping[str, Any]],
    *,
    surface: str,
    max_attention_items: int = MAX_BRIEF_ITEMS,
) -> dict[str, Any]:
    """
    Route standardized knowledge items for one surface.

    Returns achievements + attention routed feeds (Daily Brief shape).
    """
    eligible: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        item = dict(raw)
        if not is_surface_eligible_v1(item, surface):
            continue
        if not is_merchant_visible_v1(item):
            continue
        eligible.append(item)

    achievement_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    attention_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in eligible:
        section = assign_routing_section_v1(item)
        agg = _norm(item.get("aggregation_key")) or _norm(item.get("knowledge_id"))
        if section == SECTION_ACHIEVEMENT:
            achievement_groups[agg].append(item)
        else:
            attention_groups[agg].append(item)

    achievements = [
        _build_routed_item_v1(
            surface=surface,
            section=SECTION_ACHIEVEMENT,
            group=grp,
            aggregation_key=key,
        )
        for key, grp in achievement_groups.items()
    ]
    achievements.sort(
        key=lambda r: (
            -int(r.get("routing_priority") or 0),
            -int(r.get("member_count") or 0),
            _norm(r.get("knowledge_id")),
        )
    )

    attention = [
        _build_routed_item_v1(
            surface=surface,
            section=SECTION_ATTENTION,
            group=grp,
            aggregation_key=key,
        )
        for key, grp in attention_groups.items()
    ]
    attention.sort(
        key=lambda r: (
            -int(r.get("routing_priority") or 0),
            -int(r.get("member_count") or 0),
            _norm(r.get("knowledge_id")),
        )
    )
    attention = attention[: max(0, int(max_attention_items))]

    return {
        "routing_version": ROUTING_VERSION,
        "surface": surface,
        "achievements": achievements,
        "attention_items": attention,
        "aggregation_reason": _AGGREGATION_REASON,
        "observability": {
            "input_items": len(list(items)) if not isinstance(items, list) else len(items),
            "eligible_items": len(eligible),
            "achievement_groups": len(achievements),
            "attention_groups": len(attention),
        },
    }


def route_daily_brief_knowledge_v1(
    *,
    decision_bundles: Iterable[Mapping[str, Any] | None] = (),
    kl_insights: Iterable[Mapping[str, Any] | None] = (),
    max_attention_items: int = MAX_BRIEF_ITEMS,
) -> dict[str, Any]:
    """Route knowledge for Daily Brief surface from producer inputs."""
    items = collect_routing_input_items_v1(
        decision_bundles=decision_bundles,
        kl_insights=kl_insights,
    )
    return route_knowledge_for_surface_v1(
        items,
        surface=SURFACE_DAILY_BRIEF,
        max_attention_items=max_attention_items,
    )


def route_knowledge_layer_knowledge_v1(
    *,
    kl_insights: Iterable[Mapping[str, Any] | None] = (),
    max_display_items: int = MAX_BRIEF_ITEMS,
) -> dict[str, Any]:
    """Route knowledge for Knowledge Layer surface from KL producer insights."""
    items = extract_knowledge_items_from_kl_insights_v1(kl_insights)
    return route_knowledge_for_surface_v1(
        items,
        surface=SURFACE_KNOWLEDGE_LAYER,
        max_attention_items=max_display_items,
    )


def route_cart_detail_knowledge_v1(
    *,
    explanation: Mapping[str, Any] | None = None,
    decision_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Route knowledge for Cart Detail surface from explanation + decisions."""
    items = collect_routing_input_items_v1(decision_bundles=[decision_bundle])
    if isinstance(explanation, Mapping) and _norm(explanation.get("knowledge_id")):
        kid = _norm(explanation.get("knowledge_id"))
        if not any(_norm(it.get("knowledge_id")) == kid for it in items):
            items.append(dict(explanation))
    return route_knowledge_for_surface_v1(
        items,
        surface=SURFACE_CART_DETAIL,
        max_attention_items=1,
    )


def route_merchant_home_knowledge_v1(
    *,
    kl_insights: Iterable[Mapping[str, Any] | None] | None = None,
    max_display_items: int = 3,
) -> dict[str, Any]:
    """Route KL producer insights for Merchant Home store-understanding slice."""
    items = extract_knowledge_items_from_kl_insights_v1(kl_insights)
    return route_knowledge_for_surface_v1(
        items,
        surface=SURFACE_MERCHANT_HOME,
        max_attention_items=max_display_items,
    )


def validate_routed_knowledge_item_v1(item: Mapping[str, Any]) -> list[str]:
    """Validate routed output contract."""
    required = (
        "knowledge_id",
        "routing_priority",
        "eligible_surfaces",
        "merchant_visibility",
        "admin_visibility",
        "attention_level",
        "aggregation_key",
        "narrative_role",
        "expiration_rule",
        "traceability",
        "producer_reference",
        "knowledge_payload",
        "routing_version",
    )
    missing = [k for k in required if k not in item]
    trace = item.get("traceability")
    if not isinstance(trace, Mapping):
        missing.append("traceability.type")
    elif not _norm(trace.get("routing_version")):
        missing.append("traceability.routing_version")
    pref = item.get("producer_reference")
    if not isinstance(pref, Mapping):
        missing.append("producer_reference.type")
    return missing


__all__ = [
    "ROUTING_VERSION",
    "SECTION_ACHIEVEMENT",
    "SECTION_ATTENTION",
    "SURFACE_DAILY_BRIEF",
    "SURFACE_CART_DETAIL",
    "SURFACE_KNOWLEDGE_LAYER",
    "assign_routing_section_v1",
    "collect_routing_input_items_v1",
    "compute_routing_priority_v1",
    "extract_knowledge_items_from_decision_bundles_v1",
    "extract_knowledge_items_from_kl_insights_v1",
    "is_published_knowledge_item",
    "is_surface_eligible_v1",
    "route_cart_detail_knowledge_v1",
    "route_merchant_home_knowledge_v1",
    "route_daily_brief_knowledge_v1",
    "route_knowledge_for_surface_v1",
    "route_knowledge_layer_knowledge_v1",
    "validate_routed_knowledge_item_v1",
]
