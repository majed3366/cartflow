# -*- coding: utf-8 -*-
"""
Merchant Daily Brief Composer v2 — projection-only consumer of routed knowledge.

Groups are assigned by Knowledge Routing v1. Composer projects routed items only.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from services.merchant_daily_brief_time_v1 import brief_date_iso
from services.knowledge_routing_v1 import (
    ROUTING_VERSION,
    route_daily_brief_knowledge_v1,
)
from services.merchant_daily_brief_v1 import (
    MAX_BRIEF_ITEMS,
    _EMPTY_MESSAGE_AR,
    _EMPTY_TITLE_AR,
    _brief_action_ar,
    _commercial_goal_label_ar,
    _confidence_label_ar,
    _decision_class_label_ar,
    _evidence_source_ar,
    project_brief_item_v1,
)

COMPOSER_VERSION = "v2"
BRIEF_VERSION = "v2"
SECTION_ACHIEVEMENT = "achievement"
SECTION_ATTENTION = "attention"

_AGGREGATION_REASON = "routing:aggregation_key+narrative_role+surface"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _decision_trace_id(decision: Mapping[str, Any]) -> str:
    mk = _norm(decision.get("merge_key"))
    if mk:
        return mk
    return _norm(decision.get("decision_id"))


def _headline_from_routed_v2(routed: Mapping[str, Any]) -> str:
    """Project headline from routed knowledge_payload only — no domain branching."""
    payload = routed.get("knowledge_payload")
    if not isinstance(payload, Mapping):
        return "—"
    explanation = payload.get("decision_explanation")
    rationale = ""
    if isinstance(explanation, Mapping):
        rationale = _norm(explanation.get("rationale_ar"))
    if not rationale:
        rationale = _norm(payload.get("title_ar"))
    count = int(routed.get("member_count") or 1)
    if count > 1:
        return f"{count} حالات — {rationale}" if rationale else f"{count} حالات"
    return rationale or "—"


def _why_from_routed_v2(routed: Mapping[str, Any]) -> str:
    payload = routed.get("knowledge_payload")
    if not isinstance(payload, Mapping):
        return "—"
    explanation = payload.get("decision_explanation")
    if isinstance(explanation, Mapping):
        why = _norm(explanation.get("why_now_ar"))
        if why:
            count = int(routed.get("member_count") or 1)
            if count > 1:
                return f"{why} ({count} حالات)"
            return why
    return "—"


def _source_trace_ids_from_routed_v2(routed: Mapping[str, Any]) -> list[str]:
    ids: set[str] = set()
    members = routed.get("member_payloads")
    if isinstance(members, list) and members:
        for member in members:
            if isinstance(member, Mapping):
                tid = _decision_trace_id(member)
                if tid:
                    ids.add(tid)
    else:
        payload = routed.get("knowledge_payload")
        if isinstance(payload, Mapping):
            tid = _decision_trace_id(payload)
            if tid:
                ids.add(tid)
    return sorted(ids)


def project_routed_topic_v2(
    routed: Mapping[str, Any],
    *,
    brief_date: Optional[str] = None,
) -> dict[str, Any]:
    """Project one routed knowledge item into a Daily Brief topic (presentation only)."""
    day = brief_date or brief_date_iso()
    payload = routed.get("knowledge_payload")
    rep = payload if isinstance(payload, Mapping) else {}
    section = _norm(routed.get("section")) or SECTION_ATTENTION
    aggregation_key = _norm(routed.get("aggregation_key"))
    headline = _headline_from_routed_v2(routed)
    why = _why_from_routed_v2(routed)
    count = int(routed.get("member_count") or 1)
    action = _brief_action_ar(rep) if count == 1 else ""
    projected = project_brief_item_v1(rep, brief_date=day) if rep else {}

    return {
        "brief_item_id": f"daily_brief:{day}:{section}:{aggregation_key}",
        "section": section,
        "headline_ar": headline,
        "what_ar": headline,
        "why_ar": why,
        "action_ar": action,
        "action_present": bool(action),
        "decision_count": count,
        "source_decision_ids": _source_trace_ids_from_routed_v2(routed),
        "aggregation_key": aggregation_key,
        "aggregation_reason": _AGGREGATION_REASON,
        "routing_priority": int(routed.get("routing_priority") or 0),
        "routing_version": _norm(routed.get("routing_version")) or ROUTING_VERSION,
        "routed_knowledge_id": _norm(routed.get("knowledge_id")),
        "representative_knowledge_id": _norm(
            (routed.get("producer_reference") or {}).get("representative_knowledge_id")
            if isinstance(routed.get("producer_reference"), Mapping)
            else ""
        ),
        "representative_decision_id": _norm(rep.get("decision_id")),
        "decision_id": _norm(rep.get("decision_id")),
        "decision_class": _norm(rep.get("decision_class")),
        "decision_class_label_ar": _decision_class_label_ar(_norm(rep.get("decision_class"))),
        "priority": int(routed.get("routing_priority") or 0),
        "confidence": _norm(routed.get("confidence")) or _norm(rep.get("confidence")),
        "confidence_label_ar": _confidence_label_ar(
            _norm(routed.get("confidence")) or _norm(rep.get("confidence"))
        ),
        "evidence_source_ar": _evidence_source_ar(rep) if rep else "—",
        "evidence_ids": list(rep.get("evidence_ids") or []),
        "commercial_goal": _norm(rep.get("commercial_goal")),
        "commercial_goal_label_ar": _commercial_goal_label_ar(_norm(rep.get("commercial_goal"))),
        "merge_key": aggregation_key,
        "proof_sources": list(rep.get("proof_sources") or []),
        "action_key": projected.get("action_key"),
    }


def compose_merchant_daily_brief_v2(
    *,
    decision_bundles: Iterable[Mapping[str, Any] | None] = (),
    kl_insights: Iterable[Mapping[str, Any] | None] = (),
    routed_feed: Optional[Mapping[str, Any]] = None,
    brief_date: Optional[str] = None,
) -> dict[str, Any]:
    """Compose executive daily brief from routed knowledge (projection only)."""
    day = brief_date or brief_date_iso()
    feed = routed_feed or route_daily_brief_knowledge_v1(
        decision_bundles=decision_bundles,
        kl_insights=kl_insights,
    )
    achievements = [
        project_routed_topic_v2(r, brief_date=day)
        for r in feed.get("achievements") or []
        if isinstance(r, Mapping)
    ]
    attention_items = [
        project_routed_topic_v2(r, brief_date=day)
        for r in feed.get("attention_items") or []
        if isinstance(r, Mapping)
    ]

    all_source_ids: set[str] = set()
    for topic in achievements + attention_items:
        for sid in topic.get("source_decision_ids") or []:
            all_source_ids.add(_norm(sid))

    empty = not achievements and not attention_items
    obs = feed.get("observability") if isinstance(feed.get("observability"), Mapping) else {}
    return {
        "version": BRIEF_VERSION,
        "composer_version": COMPOSER_VERSION,
        "brief_date": day,
        "achievements": achievements,
        "attention_items": attention_items,
        "items": attention_items,
        "achievement_count": len(achievements),
        "attention_count": len(attention_items),
        "item_count": len(attention_items),
        "max_items": MAX_BRIEF_ITEMS,
        "empty": empty,
        "empty_state_ar": {
            "title_ar": _EMPTY_TITLE_AR,
            "message_ar": _EMPTY_MESSAGE_AR,
        },
        "knowledge_routing_v1": {
            "routing_version": _norm(feed.get("routing_version")) or ROUTING_VERSION,
            "surface": _norm(feed.get("surface")) or "daily_brief",
            "observability": dict(obs),
        },
        "observability": {
            "decisions_collected": int(obs.get("input_items") or 0),
            "decisions_composed": len(all_source_ids),
            "achievement_topics": len(achievements),
            "attention_topics": len(attention_items),
            "bundles_scanned": sum(
                1
                for b in decision_bundles
                if isinstance(b, Mapping) and isinstance(b.get("decisions"), list)
            ),
            "routing_eligible_items": int(obs.get("eligible_items") or 0),
        },
    }


def validate_merchant_daily_brief_v2(brief: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if _norm(brief.get("composer_version")) != COMPOSER_VERSION:
        errors.append("composer_version")
    achievements = brief.get("achievements")
    attention = brief.get("attention_items")
    if not isinstance(achievements, list):
        errors.append("achievements")
    if not isinstance(attention, list):
        errors.append("attention_items")
        return errors
    if len(attention) > MAX_BRIEF_ITEMS:
        errors.append("attention_count_exceeds_max")

    seen_agg: set[str] = set()
    for section_name, items in (("achievements", achievements), ("attention", attention)):
        for idx, item in enumerate(items or []):
            if not isinstance(item, Mapping):
                errors.append(f"{section_name}[{idx}]_type")
                continue
            agg = _norm(item.get("aggregation_key"))
            if agg in seen_agg:
                errors.append(f"duplicate_aggregation:{agg}")
            seen_agg.add(agg)
            ids = item.get("source_decision_ids")
            if not isinstance(ids, list) or not ids:
                errors.append(f"{section_name}[{idx}].source_decision_ids")
            count = item.get("decision_count")
            if not isinstance(count, int) or count < 1:
                errors.append(f"{section_name}[{idx}].decision_count")
            elif isinstance(ids, list) and count != len(ids):
                errors.append(f"{section_name}[{idx}].decision_count_mismatch")
            if not _norm(item.get("aggregation_reason")):
                errors.append(f"{section_name}[{idx}].aggregation_reason")
            if not _norm(item.get("headline_ar")):
                errors.append(f"{section_name}[{idx}].headline_ar")
    return errors


# Legacy helpers retained for unit tests of routing migration — not used by compose path.
def decision_id_family(decision_id: str) -> str:
    did = _norm(decision_id)
    if ":" in did:
        return did.split(":", 1)[0]
    return did


def aggregation_key_for_decision(decision: Mapping[str, Any]) -> str:
    return _norm(decision.get("aggregation_key")) or _norm(decision.get("merge_key"))


def is_achievement_decision(decision: Mapping[str, Any]) -> bool:
    from services.knowledge_routing_v1 import assign_routing_section_v1

    return assign_routing_section_v1(decision) == SECTION_ACHIEVEMENT


def group_decisions_into_topics(
    decisions: list[dict[str, Any]],
    *,
    brief_date: Optional[str] = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deprecated — routing assigns groups; retained for migration tests."""
    from services.knowledge_routing_v1 import route_daily_brief_knowledge_v1

    day = brief_date or brief_date_iso()
    feed = route_daily_brief_knowledge_v1(decision_bundles=[{"decisions": decisions}])
    achievements = [
        project_routed_topic_v2(r, brief_date=day) for r in feed.get("achievements") or []
    ]
    attention = [
        project_routed_topic_v2(r, brief_date=day) for r in feed.get("attention_items") or []
    ]
    return achievements, attention


__all__ = [
    "BRIEF_VERSION",
    "COMPOSER_VERSION",
    "SECTION_ACHIEVEMENT",
    "SECTION_ATTENTION",
    "aggregation_key_for_decision",
    "compose_merchant_daily_brief_v2",
    "decision_id_family",
    "group_decisions_into_topics",
    "is_achievement_decision",
    "project_routed_topic_v2",
    "validate_merchant_daily_brief_v2",
]
