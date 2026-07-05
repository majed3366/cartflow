# -*- coding: utf-8 -*-
"""
Merchant Daily Brief Composer v2 — groups published decisions into briefing topics.

Deterministic aggregation only. Never mints decisions or changes truth/confidence.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Iterable, Mapping, Optional

from services.merchant_daily_brief_v1 import (
    MAX_BRIEF_ITEMS,
    _EMPTY_MESSAGE_AR,
    _EMPTY_TITLE_AR,
    _brief_action_ar,
    _commercial_goal_label_ar,
    _confidence_label_ar,
    _decision_class_label_ar,
    _evidence_source_ar,
    collect_published_decisions_from_bundles_v1,
    project_brief_item_v1,
)
from services.merchant_decision_layer_v1 import (
    CLASS_OBSERVATION,
)
from services.merchant_decision_registry_v1 import (
    DECISION_ID_CONTACT_CUSTOMER,
    DECISION_ID_FIX_CHANNEL,
    DECISION_ID_KL_OBSERVATION,
    DECISION_ID_MONITOR_RETURN,
    DECISION_ID_OBTAIN_CONTACT,
)

COMPOSER_VERSION = "v2"
BRIEF_VERSION = "v2"
SECTION_ACHIEVEMENT = "achievement"
SECTION_ATTENTION = "attention"

_AGGREGATION_REASON = "decision_id_family+action_key+commercial_goal+evidence_id"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _brief_date_iso() -> str:
    return date.today().isoformat()


def decision_id_family(decision_id: str) -> str:
    did = _norm(decision_id)
    if ":" in did:
        return did.split(":", 1)[0]
    return did


def aggregation_key_for_decision(decision: Mapping[str, Any]) -> str:
    """Deterministic grouping key — related decisions only."""
    family = decision_id_family(_norm(decision.get("decision_id")))
    action_key = _norm(decision.get("action_key")).lower()
    goal = _norm(decision.get("commercial_goal")).lower()
    evidence_ids = decision.get("evidence_ids")
    evidence = _norm(evidence_ids[0]) if isinstance(evidence_ids, list) and evidence_ids else ""
    insight_key = ""
    for src in decision.get("proof_sources") or []:
        s = _norm(src)
        if s.startswith("insight_key:"):
            insight_key = s
            break
    if family == DECISION_ID_KL_OBSERVATION:
        return f"{family}:{evidence}:{insight_key or goal}"
    return f"{family}:{action_key}:{goal}:{evidence}"


def is_achievement_decision(decision: Mapping[str, Any]) -> bool:
    """Achievements = completed/platform work (observation/monitor), not merchant problems."""
    cls = _norm(decision.get("decision_class"))
    action = _norm(decision.get("merchant_action")).lower()
    if cls == CLASS_OBSERVATION:
        return True
    if action == "monitor":
        return True
    family = decision_id_family(_norm(decision.get("decision_id")))
    if family == DECISION_ID_KL_OBSERVATION:
        return True
    return False


def _decision_trace_id(decision: Mapping[str, Any]) -> str:
    """Unique published-decision instance key for traceability (merge_key when present)."""
    mk = _norm(decision.get("merge_key"))
    if mk:
        return mk
    return _norm(decision.get("decision_id"))


def _representative_decision(group: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        group,
        key=lambda d: (
            int(d.get("priority") or 0),
            _norm(d.get("decision_timestamp")),
        ),
    )


def _singular_headline(decision: Mapping[str, Any]) -> str:
    cls = _norm(decision.get("decision_class"))
    explanation = decision.get("decision_explanation")
    if cls == CLASS_OBSERVATION and isinstance(explanation, Mapping):
        rationale = _norm(explanation.get("rationale_ar"))
        if rationale:
            return rationale
    action = _brief_action_ar(decision)
    if action:
        return action
    explanation = decision.get("decision_explanation")
    if isinstance(explanation, Mapping):
        rationale = _norm(explanation.get("rationale_ar"))
        if rationale:
            return rationale
    return "—"


def _topic_headline_ar(family: str, count: int, representative: Mapping[str, Any]) -> str:
    if count <= 1:
        return _singular_headline(representative)

    templates: dict[str, str] = {
        DECISION_ID_OBTAIN_CONTACT: (
            "{n} عملاء لا يمكن التواصل معهم — أرقام التواصل غير متوفرة"
        ),
        DECISION_ID_CONTACT_CUSTOMER: "{n} سلات تحتاج تواصلك مع العملاء",
        DECISION_ID_FIX_CHANNEL: "{n} سلات — فشل إرسال رسالة الاسترجاع",
        DECISION_ID_MONITOR_RETURN: (
            "CartFlow رصد {n} عودة للمتجر بعد رسالة الاسترجاع"
        ),
        DECISION_ID_KL_OBSERVATION: "CartFlow رصد {n} ملاحظات في نشاط متجرك",
    }
    template = templates.get(family)
    if template:
        return template.format(n=count)
    singular = _singular_headline(representative)
    return f"{count} حالات — {singular}" if count > 1 else singular


def _topic_why_ar(representative: Mapping[str, Any], count: int) -> str:
    explanation = representative.get("decision_explanation")
    if isinstance(explanation, Mapping):
        why = _norm(explanation.get("why_now_ar"))
        if why:
            if count > 1:
                return f"{why} ({count} حالات)"
            return why
    return "—"


def _build_topic_item(
    *,
    section: str,
    group: list[dict[str, Any]],
    aggregation_key: str,
    brief_date: str,
) -> dict[str, Any]:
    rep = _representative_decision(group)
    family = decision_id_family(_norm(rep.get("decision_id")))
    count = len(group)
    source_ids = sorted({_decision_trace_id(d) for d in group if _decision_trace_id(d)})
    headline = _topic_headline_ar(family, count, rep)
    why = _topic_why_ar(rep, count)
    action = _brief_action_ar(rep) if count == 1 else ""
    projected = project_brief_item_v1(rep, brief_date=brief_date)

    return {
        "brief_item_id": f"daily_brief:{brief_date}:{section}:{aggregation_key}",
        "section": section,
        "headline_ar": headline,
        "what_ar": headline,
        "why_ar": why,
        "action_ar": action,
        "action_present": bool(action),
        "decision_count": count,
        "source_decision_ids": source_ids,
        "aggregation_key": aggregation_key,
        "aggregation_reason": _AGGREGATION_REASON,
        "representative_decision_id": _norm(rep.get("decision_id")),
        "decision_id": _norm(rep.get("decision_id")),
        "decision_class": _norm(rep.get("decision_class")),
        "decision_class_label_ar": _decision_class_label_ar(_norm(rep.get("decision_class"))),
        "priority": max(int(d.get("priority") or 0) for d in group),
        "confidence": _norm(rep.get("confidence")),
        "confidence_label_ar": _confidence_label_ar(_norm(rep.get("confidence"))),
        "evidence_source_ar": _evidence_source_ar(rep),
        "evidence_ids": list(rep.get("evidence_ids") or []),
        "commercial_goal": _norm(rep.get("commercial_goal")),
        "commercial_goal_label_ar": _commercial_goal_label_ar(
            _norm(rep.get("commercial_goal"))
        ),
        "merge_key": aggregation_key,
        "proof_sources": list(rep.get("proof_sources") or []),
        "action_key": projected.get("action_key"),
    }


def group_decisions_into_topics(
    decisions: list[dict[str, Any]],
    *,
    brief_date: Optional[str] = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (achievements, attention_topics) from published decisions."""
    day = brief_date or _brief_date_iso()
    achievement_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    attention_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for decision in decisions:
        key = aggregation_key_for_decision(decision)
        if is_achievement_decision(decision):
            achievement_groups[key].append(decision)
        else:
            attention_groups[key].append(decision)

    achievements = [
        _build_topic_item(
            section=SECTION_ACHIEVEMENT,
            group=grp,
            aggregation_key=key,
            brief_date=day,
        )
        for key, grp in achievement_groups.items()
    ]
    achievements.sort(key=lambda t: (-int(t.get("decision_count") or 0), -int(t.get("priority") or 0)))

    attention_topics = [
        _build_topic_item(
            section=SECTION_ATTENTION,
            group=grp,
            aggregation_key=key,
            brief_date=day,
        )
        for key, grp in attention_groups.items()
    ]
    attention_topics.sort(
        key=lambda t: (-int(t.get("priority") or 0), -int(t.get("decision_count") or 0))
    )
    return achievements, attention_topics[:MAX_BRIEF_ITEMS]


def compose_merchant_daily_brief_v2(
    *,
    decision_bundles: Iterable[Mapping[str, Any] | None],
    brief_date: Optional[str] = None,
) -> dict[str, Any]:
    """Compose executive daily brief with achievements first, then attention topics."""
    day = brief_date or _brief_date_iso()
    collected = collect_published_decisions_from_bundles_v1(decision_bundles)
    achievements, attention_items = group_decisions_into_topics(collected, brief_date=day)

    all_source_ids: set[str] = set()
    for topic in achievements + attention_items:
        for sid in topic.get("source_decision_ids") or []:
            all_source_ids.add(_norm(sid))

    empty = not achievements and not attention_items
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
        "observability": {
            "decisions_collected": len(collected),
            "decisions_composed": len(all_source_ids),
            "achievement_topics": len(achievements),
            "attention_topics": len(attention_items),
            "bundles_scanned": sum(
                1
                for b in decision_bundles
                if isinstance(b, Mapping) and isinstance(b.get("decisions"), list)
            ),
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
    "validate_merchant_daily_brief_v2",
]
