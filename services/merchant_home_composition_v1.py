# -*- coding: utf-8 -*-
"""
Merchant Home Composition v1 — presentation-only composition of governed knowledge.

Consumes Daily Brief (routing-backed), Knowledge Layer projection, and read-model nav
metadata. Never mints decisions, explanations, routing, or KPI knowledge.

INV-002 WP-5: consumes Platform Identity Authority MQIC — never resolves
merchant/store identity independently.

PIB-1 — Home Truth Alignment: Home summarizes the same store truth Knowledge already
holds (Attention for blocked work, Understanding for KL insights, badge = cart_count).

PIB-2 — Attention Decision Surface: Attention is an ordered merchant decision queue
(action / why / evidence / state / outcome) — never a passive list; never invents priority.

PIB-3 — Recovery Journey Explainability: each recovery Attention decision exposes
stage / channel / blocker / next platform & merchant actions from canonical LT-C1 labels.

Home Daily Business Brief V1 — Constitution V3: seven sections, one business
question each (health / risk / opportunity / priority / understanding / learning /
timeline). Home consumes governed upstream truth; never mints commercial meaning.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from services.knowledge_layer_projection_v1 import (
    flatten_kl_routed_display_items_v1,
    project_kl_display_card_v1,
)
from services.knowledge_routing_v1 import (
    ROUTING_VERSION,
    SURFACE_MERCHANT_HOME,
    route_merchant_home_knowledge_v1,
)
from services.merchant_daily_brief_time_v1 import brief_date_iso
from services.merchant_daily_brief_v1 import MAX_BRIEF_ITEMS
from services.merchant_recovery_journey_home_v1 import (
    attach_recovery_journey_to_attention_item_v1,
    recovery_decision_requires_journey_v1,
)

COMPOSITION_VERSION = "v1"
EXPERIENCE_TIER_STARTER = "starter"
EXPERIENCE_TIER_GROWTH = "growth"
EXPERIENCE_TIER_PRO = "pro"

# Constitution V3 — Today's Priority is exactly one primary recommendation.
HOME_MAX_ATTENTION_DISPLAY = 1
HOME_MAX_UNDERSTANDING_DISPLAY = 3
HOME_DAILY_BUSINESS_BRIEF_V1 = True

_SECTION_WHILE_AWAY = "while_away"
_SECTION_ATTENTION = "attention_today"
_SECTION_UNDERSTANDING = "store_understanding"

_PLACEHOLDER_DETAILS = frozenset(
    {
        "—",
        "-",
        "ملخص Knowledge Layer للفترة المحددة",
    }
)

_ACTION_OBTAIN_CONTACT_AR = "الحصول على رقم العميل — افتح السلال بانتظار رقم التواصل"
_ACTION_FIX_CHANNEL_AR = "إصلاح قناة واتساب — راجع إعدادات الاتصال"
_ACTION_CONTACT_CUSTOMER_AR = "التواصل مع العميل — افتح السلال التي تحتاج تدخلاً"

_STATE_CONTACT_WAIT_AR = "الاسترجاع متوقف — بانتظار رقم العميل"
_OUTCOME_CONTACT_AR = "بعد توفر الرقم يمكن متابعة الاسترجاع تلقائياً"
_IF_IGNORED_CONTACT_AR = "تبقى السلال بدون إرسال استرجاع آلي"

_STATE_FIX_CHANNEL_AR = "قناة الإرسال متعطلة — الاسترجاع لا يصل"
_OUTCOME_FIX_CHANNEL_AR = "بعد الإصلاح تُستأنف رسائل الاسترجاع"
_IF_IGNORED_FIX_CHANNEL_AR = "تتوقف رسائل الاسترجاع على السلال المتأثرة"

_STATE_CONTACT_CUSTOMER_AR = "سلة تحتاج تدخلاً يدوياً بعد توفر بيانات التواصل"
_OUTCOME_CONTACT_CUSTOMER_AR = "التواصل في الوقت المناسب يزيد فرصة إكمال الشراء"
_IF_IGNORED_CONTACT_CUSTOMER_AR = "قد تفوت فرصة استرجاع يدوية"

# Home Understanding priority when summarizing Knowledge (not a new product concept).
_UNDERSTANDING_PRIORITY = {
    "traffic_cart_demand_trend": 100,
    "store_health_overview": 90,
    "hesitation_top_reason": 80,
    "recovery_activity_summary": 70,
    "conversion_cart_to_purchase": 60,
}

# Merchant priority classes for Attention queue (lower = earlier). Not AI; product truth only.
_PRIORITY_BLOCKED = 0
_PRIORITY_IMMEDIATE_ACTION = 1
_PRIORITY_PASSIVE = 2


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _greeting_ar(hour: Optional[int] = None) -> str:
    from services.knowledge_time_authority_v1 import knowledge_stamp_now  # noqa: PLC0415

    h = hour if hour is not None else knowledge_stamp_now().hour
    if 5 <= h < 12:
        return "صباح الخير"
    return "مساء الخير"


def _is_placeholder_detail(value: Any) -> bool:
    return _norm(value) in _PLACEHOLDER_DETAILS


def _insight_key_from_topic(topic: Mapping[str, Any]) -> str:
    for key in ("insight_key",):
        raw = _norm(topic.get(key))
        if raw:
            return raw
    agg = _norm(topic.get("aggregation_key"))
    if "insight_key:" in agg:
        return agg.split("insight_key:")[-1].split(":")[0]
    head = agg.split(":")[0] if agg else ""
    if head and not head.startswith("decision_") and head not in (
        "route",
        "daily_brief",
        "agg",
        "kid",
        "bid",
    ):
        return head
    for src in topic.get("proof_sources") or topic.get("source_decision_ids") or []:
        s = _norm(src)
        if s.startswith("insight_key:"):
            return s.split(":", 1)[1]
        if s.startswith("insight:"):
            return s.split(":", 1)[1]
    return ""


def _fact_key_from_topic(topic: Mapping[str, Any]) -> str:
    """One merchant fact → one stable key across Brief / Timeline / Understanding."""
    agg = _norm(topic.get("aggregation_key"))
    if "obtain_contact" in agg or _norm(topic.get("action_key")).lower() == "obtain_contact":
        return "fact:obtain_contact"
    insight = _insight_key_from_topic(topic)
    if insight:
        return f"insight:{insight}"
    if agg:
        return f"agg:{agg}"
    kid = _norm(topic.get("routed_knowledge_id")) or _norm(topic.get("source_knowledge_id"))
    if kid:
        return f"kid:{kid}"
    return f"bid:{_norm(topic.get('brief_item_id'))}"


def _fact_key_from_card(card: Mapping[str, Any]) -> str:
    insight = _norm(card.get("insight_key"))
    if insight:
        return f"insight:{insight}"
    kid = _norm(card.get("routing_knowledge_id")) or _norm(card.get("source_knowledge_id"))
    if kid:
        return f"kid:{kid}"
    return f"key:{_norm(card.get('title_ar'))}"


def _dedupe_key_from_topic(topic: Mapping[str, Any]) -> str:
    return _fact_key_from_topic(topic)


def _dedupe_key_from_card(card: Mapping[str, Any]) -> str:
    return _fact_key_from_card(card)


def _is_blocked_contact_wait(topic: Mapping[str, Any]) -> bool:
    """Blocked recovery waiting for customer phone — Attention, never a win."""
    agg = _norm(topic.get("aggregation_key")).lower()
    action = _norm(topic.get("action_key")).lower()
    decision_id = _norm(topic.get("decision_id")).lower()
    headline = _norm(topic.get("headline_ar")) or _norm(topic.get("what_ar"))
    detail = _norm(topic.get("why_ar")) or _norm(topic.get("detail_ar"))
    blob = f"{agg} {action} {decision_id} {headline} {detail}"
    if "obtain_contact" in blob:
        return True
    if "بانتظار رقم" in blob or "بدون رقم" in blob:
        return True
    if "لا يمكن متابعة الاسترجاع بدون رقم" in blob:
        return True
    return False


def _is_limit_insight_win(topic: Mapping[str, Any]) -> bool:
    """Insufficient / unavailable Knowledge must not appear as while-away completions."""
    conf = _norm(topic.get("confidence")).lower()
    if conf == "insufficient":
        return True
    insight = _insight_key_from_topic(topic).lower()
    agg = _norm(topic.get("aggregation_key")).lower()
    markers = (
        "insufficient",
        "unavailable",
        "funnel_gaps",
        "visitor_unavailable",
    )
    return any(m in insight or m in agg for m in markers)


def _is_kl_observation_twin(topic: Mapping[str, Any]) -> bool:
    agg = _norm(topic.get("aggregation_key"))
    decision_id = _norm(topic.get("decision_id"))
    return agg.startswith("decision_kl_observation") or decision_id.startswith(
        "decision_kl_observation"
    )


def _project_while_away_item(topic: Mapping[str, Any]) -> dict[str, Any]:
    headline = _norm(topic.get("headline_ar"))
    if not headline:
        headline = _norm(topic.get("what_ar")) or "—"
    detail = _norm(topic.get("why_ar")) or _norm(topic.get("what_ar"))
    return {
        "headline_ar": headline,
        "detail_ar": detail,
        "action_ar": _norm(topic.get("action_ar")),
        "aggregation_key": _norm(topic.get("aggregation_key")),
        "source_knowledge_id": _norm(topic.get("routed_knowledge_id")),
        "routing_priority": int(topic.get("routing_priority") or 0),
        "section": _SECTION_WHILE_AWAY,
        "insight_key": _insight_key_from_topic(topic),
        "confidence": _norm(topic.get("confidence")),
        "fact_key": _fact_key_from_topic(topic),
    }


def _decision_case_count(topic: Mapping[str, Any]) -> int:
    for key in ("decision_count", "member_count", "case_count"):
        try:
            n = int(topic.get(key) or 0)
        except (TypeError, ValueError):
            n = 0
        if n > 0:
            return n
    headline = _norm(topic.get("headline_ar")) or _norm(topic.get("what_ar"))
    if "حالات" in headline:
        head = headline.split("حالات", 1)[0].strip()
        digits = "".join(ch for ch in head if ch.isdigit())
        if digits:
            try:
                return int(digits)
            except ValueError:
                return 0
    return 0


def _operational_decision_key(topic: Mapping[str, Any]) -> str:
    """One merchant problem → one Attention decision (PIB-2)."""
    agg = _norm(topic.get("aggregation_key")).lower()
    action = _norm(topic.get("action_key")).lower()
    insight = _insight_key_from_topic(topic).lower()
    if _is_blocked_contact_wait(topic) or "obtain_contact" in agg or action == "obtain_contact":
        return "decision:obtain_contact"
    if insight == "store_health_overview":
        # Phone-gap health is the same operational ask as obtain-contact.
        return "decision:obtain_contact"
    if "fix_channel" in agg or action == "fix_channel":
        return "decision:fix_channel"
    if "contact_customer" in agg or action == "contact_customer":
        return "decision:contact_customer"
    return f"decision:{_fact_key_from_topic(topic)}"


def _extract_decision_explanation(topic: Mapping[str, Any]) -> dict[str, str]:
    expl = topic.get("decision_explanation")
    if isinstance(expl, Mapping):
        return {
            "rationale_ar": _norm(expl.get("rationale_ar")),
            "why_now_ar": _norm(expl.get("why_now_ar")),
            "if_omitted_ar": _norm(expl.get("if_omitted_ar")),
        }
    return {
        "rationale_ar": "",
        "why_now_ar": _norm(topic.get("why_ar")) or _norm(topic.get("detail_ar")),
        "if_omitted_ar": _norm(topic.get("if_omitted_ar")) or _norm(topic.get("if_ignored_ar")),
    }


def _attention_priority_class(item: Mapping[str, Any]) -> int:
    """Merchant priority only: blocked → immediate action → passive."""
    op = _norm(item.get("operational_decision_key"))
    if op in ("decision:obtain_contact", "decision:fix_channel"):
        return _PRIORITY_BLOCKED
    severity = _norm(item.get("severity"))
    cls = _norm(item.get("decision_class"))
    if severity in ("critical", "suggested", "attention") or cls in (
        "critical_action",
        "suggested_action",
        "needs_attention",
    ):
        if item.get("action_present"):
            return _PRIORITY_IMMEDIATE_ACTION
    return _PRIORITY_PASSIVE


def _is_attention_decision_complete(item: Mapping[str, Any]) -> bool:
    required = (
        "action_ar",
        "why_ar",
        "evidence_ar",
        "operational_state_ar",
        "expected_outcome_ar",
    )
    return all(_norm(item.get(k)) and not _is_placeholder_detail(item.get(k)) for k in required)


def _complete_attention_decision(
    projected: dict[str, Any],
    topic: Mapping[str, Any],
    kl_by_insight: Mapping[str, Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    """Fill PIB-2 Attention contract from governed topic + Knowledge; drop if incomplete."""
    op_key = _operational_decision_key(topic)
    projected["operational_decision_key"] = op_key
    expl = _extract_decision_explanation(topic)
    cases = _decision_case_count(topic)

    if op_key == "decision:obtain_contact":
        projected["action_ar"] = projected.get("action_ar") or _ACTION_OBTAIN_CONTACT_AR
        projected["why_ar"] = (
            projected.get("why_ar")
            or expl.get("why_now_ar")
            or "لا يمكن متابعة الاسترجاع بدون رقم تواصل"
        )
        kl_health = kl_by_insight.get("store_health_overview")
        kl_msg = ""
        if isinstance(kl_health, Mapping):
            kl_msg = _norm(kl_health.get("message_ar")) or _norm(kl_health.get("message"))
        evidence = kl_msg or _norm(projected.get("why_ar"))
        if cases > 0 and evidence and str(cases) not in evidence:
            evidence = f"{cases} حالات — {evidence}"
        elif cases > 0 and not evidence:
            evidence = f"{cases} حالات بانتظار رقم العميل"
        if not evidence:
            evidence = kl_msg or "سلال بانتظار رقم العميل قبل متابعة الاسترجاع"
        projected["evidence_ar"] = evidence
        state = _STATE_CONTACT_WAIT_AR
        if cases > 0:
            state = f"{_STATE_CONTACT_WAIT_AR} ({cases} حالات)"
        projected["operational_state_ar"] = state
        projected["expected_outcome_ar"] = _OUTCOME_CONTACT_AR
        ignored = expl.get("if_omitted_ar")
        projected["if_ignored_ar"] = (
            ignored
            if ignored and not _is_placeholder_detail(ignored)
            else _IF_IGNORED_CONTACT_AR
        )
        if _norm(projected.get("decision_class")) in ("", "observation"):
            projected["decision_class"] = "needs_attention"
            projected["decision_class_label_ar"] = "يحتاج انتباه"
            projected["severity"] = "attention"
    elif op_key == "decision:fix_channel":
        projected["action_ar"] = projected.get("action_ar") or _ACTION_FIX_CHANNEL_AR
        projected["why_ar"] = (
            projected.get("why_ar") or expl.get("why_now_ar") or _STATE_FIX_CHANNEL_AR
        )
        projected["evidence_ar"] = projected.get("why_ar") or _STATE_FIX_CHANNEL_AR
        projected["operational_state_ar"] = _STATE_FIX_CHANNEL_AR
        projected["expected_outcome_ar"] = _OUTCOME_FIX_CHANNEL_AR
        ignored = expl.get("if_omitted_ar")
        projected["if_ignored_ar"] = (
            ignored
            if ignored and not _is_placeholder_detail(ignored)
            else _IF_IGNORED_FIX_CHANNEL_AR
        )
        projected["decision_class"] = projected.get("decision_class") or "critical_action"
        projected["severity"] = "critical"
        projected["decision_class_label_ar"] = projected.get("decision_class_label_ar") or "إجراء عاجل"
    elif op_key == "decision:contact_customer":
        projected["action_ar"] = projected.get("action_ar") or _ACTION_CONTACT_CUSTOMER_AR
        projected["why_ar"] = (
            projected.get("why_ar") or expl.get("why_now_ar") or _STATE_CONTACT_CUSTOMER_AR
        )
        projected["evidence_ar"] = projected.get("why_ar") or _STATE_CONTACT_CUSTOMER_AR
        if cases > 0 and str(cases) not in projected["evidence_ar"]:
            projected["evidence_ar"] = f"{cases} حالات — {projected['evidence_ar']}"
        projected["operational_state_ar"] = (
            f"{_STATE_CONTACT_CUSTOMER_AR} ({cases} حالات)" if cases > 0 else _STATE_CONTACT_CUSTOMER_AR
        )
        projected["expected_outcome_ar"] = _OUTCOME_CONTACT_CUSTOMER_AR
        ignored = expl.get("if_omitted_ar")
        projected["if_ignored_ar"] = (
            ignored
            if ignored and not _is_placeholder_detail(ignored)
            else _IF_IGNORED_CONTACT_CUSTOMER_AR
        )
        if _norm(projected.get("decision_class")) in ("", "observation"):
            projected["decision_class"] = "needs_attention"
            projected["severity"] = "attention"
            projected["decision_class_label_ar"] = "يحتاج انتباه"
    else:
        # Informational attention — still must be a complete decision or it is dropped.
        projected["action_ar"] = projected.get("action_ar") or ""
        projected["why_ar"] = projected.get("why_ar") or expl.get("why_now_ar") or ""
        projected["evidence_ar"] = (
            _enrich_detail_from_kl("", topic, kl_by_insight)
            or projected.get("why_ar")
            or ""
        )
        projected["operational_state_ar"] = (
            expl.get("rationale_ar") or projected.get("headline_ar") or ""
        )
        ignored = expl.get("if_omitted_ar")
        projected["if_ignored_ar"] = (
            ignored if ignored and not _is_placeholder_detail(ignored) else ""
        )
        projected["expected_outcome_ar"] = projected.get("if_ignored_ar") or (
            "نستمر في المراقبة — التفاصيل في طبقة المعرفة"
            if projected.get("why_ar")
            else ""
        )

    projected["action_present"] = bool(_norm(projected.get("action_ar")))
    projected["priority_class"] = _attention_priority_class(projected)
    projected["queue_rank"] = int(projected["priority_class"])

    # PIB-3: attach Recovery Journey chapter (canonical stages only).
    attach_recovery_journey_to_attention_item_v1(
        projected,
        operational_decision_key=op_key,
        case_count=cases,
    )
    if recovery_decision_requires_journey_v1(op_key) and not projected.get(
        "recovery_journey_complete"
    ):
        return None

    # Absorb related fact keys so Understanding/while-away do not restate the same decision.
    related = {_norm(projected.get("fact_key")), _fact_key_from_topic(topic)}
    if op_key == "decision:obtain_contact":
        related.add("fact:obtain_contact")
        related.add("insight:store_health_overview")
    projected["related_fact_keys"] = sorted(k for k in related if k)

    if not _is_attention_decision_complete(projected):
        return None
    return projected


def _prefer_attention_decision(
    current: Mapping[str, Any], incoming: Mapping[str, Any]
) -> dict[str, Any]:
    """Keep the richer decision when merging one operational problem."""
    cur = dict(current)
    inc = dict(incoming)
    cur_cases = _decision_case_count(cur)
    inc_cases = _decision_case_count(inc)
    # Prefer blocked obtain_contact wording with case counts.
    prefer_inc = False
    if _norm(inc.get("fact_key")) == "fact:obtain_contact" and _norm(cur.get("fact_key")) != (
        "fact:obtain_contact"
    ):
        prefer_inc = True
    if inc_cases > cur_cases:
        prefer_inc = True
    chosen = inc if prefer_inc else cur
    other = cur if prefer_inc else inc
    # Merge evidence / related facts.
    if not _norm(chosen.get("evidence_ar")) and _norm(other.get("evidence_ar")):
        chosen["evidence_ar"] = other["evidence_ar"]
    elif (
        _norm(other.get("evidence_ar"))
        and _norm(other.get("evidence_ar")) not in _norm(chosen.get("evidence_ar"))
    ):
        chosen["evidence_ar"] = (
            f"{chosen['evidence_ar']} — {other['evidence_ar']}"
            if _norm(chosen.get("evidence_ar"))
            else other["evidence_ar"]
        )
    related = set(chosen.get("related_fact_keys") or [])
    related.update(other.get("related_fact_keys") or [])
    chosen["related_fact_keys"] = sorted(related)
    if not _norm(chosen.get("if_ignored_ar")):
        chosen["if_ignored_ar"] = _norm(other.get("if_ignored_ar"))
    chosen["priority_class"] = _attention_priority_class(chosen)
    chosen["queue_rank"] = int(chosen["priority_class"])
    # Re-attach journey so case counts / action stay coherent after merge.
    attach_recovery_journey_to_attention_item_v1(
        chosen,
        operational_decision_key=_norm(chosen.get("operational_decision_key")),
        case_count=_decision_case_count(chosen),
    )
    return chosen


def _project_attention_item(topic: Mapping[str, Any]) -> dict[str, Any]:
    headline = _norm(topic.get("headline_ar"))
    if not headline:
        if topic.get("action_present") and topic.get("action_ar"):
            headline = _norm(topic.get("action_ar"))
        else:
            headline = _norm(topic.get("what_ar")) or "—"
    why = _norm(topic.get("why_ar")) or _norm(topic.get("detail_ar"))
    if _is_placeholder_detail(why):
        why = ""
    action = _norm(topic.get("action_ar"))
    if _is_blocked_contact_wait(topic) and not action:
        action = _ACTION_OBTAIN_CONTACT_AR
    cls = _norm(topic.get("decision_class"))
    if _is_blocked_contact_wait(topic) and cls in ("", "observation"):
        cls = "needs_attention"
    severity = "observation"
    if cls == "critical_action":
        severity = "critical"
    elif cls == "suggested_action":
        severity = "suggested"
    elif cls == "needs_attention":
        severity = "attention"
    return {
        "headline_ar": headline,
        "why_ar": why,
        "action_ar": action,
        "action_present": bool(action),
        "decision_class": cls,
        "decision_class_label_ar": _norm(topic.get("decision_class_label_ar"))
        or ("يحتاج انتباه" if cls == "needs_attention" else ""),
        "severity": severity,
        "aggregation_key": _norm(topic.get("aggregation_key")),
        "source_knowledge_id": _norm(topic.get("routed_knowledge_id"))
        or _norm(topic.get("source_knowledge_id")),
        "routing_priority": int(topic.get("routing_priority") or 0),
        "section": _SECTION_ATTENTION,
        "insight_key": _insight_key_from_topic(topic),
        "fact_key": _fact_key_from_topic(topic),
        "decision_count": _decision_case_count(topic),
        "decision_explanation": topic.get("decision_explanation"),
        "action_key": _norm(topic.get("action_key")),
        "if_omitted_ar": _norm(topic.get("if_omitted_ar")),
    }


def _project_understanding_item(
    card: Mapping[str, Any],
    *,
    window_days: int = 7,
) -> dict[str, Any]:
    observation = _norm(card.get("observation_ar"))
    if _is_placeholder_detail(observation):
        observation = ""
    return {
        "title_ar": _norm(card.get("title_ar")),
        "observation_ar": observation,
        "impact_ar": _norm(card.get("impact_ar")),
        "action_ar": _norm(card.get("action_ar")),
        "insight_key": _norm(card.get("insight_key")),
        "source_knowledge_id": _norm(card.get("routing_knowledge_id"))
        or _norm(card.get("source_knowledge_id")),
        "confidence": _norm(card.get("confidence")) or "insufficient",
        "evidence_label_ar": _norm(card.get("evidence_label_ar")),
        "window_days": int(window_days or 7),
        "section": _SECTION_UNDERSTANDING,
        "fact_key": _fact_key_from_card(card),
    }


def _enrich_detail_from_kl(
    detail: str,
    topic: Mapping[str, Any],
    kl_by_insight: Mapping[str, Mapping[str, Any]],
) -> str:
    if detail and not _is_placeholder_detail(detail):
        return detail
    insight_key = _insight_key_from_topic(topic)
    ins = kl_by_insight.get(insight_key)
    if not isinstance(ins, Mapping):
        return ""
    message = _norm(ins.get("message_ar")) or _norm(ins.get("message"))
    if message and not _is_placeholder_detail(message):
        return message
    return ""


def _build_kl_by_insight(
    kl_insights: Iterable[Mapping[str, Any] | None] | None,
) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for raw in kl_insights or ():
        if not isinstance(raw, Mapping):
            continue
        key = _norm(raw.get("insight_key")) or _norm(raw.get("key"))
        if key and key not in out:
            out[key] = raw
    return out


def _select_understanding_cards(
    selected: list[Mapping[str, Any]],
    *,
    window_days: int,
    max_understanding: int,
    seen_facts: set[str],
) -> list[dict[str, Any]]:
    cards: list[tuple[int, dict[str, Any]]] = []
    for routed in selected:
        card = project_kl_display_card_v1(routed, window_days=window_days)
        projected = _project_understanding_item(card, window_days=window_days)
        if not projected.get("observation_ar") and not projected.get("title_ar"):
            continue
        if _is_placeholder_detail(projected.get("observation_ar")):
            continue
        fact = _norm(projected.get("fact_key"))
        if fact and fact in seen_facts:
            continue
        priority = int(_UNDERSTANDING_PRIORITY.get(_norm(projected.get("insight_key")), 10))
        cards.append((priority, projected))
    cards.sort(key=lambda pair: (-pair[0], _norm(pair[1].get("insight_key"))))
    understanding: list[dict[str, Any]] = []
    for _priority, projected in cards:
        fact = _norm(projected.get("fact_key"))
        if fact:
            if fact in seen_facts:
                continue
            seen_facts.add(fact)
        understanding.append(projected)
        if len(understanding) >= max_understanding:
            break
    return understanding


def _build_quick_nav_v1(nav: Optional[Mapping[str, Any]] = None) -> list[dict[str, Any]]:
    n = nav if isinstance(nav, Mapping) else {}
    # Prefer Knowledge cart_count when provided (HR-7 / MV1-D05).
    if n.get("knowledge_cart_count") is not None:
        active_carts = int(n.get("knowledge_cart_count") or 0)
    else:
        active_carts = int(n.get("active_carts") or 0)
    waiting = int(n.get("waiting_send") or 0)
    return [
        {
            "id": "knowledge",
            "label_ar": "طبقة المعرفة",
            "nav_type": "anchor",
            "href": "#ma-home-understanding",
        },
        {
            "id": "active_carts",
            "label_ar": "السلال النشطة",
            "nav_type": "cart_tab",
            "cart_tab": "all",
            "badge_count": active_carts if active_carts > 0 else 0,
        },
        {
            "id": "completed",
            "label_ar": "الاستردادات المكتملة",
            "nav_type": "cart_tab",
            "cart_tab": "completed",
        },
        {
            "id": "settings",
            "label_ar": "الإعدادات",
            "nav_type": "settings",
            "settings_page": "settings",
        },
        {
            "id": "waiting",
            "label_ar": "بانتظار الإرسال",
            "nav_type": "cart_tab",
            "cart_tab": "waiting",
            "badge_count": waiting if waiting > 0 else 0,
            "visible": waiting > 0,
        },
    ]


def _tier_capabilities_v1() -> dict[str, dict[str, Any]]:
    """Progressive experience tiers — architecture only; Starter active today."""
    return {
        EXPERIENCE_TIER_STARTER: {
            "max_attention_display": HOME_MAX_ATTENTION_DISPLAY,
            "max_understanding_display": HOME_MAX_UNDERSTANDING_DISPLAY,
            "trend_awareness": False,
            "executive_summary": False,
        },
        EXPERIENCE_TIER_GROWTH: {
            "max_attention_display": HOME_MAX_ATTENTION_DISPLAY,
            "max_understanding_display": HOME_MAX_UNDERSTANDING_DISPLAY + 2,
            "trend_awareness": True,
            "executive_summary": False,
        },
        EXPERIENCE_TIER_PRO: {
            # Home Daily Brief: still one primary priority (Constitution V3).
            "max_attention_display": HOME_MAX_ATTENTION_DISPLAY,
            "max_understanding_display": HOME_MAX_UNDERSTANDING_DISPLAY + 2,
            "trend_awareness": True,
            "executive_summary": True,
        },
    }


def _nav_int(nav: Mapping[str, Any], *keys: str) -> int:
    for key in keys:
        if key not in nav:
            continue
        try:
            return max(0, int(nav.get(key) or 0))
        except (TypeError, ValueError):
            continue
    return 0


def _compose_business_health_v1(
    *,
    nav: Mapping[str, Any],
    attention_count: int,
    has_primary_risk: bool,
    understanding_confidence: str,
) -> dict[str, Any]:
    """Section 1 — How is my business today? Status first; never an event list."""
    no_phone = _nav_int(nav, "canonical_no_phone_total")
    active = _nav_int(nav, "knowledge_cart_count", "active_carts")
    attention_required = bool(attention_count > 0 or has_primary_risk or no_phone > 0)

    if has_primary_risk or no_phone > 0:
        status_ar = "يحتاج انتباهك"
        summary_ar = (
            "المتجر يعمل، لكن عائقاً تجارياً يحدّ من استرجاع الإيراد الآن."
        )
        direction_ar = "يتراجع تحت ضغط الاسترجاع"
        direction_key = "declining_pressure"
    elif attention_count > 0:
        status_ar = "يحتاج قراراً"
        summary_ar = "يوجد قرار تجاري واحد يستحق تركيزك اليوم."
        direction_ar = "مستقر مع قرار معلق"
        direction_key = "stable_with_decision"
    else:
        status_ar = "مستقر"
        summary_ar = "لا عائق تجاري بارز اليوم — المتجر في وضع تشغيلي هادئ."
        direction_ar = "مستقر"
        direction_key = "stable"

    conf = _norm(understanding_confidence).lower()
    if conf in ("high", "confirmed"):
        confidence_ar = "عالية"
        confidence = "high"
    elif conf == "medium":
        confidence_ar = "متوسطة"
        confidence = "medium"
    elif attention_required:
        confidence_ar = "متوسطة"
        confidence = "medium"
    else:
        confidence_ar = "أدلة غير كافية"
        confidence = "insufficient"

    evidence_bits: list[str] = []
    if active > 0:
        evidence_bits.append(f"{active} سلة نشطة")
    if no_phone > 0:
        evidence_bits.append(f"{no_phone} بانتظار بيانات تواصل")
    if attention_count > 0:
        evidence_bits.append("قرار واحد اليوم")

    return {
        "title_ar": "صحة العمل",
        "lead_ar": "كيف حال عملي اليوم؟",
        "section_question_ar": "كيف حال عملي اليوم؟",
        "knowledge_role": "business_health",
        "status_ar": status_ar,
        "summary_ar": summary_ar,
        "confidence": confidence,
        "confidence_ar": confidence_ar,
        "attention_required": attention_required,
        "direction_ar": direction_ar,
        "direction_key": direction_key,
        "evidence_summary_ar": " · ".join(evidence_bits) if evidence_bits else "",
        "empty_message_ar": "نجمع صورة أوضح لصحة العمل.",
    }


def _compose_biggest_opportunity_v1(
    *,
    nav: Mapping[str, Any],
    risk_fact_key: str = "",
) -> dict[str, Any]:
    """
    Section 3 — Where is today's best opportunity?

    Evidence-backed only. Never duplicates the primary revenue-risk fact.
    """
    active = _nav_int(nav, "knowledge_cart_count", "active_carts")
    no_phone = _nav_int(nav, "canonical_no_phone_total")
    waiting = _nav_int(nav, "waiting_send")
    recoverable = max(0, active - no_phone)
    risk_fact = _norm(risk_fact_key)

    item: Optional[dict[str, Any]] = None
    if recoverable > 0:
        fact = "fact:opportunity:recoverable_with_contact"
        if fact != risk_fact:
            item = {
                "headline_ar": f"أفضل فرصة اليوم: {recoverable} سلة جاهزة للمتابعة",
                "why_ar": (
                    "هذه السلال لديها بيانات تواصل كافية لبدء أو متابعة الاسترجاع."
                ),
                "evidence_ar": (
                    f"{recoverable} سلة نشطة ببيانات تواصل"
                    + (f" من أصل {active}" if active > 0 else "")
                    + "."
                ),
                "commercial_value_ar": "فرصة أقرب لحماية واستعادة إيراد قابل للتنفيذ.",
                "confidence": "medium" if recoverable >= 3 else "low",
                "fact_key": fact,
                "drilldown_href": "#carts",
                "cta_label_ar": "عرض السلال النشطة",
            }
    if item is None and waiting > 0:
        fact = "fact:opportunity:waiting_send"
        if fact != risk_fact:
            item = {
                "headline_ar": f"أفضل فرصة اليوم: {waiting} سلة بانتظار المتابعة",
                "why_ar": "هناك سلال في مسار الاسترجاع جاهزة لخطوة المتابعة التالية.",
                "evidence_ar": f"{waiting} سلة بانتظار الإرسال أو المتابعة.",
                "commercial_value_ar": "تسريع المتابعة يزيد فرصة إكمال الشراء.",
                "confidence": "medium" if waiting >= 3 else "low",
                "fact_key": fact,
                "drilldown_href": "#carts?tab=waiting",
                "cta_label_ar": "عرض سلال المتابعة",
            }

    return {
        "title_ar": "أكبر فرصة اليوم",
        "lead_ar": "أين أفضل فرصة اليوم؟",
        "section_question_ar": "أين أفضل فرصة اليوم؟",
        "knowledge_role": "opportunity",
        "item": item,
        "items": [item] if item else [],
        "empty_message_ar": "لا فرصة تجارية مؤكدة بأدلة كافية اليوم.",
    }


def _compose_learning_progress_v1(
    *,
    understanding_items: list[Mapping[str, Any]],
    has_primary_risk: bool,
    risk_confidence: str = "",
) -> dict[str, Any]:
    """Section 6 — How is our understanding of the business evolving?"""
    items: list[dict[str, Any]] = []
    if has_primary_risk:
        conf = _norm(risk_confidence).lower() or "high"
        items.append(
            {
                "kind": "pattern_confirmed",
                "progress_ar": "تأكّد نمط يمنع استرجاع الإيراد",
                "detail_ar": (
                    "نقص بيانات التواصل ليس حادثاً منفرداً — بل عائقاً تجارياً متكرراً."
                ),
                "confidence": conf,
                "fact_key": "fact:learning:contact_blocker_pattern",
            }
        )
    for raw in understanding_items[:2]:
        if not isinstance(raw, Mapping):
            continue
        if raw.get("commercial_interpretation_id") and has_primary_risk:
            continue
        conf = _norm(raw.get("confidence")).lower()
        obs = _norm(raw.get("observation_ar") or raw.get("title_ar"))
        if not obs:
            continue
        if conf in ("high", "confirmed"):
            kind = "confidence_increased"
            progress = "ارتفعت ثقة الفهم التجاري"
        elif conf == "medium":
            kind = "new_behaviour"
            progress = "ظهر سلوك تجاري يحتاج متابعة"
        else:
            kind = "more_evidence_required"
            progress = "ما زلنا نحتاج أدلة إضافية"
        items.append(
            {
                "kind": kind,
                "progress_ar": progress,
                "detail_ar": obs,
                "confidence": conf or "insufficient",
                "fact_key": _norm(raw.get("fact_key"))
                or f"fact:learning:{_norm(raw.get('insight_key'))}",
            }
        )
        if len(items) >= 2:
            break
    if not items:
        items.append(
            {
                "kind": "unknown_becoming_known",
                "progress_ar": "الفهم يتراكم مع كل يوم تشغيل",
                "detail_ar": (
                    "كل نشاط في المتجر يغذّي صورة أوضح عن التردد والاسترجاع والشراء."
                ),
                "confidence": "low",
                "fact_key": "fact:learning:accumulating",
            }
        )
    return {
        "title_ar": "تقدّم الفهم",
        "lead_ar": "كيف يتطوّر فهمنا للعمل؟",
        "section_question_ar": "كيف يتطوّر فهمنا للعمل؟",
        "knowledge_role": "learning_progress",
        "items": items[:3],
        "empty_message_ar": "ما زال فهم العمل في طور البناء.",
    }


def _enrich_timeline_why_it_matters_v1(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Section 7 — Timeline stays historical; each event may say why it matters."""
    enriched: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        why = _norm(item.get("why_it_matters_ar"))
        if not why:
            detail = _norm(item.get("detail_ar"))
            headline = _norm(item.get("headline_ar"))
            if detail and detail != headline:
                why = detail
            elif "استرجع" in headline or "استرد" in headline:
                why = "يؤثر مباشرة على مسار استرجاع الإيراد."
            elif "شراء" in headline or "اشتر" in headline:
                why = "يعزّز وضوح التحويل التجاري اليوم."
            elif headline:
                why = "حدث تشغيلي يساعد على قراءة حركة المتجر اليوم."
            else:
                why = ""
        if why:
            item["why_it_matters_ar"] = why
        enriched.append(item)
    return enriched


def _enrich_understanding_business_meaning_v1(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Evolve Knowledge → Business Understanding structure (explain the business)."""
    out: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        observation = _norm(item.get("observation_ar") or item.get("title_ar"))
        evidence = _norm(item.get("evidence_label_ar"))
        meaning = _norm(
            item.get("business_meaning_ar")
            or item.get("impact_ar")
            or item.get("explanation_ar")
        )
        commercial = _norm(
            item.get("commercial_impact_ar")
            or item.get("expected_result_ar")
            or meaning
        )
        direction = _norm(
            item.get("recommended_direction_ar")
            or item.get("cartflow_action_ar")
        )
        if not direction and meaning:
            direction = "راقب هذا النمط في قرارات اليوم التالية."
        item["observation_ar"] = observation
        item["evidence_label_ar"] = evidence
        item["business_meaning_ar"] = meaning
        item["commercial_impact_ar"] = commercial
        item["recommended_direction_ar"] = direction
        # Keep impact_ar as business meaning for older consumers.
        if meaning and not _norm(item.get("impact_ar")):
            item["impact_ar"] = meaning
        item["action_ar"] = ""
        item["knowledge_role"] = "explain"
        item.pop("drilldown_href", None)
        item.pop("cta_label_ar", None)
        out.append(item)
    return out


def finalize_home_daily_business_brief_v1(
    home: dict[str, Any],
    *,
    nav_metadata: Optional[Mapping[str, Any]] = None,
    findings_package: Optional[Mapping[str, Any]] = None,
    commercial_intel_load_db: bool = False,
    commercial_intel_demo: bool = True,
    dash_store: Any = None,
) -> dict[str, Any]:
    """
    Shape composed Home into Constitution V3 Daily Business Brief sections.

    Preserves upstream keys (attention_today / store_understanding / while_away)
    while attaching first-class brief sections and enforcing one-question ownership.
    """
    if not isinstance(home, dict):
        return home
    nav = nav_metadata if isinstance(nav_metadata, Mapping) else {}

    attention = home.get("attention_today")
    if not isinstance(attention, dict):
        attention = {"items": []}
        home["attention_today"] = attention
    att_items = [
        it for it in list(attention.get("items") or []) if isinstance(it, Mapping)
    ]
    # Exactly one primary recommendation.
    if len(att_items) > HOME_MAX_ATTENTION_DISPLAY:
        att_items = att_items[:HOME_MAX_ATTENTION_DISPLAY]
    for idx, it in enumerate(att_items):
        if isinstance(it, dict):
            it["queue_position"] = idx + 1
    attention["items"] = att_items
    attention["count"] = len(att_items)
    attention["max_display"] = HOME_MAX_ATTENTION_DISPLAY
    attention["title_ar"] = "أولوية اليوم"
    attention["lead_ar"] = "ما أهم شيء أفعله اليوم؟"
    attention["section_question_ar"] = "ما أهم شيء أفعله اليوم؟"
    attention["knowledge_role"] = "priority"
    attention["decision_surface"] = True
    attention["empty_message_ar"] = "لا أولوية تجارية واحدة مطلوبة منك الآن."

    understanding = home.get("store_understanding")
    if not isinstance(understanding, dict):
        understanding = {"items": []}
        home["store_understanding"] = understanding
    u_items = _enrich_understanding_business_meaning_v1(
        [dict(it) for it in list(understanding.get("items") or []) if isinstance(it, Mapping)]
    )
    understanding["items"] = u_items
    understanding["title_ar"] = "فهم العمل"
    understanding["lead_ar"] = "ماذا نفهم عن عملك الآن؟"
    understanding["section_question_ar"] = "ماذا نفهم عن عملك الآن؟"
    understanding["knowledge_role"] = "explain"
    understanding["purpose_ar"] = (
        "ملاحظة → دليل → معنى تجاري → أثر تجاري → اتجاه موصى به → ثقة"
    )
    understanding["empty_message_ar"] = (
        "لا فهم تجاري مؤكد بعد — نبني صورة أوضح مع كل يوم تشغيل."
    )

    risk = home.get("biggest_revenue_risk")
    if not isinstance(risk, dict):
        risk = {
            "title_ar": "أكبر خطر على الإيراد",
            "lead_ar": "أين أخسر أكثر الآن؟",
            "section_question_ar": "أين أخسر أكثر الآن؟",
            "knowledge_role": "revenue_risk",
            "item": None,
            "items": [],
            "empty_message_ar": "لا خطر إيراد مؤكد بأدلة كافية الآن.",
        }
        home["biggest_revenue_risk"] = risk
    else:
        risk.setdefault("title_ar", "أكبر خطر على الإيراد")
        risk.setdefault("lead_ar", "أين أخسر أكثر الآن؟")
        risk.setdefault("section_question_ar", "أين أخسر أكثر الآن؟")
        risk["knowledge_role"] = "revenue_risk"

    risk_item = risk.get("item") if isinstance(risk.get("item"), Mapping) else None
    if risk_item is None:
        r_items = [it for it in list(risk.get("items") or []) if isinstance(it, Mapping)]
        risk_item = r_items[0] if r_items else None
    has_primary_risk = bool(risk_item)
    risk_fact = _norm((risk_item or {}).get("fact_key"))
    risk_conf = _norm((risk_item or {}).get("confidence"))

    u_conf = ""
    if u_items:
        u_conf = _norm(u_items[0].get("confidence"))
    if not u_conf and risk_conf:
        u_conf = risk_conf

    home["business_health"] = _compose_business_health_v1(
        nav=nav,
        attention_count=len(att_items),
        has_primary_risk=has_primary_risk,
        understanding_confidence=u_conf,
    )
    home["biggest_opportunity"] = _compose_biggest_opportunity_v1(
        nav=nav,
        risk_fact_key=risk_fact,
    )
    # Opportunity must not reuse risk/priority fact keys; never ship empty headlines.
    opp = home["biggest_opportunity"]
    opp_item = opp.get("item") if isinstance(opp.get("item"), Mapping) else None
    if opp_item and (
        not _norm(opp_item.get("headline_ar"))
        or _norm(opp_item.get("fact_key"))
        in {
            risk_fact,
            "fact:obtain_contact",
            "fact:commercial_interpretation:missing_contact_blocks_recovery_v1",
        }
    ):
        opp["item"] = None
        opp["items"] = []
    elif opp_item:
        opp["items"] = [dict(opp_item)]
    else:
        opp["item"] = None
        opp["items"] = []

    home["learning_progress"] = _compose_learning_progress_v1(
        understanding_items=u_items,
        has_primary_risk=has_primary_risk,
        risk_confidence=risk_conf,
    )

    while_away = home.get("while_away")
    if isinstance(while_away, dict):
        tl_items = _enrich_timeline_why_it_matters_v1(
            [dict(it) for it in list(while_away.get("items") or []) if isinstance(it, Mapping)]
        )
        while_away["items"] = tl_items
        while_away["title_ar"] = "سجل العمل"
        while_away["lead_ar"] = "ما الذي حدث — ولماذا يهم؟"
        while_away["section_question_ar"] = "ما الذي حدث — ولماذا يهم؟"
        while_away["knowledge_role"] = "business_timeline"
        while_away["empty_message_ar"] = "لا أحداث بارزة مسجّلة بعد."

    home["business_understanding"] = understanding
    home["todays_priority"] = attention
    home["business_timeline"] = while_away if isinstance(while_away, dict) else {
        "title_ar": "سجل العمل",
        "items": [],
        "knowledge_role": "business_timeline",
    }
    home["daily_business_brief_v1"] = True
    home["constitution_ref"] = "MERCHANT_DAILY_BUSINESS_BRIEF_CONSTITUTION_V3"

    obs = home.get("observability")
    if not isinstance(obs, dict):
        obs = {}
        home["observability"] = obs
    obs["home_daily_business_brief_v1"] = True
    obs["home_knowledge_redistribution_v1"] = True
    obs["attention_items"] = len(att_items)
    obs["understanding_items"] = len(u_items)
    obs["has_revenue_risk"] = has_primary_risk
    obs["has_opportunity"] = bool(
        isinstance(home.get("biggest_opportunity"), Mapping)
        and home["biggest_opportunity"].get("item")
    )

    # Commercial Intelligence Transition V1 — admit insights that answer
    # commercial questions (products/hesitation/traffic/recovery/…), not counts.
    try:
        from services.home_commercial_intelligence_v1 import (  # noqa: PLC0415
            apply_home_commercial_intelligence_v1,
        )

        apply_home_commercial_intelligence_v1(
            home,
            store_slug=_norm(home.get("store_slug")),
            findings_package=findings_package,
            dash_store=dash_store,
            load_db=bool(commercial_intel_load_db),
            demo_fixture=bool(commercial_intel_demo) and not commercial_intel_load_db,
        )
    except Exception:  # noqa: BLE001
        pass

    # Cross-section semantic composition — one coherent story (no paraphrase fan-out).
    try:
        from services.home_semantic_composition_v1 import (  # noqa: PLC0415
            apply_home_semantic_composition_v1,
        )

        apply_home_semantic_composition_v1(home)
    except Exception:  # noqa: BLE001
        pass

    return home


def _resolve_greeting_date_ar(*, date_ar: str, brief_date: str) -> str:
    """Greeting day must match Brief day (HR-8) — never silently empty."""
    if _norm(date_ar):
        return _norm(date_ar)
    return _norm(brief_date)


def compose_merchant_home_experience_v1(
    *,
    merchant_name_ar: str = "",
    date_ar: str = "",
    brief_date: Optional[str] = None,
    daily_brief: Optional[Mapping[str, Any]] = None,
    kl_insights: Iterable[Mapping[str, Any] | None] | None = None,
    window_days: int = 7,
    nav_metadata: Optional[Mapping[str, Any]] = None,
    experience_tier: str = EXPERIENCE_TIER_STARTER,
    routed_home_feed: Optional[Mapping[str, Any]] = None,
    store_slug: str = "",
    mqic: Any = None,
    findings_package: Optional[Mapping[str, Any]] = None,
    commercial_intel_load_db: bool = False,
    commercial_intel_demo: bool = True,
    dash_store: Any = None,
) -> dict[str, Any]:
    """Compose Merchant Home experience sections from governed upstream payloads."""
    day = brief_date or brief_date_iso()
    brief = daily_brief if isinstance(daily_brief, Mapping) else {}
    tier = _norm(experience_tier) or EXPERIENCE_TIER_STARTER
    tier_caps = _tier_capabilities_v1().get(tier, _tier_capabilities_v1()[EXPERIENCE_TIER_STARTER])
    max_attention = int(tier_caps.get("max_attention_display") or HOME_MAX_ATTENTION_DISPLAY)
    max_understanding = int(
        tier_caps.get("max_understanding_display") or HOME_MAX_UNDERSTANDING_DISPLAY
    )
    kl_by_insight = _build_kl_by_insight(kl_insights)

    seen_facts: set[str] = set()
    # INV-002 WP-6: Activity Timeline is a first-class MQIC consumer.
    from services.identity_authority import get_mqic, mqic_from_caller_store_slug  # noqa: PLC0415
    from services.merchant_timeline_v1 import (  # noqa: PLC0415
        build_merchant_activity_timeline_v1,
    )

    tl_slug = _norm(store_slug)
    tl_mqic = mqic
    if tl_mqic is None and not tl_slug and get_mqic() is None:
        # Pure composition fixtures (no session): still seal via Authority (no DB).
        tl_mqic = mqic_from_caller_store_slug("composition")
    timeline_section = build_merchant_activity_timeline_v1(
        daily_brief=brief,
        store_slug=tl_slug,
        mqic=tl_mqic,
        seen_keys=set(),  # Home owns cross-section fact dedupe below
    )
    raw_while_away = list(timeline_section.get("items") or [])

    # --- Attention: ordered decision queue (PIB-2) — never a passive list ---
    attention_by_decision: dict[str, dict[str, Any]] = {}

    def _append_attention_candidate(raw: Mapping[str, Any]) -> None:
        projected = _project_attention_item(raw)
        why = _enrich_detail_from_kl(projected.get("why_ar") or "", raw, kl_by_insight)
        if why:
            projected["why_ar"] = why
        if _is_placeholder_detail(projected.get("why_ar")):
            projected["why_ar"] = ""
        completed = _complete_attention_decision(projected, raw, kl_by_insight)
        if completed is None:
            return
        op_key = _norm(completed.get("operational_decision_key"))
        if not op_key:
            return
        if op_key in attention_by_decision:
            attention_by_decision[op_key] = _prefer_attention_decision(
                attention_by_decision[op_key], completed
            )
        else:
            attention_by_decision[op_key] = completed

    # Promote contact-wait from achievements before other attention topics (HR-1 / C07).
    for raw in brief.get("achievements") or []:
        if isinstance(raw, Mapping) and _is_blocked_contact_wait(raw):
            _append_attention_candidate(raw)

    for raw in brief.get("attention_items") or []:
        if isinstance(raw, Mapping):
            _append_attention_candidate(raw)

    attention_candidates = list(attention_by_decision.values())
    attention_candidates.sort(
        key=lambda item: (
            int(item.get("priority_class") if item.get("priority_class") is not None else _PRIORITY_PASSIVE),
            0 if _norm(item.get("operational_decision_key")) == "decision:obtain_contact" else 1,
            -int(item.get("decision_count") or 0),
            -int(item.get("routing_priority") or 0),
            _norm(item.get("operational_decision_key")),
        )
    )
    attention = []
    for queue_index, projected in enumerate(attention_candidates):
        for fact in list(projected.get("related_fact_keys") or []):
            if fact:
                seen_facts.add(fact)
        fact = _norm(projected.get("fact_key"))
        if fact:
            seen_facts.add(fact)
        projected["queue_position"] = queue_index + 1
        attention.append(projected)
        if len(attention) >= max_attention:
            break

    # --- Understanding: inherit Knowledge messages (never deny KL evidence) ---
    feed = routed_home_feed or route_merchant_home_knowledge_v1(
        kl_insights=kl_insights,
        max_display_items=max(max_understanding * 3, max_understanding),
    )
    selected = flatten_kl_routed_display_items_v1(
        feed, max_items=max(max_understanding * 3, max_understanding)
    )
    understanding = _select_understanding_cards(
        selected,
        window_days=window_days,
        max_understanding=max_understanding,
        seen_facts=seen_facts,
    )
    # Knowledge Redistribution V1: Understanding explains only — never instructs.
    for item in understanding:
        if isinstance(item, dict):
            item["action_ar"] = ""
            item["knowledge_role"] = "explain"
            item.pop("drilldown_href", None)
            item.pop("cta_label_ar", None)
    understanding_facts = {
        _norm(item.get("fact_key")) for item in understanding if _norm(item.get("fact_key"))
    }

    # --- While-away: true completions only; one fact → one card; no placeholders ---
    while_away: list[dict[str, Any]] = []
    for item in raw_while_away:
        if not isinstance(item, Mapping):
            continue
        topic = dict(item)
        fact = _norm(topic.get("fact_key")) or _fact_key_from_topic(topic)
        if fact in seen_facts or fact in understanding_facts:
            continue
        if _is_blocked_contact_wait(topic):
            continue
        if _is_limit_insight_win(topic):
            continue
        if _is_kl_observation_twin(topic):
            # KL observation twin is not a completion; Understanding owns the message.
            continue
        detail = _enrich_detail_from_kl(
            _norm(topic.get("detail_ar")), topic, kl_by_insight
        )
        if _is_placeholder_detail(detail) or not detail:
            continue
        projected = dict(topic)
        projected["detail_ar"] = detail
        projected["fact_key"] = fact
        seen_facts.add(fact)
        while_away.append(projected)

    attention_count = len(attention)
    empty_calm = not while_away and not attention and not understanding
    greeting_date = _resolve_greeting_date_ar(date_ar=date_ar, brief_date=day)

    home: dict[str, Any] = {
        "version": COMPOSITION_VERSION,
        "experience_tier": tier,
        "tier_capabilities": _tier_capabilities_v1(),
        "brief_date": day,
        "greeting": {
            "greeting_ar": _greeting_ar(),
            "merchant_name_ar": _norm(merchant_name_ar) or "متجرك",
            "date_ar": greeting_date,
        },
        "while_away": {
            "title_ar": "سجل العمل",
            "lead_ar": "ما الذي حدث — ولماذا يهم؟",
            "items": while_away,
            # Merchant language only — never inherit product-name empty copy.
            "empty_message_ar": "لا أحداث بارزة مسجّلة بعد.",
            "store_slug": _norm(timeline_section.get("store_slug")),
            "identity_authority_v1": timeline_section.get("identity_authority_v1"),
            "knowledge_routing_v1": timeline_section.get("knowledge_routing_v1"),
            "section_question_ar": "ما الذي حدث — ولماذا يهم؟",
            "knowledge_role": "business_timeline",
        },
        "attention_today": {
            "title_ar": "أولوية اليوم",
            "lead_ar": "ما أهم شيء أفعله اليوم؟",
            "items": attention,
            "max_display": max_attention,
            "platform_max": MAX_BRIEF_ITEMS,
            "count": attention_count,
            "empty_message_ar": "لا أولوية تجارية واحدة مطلوبة منك الآن.",
            "decision_surface": True,
            "section_question_ar": "ما أهم شيء أفعله اليوم؟",
            "knowledge_role": "priority",
        },
        "store_understanding": {
            "title_ar": "فهم العمل",
            "lead_ar": "ماذا نفهم عن عملك الآن؟",
            "items": understanding,
            "max_display": max_understanding,
            "empty_message_ar": (
                "لا فهم تجاري مؤكد بعد — نبني صورة أوضح مع كل يوم تشغيل."
            ),
            "section_question_ar": "ماذا نفهم عن عملك الآن؟",
            "knowledge_role": "explain",
            "purpose_ar": (
                "ملاحظة → دليل → معنى تجاري → أثر تجاري → اتجاه موصى به → ثقة"
            ),
        },
        "biggest_revenue_risk": {
            "title_ar": "أكبر خطر على الإيراد",
            "lead_ar": "أين أخسر أكثر الآن؟",
            "section_question_ar": "أين أخسر أكثر الآن؟",
            "knowledge_role": "revenue_risk",
            "item": None,
            "items": [],
            "empty_message_ar": "لا خطر إيراد مؤكد بأدلة كافية الآن.",
        },
        "quick_nav": {
            "title_ar": "انتقال سريع",
            "items": _build_quick_nav_v1(nav_metadata),
        },
        "empty_calm": empty_calm,
        "knowledge_routing_v1": {
            "routing_version": _norm(feed.get("routing_version")) or ROUTING_VERSION,
            "surface": SURFACE_MERCHANT_HOME,
            "observability": dict(feed.get("observability") or {}),
        },
        "sources": {
            "daily_brief_version": _norm(brief.get("version")),
            "daily_brief_composer": _norm(brief.get("composer_version")),
            "achievement_count": len(brief.get("achievements") or []),
            "attention_source_count": len(brief.get("attention_items") or brief.get("items") or []),
            "understanding_routed_groups": len(selected),
            "knowledge_cart_count": int(
                (nav_metadata.get("knowledge_cart_count") if isinstance(nav_metadata, Mapping) else 0)
                or 0
            ),
        },
        "observability": {
            "while_away_items": len(while_away),
            "attention_items": len(attention),
            "understanding_items": len(understanding),
            "dedupe_keys": len(seen_facts),
            "pib1_home_truth_alignment": True,
            "pib2_attention_decision_surface": True,
            "pib3_recovery_journey_explainability": True,
            "home_knowledge_redistribution_v1": True,
            "home_daily_business_brief_v1": HOME_DAILY_BUSINESS_BRIEF_V1,
        },
    }

    # Commercial Interpretation Layer V1 — Home consumes governed output only.
    try:
        from services.commercial_interpretation_v1 import (  # noqa: PLC0415
            apply_commercial_interpretation_to_home_v1,
        )

        nav = nav_metadata if isinstance(nav_metadata, Mapping) else {}
        no_phone = nav.get("canonical_no_phone_total")
        try:
            no_phone_i = int(no_phone) if no_phone is not None else None
        except (TypeError, ValueError):
            no_phone_i = None
        active = nav.get("active_carts")
        try:
            active_i = int(active) if active is not None else None
        except (TypeError, ValueError):
            active_i = None
        apply_commercial_interpretation_to_home_v1(
            home,
            store_slug=_norm(store_slug) or _norm(timeline_section.get("store_slug")),
            no_phone_total=no_phone_i,
            active_total=active_i,
            payload={"nav_metadata": nav},
        )
    except Exception:  # noqa: BLE001
        pass

    home["store_slug"] = _norm(store_slug) or _norm(home.get("store_slug"))
    return finalize_home_daily_business_brief_v1(
        home,
        nav_metadata=nav_metadata if isinstance(nav_metadata, Mapping) else {},
        findings_package=findings_package,
        commercial_intel_load_db=commercial_intel_load_db,
        commercial_intel_demo=commercial_intel_demo,
        dash_store=dash_store,
    )


def build_merchant_home_experience_api_payload(
    db_session: Any,
    store_slug: str = "",
    dash_store: Any = None,
    *,
    merchant_name_ar: str = "",
    date_ar: str = "",
    nav_metadata: Optional[Mapping[str, Any]] = None,
    experience_tier: str = EXPERIENCE_TIER_STARTER,
    cookies: Optional[Mapping[str, str]] = None,
    mqic: Any = None,
    headers: Optional[Mapping[str, Any]] = None,
    attach_run_id: str = "",
    attach_start: Any = None,
    attach_start_iso: str = "",
) -> dict[str, Any]:
    """
    Build store home experience by composing certified upstream consumers.

    INV-002 WP-5: tenant key from Platform Identity Authority MQIC — Home
    never resolves store identity independently. Session bind (when cookies
    provided) shares one MQIC with nested Brief + Knowledge.

    INV-002 RC-3: optional Reality Attach composition before bind (headers /
    attach_* inputs) — Authority inputs only; consumers unchanged.
    """
    from services.identity_authority import (  # noqa: PLC0415
        attach_dashboard_home_identity_observability,
        dashboard_home_identity_scope,
        ensure_dashboard_home_mqic,
    )
    from services.identity_authority.reality_attach_composition_v1 import (  # noqa: PLC0415
        merchant_request_identity_bind,
    )

    def _compose_with_mqic(active_mqic: Any) -> dict[str, Any]:
        with dashboard_home_identity_scope(
            store_slug=store_slug, mqic=active_mqic
        ) as bound:
            identity = ensure_dashboard_home_mqic(
                store_slug=store_slug, mqic=bound
            )
            slug = identity.store_slug
            kl_insights: list[Mapping[str, Any]] = []
            window_days = 7
            name_ar = merchant_name_ar
            knowledge_cart_count: Optional[int] = None

            if not _norm(name_ar):
                try:
                    from services.merchant_onboarding_store import (  # noqa: PLC0415
                        merchant_store_display_name,
                    )

                    name_ar = merchant_store_display_name(dash_store) or "متجرك"
                except (ImportError, TypeError, ValueError):
                    name_ar = (
                        _norm(getattr(dash_store, "store_name", None)) or "متجرك"
                    )

            from services.merchant_daily_brief_v1 import (  # noqa: PLC0415
                build_merchant_daily_brief_api_payload,
            )

            brief = build_merchant_daily_brief_api_payload(
                db_session, slug, dash_store, mqic=identity
            )

            try:
                from services.knowledge_layer_v1 import (  # noqa: PLC0415
                    build_knowledge_report,
                )

                report = build_knowledge_report(
                    db_session,
                    slug,
                    window_days=window_days,
                    mqic=identity,
                )
                report_dict = report.to_dict()
                for raw in report_dict.get("insights") or []:
                    if isinstance(raw, Mapping):
                        kl_insights.append(raw)
                metrics = report_dict.get("metrics_snapshot") or report_dict.get("metrics")
                if isinstance(metrics, Mapping) and "cart_count" in metrics:
                    knowledge_cart_count = int(metrics.get("cart_count") or 0)
            except (OSError, TypeError, ValueError, ImportError):
                pass

            nav: dict[str, Any] = dict(nav_metadata or {})
            if knowledge_cart_count is not None:
                nav["knowledge_cart_count"] = knowledge_cart_count
                # Home badge equals Knowledge cart_count for the session.
                nav["active_carts"] = knowledge_cart_count

            findings_package = None
            try:
                from services.business_findings_engine_v1 import (  # noqa: PLC0415
                    run_business_findings_engine_v1,
                )

                findings_package = run_business_findings_engine_v1(
                    store_slug=slug,
                    load_db=True,
                    dash_store=dash_store,
                    demo_fixture=False,
                    window_days=max(14, int(window_days or 7)),
                )
            except Exception:  # noqa: BLE001
                findings_package = None

            composed = compose_merchant_home_experience_v1(
                merchant_name_ar=name_ar,
                date_ar=date_ar,
                brief_date=_norm(brief.get("brief_date")) or brief_date_iso(),
                daily_brief=brief,
                kl_insights=kl_insights,
                window_days=window_days,
                nav_metadata=nav,
                experience_tier=experience_tier,
                store_slug=slug,
                mqic=identity,
                findings_package=findings_package,
                commercial_intel_load_db=False,
                commercial_intel_demo=findings_package is None,
                dash_store=dash_store,
            )
            from services.knowledge_time_authority_v1 import (  # noqa: PLC0415
                knowledge_stamp_now,
            )

            composed["ok"] = True
            composed["generated_at"] = (
                knowledge_stamp_now().replace(microsecond=0).isoformat()
            )
            composed["store_slug"] = slug
            composed["daily_brief_v1"] = brief
            attach_dashboard_home_identity_observability(composed)
            return composed

    if mqic is not None:
        return _compose_with_mqic(mqic)

    if cookies is not None:
        with merchant_request_identity_bind(
            cookies=cookies,
            headers=headers,
            attach_run_id=attach_run_id,
            attach_start=attach_start,
            attach_start_iso=attach_start_iso,
        ) as active_mqic:
            return _compose_with_mqic(active_mqic)

    return _compose_with_mqic(None)


__all__ = [
    "COMPOSITION_VERSION",
    "EXPERIENCE_TIER_GROWTH",
    "EXPERIENCE_TIER_PRO",
    "EXPERIENCE_TIER_STARTER",
    "HOME_MAX_ATTENTION_DISPLAY",
    "HOME_MAX_UNDERSTANDING_DISPLAY",
    "build_merchant_home_experience_api_payload",
    "compose_merchant_home_experience_v1",
]
