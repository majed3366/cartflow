# -*- coding: utf-8 -*-
"""
Knowledge Producer Metadata v1 — standardized publisher contract helpers.

Shared deterministic knowledge_id minting, traceability, and producer metadata
for governed knowledge producers (Explanation, Decision, Knowledge Layer).

Does not implement Knowledge Routing, routing_priority, or surface selection.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

KNOWLEDGE_METADATA_VERSION = "v1"

PREFIX_EXPL = "expl"
PREFIX_DEC = "dec"
PREFIX_KL = "kl"

DOMAIN_RECOVERY = "recovery"
DOMAIN_UNDERSTANDING = "understanding"
DOMAIN_DECISION = "decision"
DOMAIN_OPERATIONAL = "operational"

VISIBILITY_MERCHANT = True
VISIBILITY_ADMIN = True
VISIBILITY_MERCHANT_ONLY = True
VISIBILITY_ADMIN_ONLY = False

NARRATIVE_FACT = "fact"
NARRATIVE_ACHIEVEMENT = "achievement"
NARRATIVE_ATTENTION = "attention"
NARRATIVE_TREND = "trend"
NARRATIVE_CLOSURE = "closure"
NARRATIVE_DIAGNOSTIC = "diagnostic"

PRODUCER_EXPLANATION = "merchant_explanation_v1"
PRODUCER_DECISION = "merchant_decision_layer_v1"
PRODUCER_KL = "knowledge_layer_v1"

_ORIGIN_EXPLANATION = "merchant_explanation"
_ORIGIN_DECISION = "merchant_decision"
_ORIGIN_KL_INSIGHT = "knowledge_insight"

_SEGMENT_RE = re.compile(r"[^a-z0-9_.-]+")

# knowledge_event_type → foundation knowledge_type
_EVENT_TO_KNOWLEDGE_TYPE: dict[str, str] = {
    "cart_active": "cart_lifecycle_event",
    "recovery_scheduled": "recovery_scheduled",
    "message_sent_waiting_reply": "message_sent_waiting_reply",
    "customer_replied": "cart_lifecycle_event",
    "customer_engaged_continuation": "cart_lifecycle_event",
    "customer_returned_to_site": "cart_lifecycle_event",
    "return_after_message_waiting_purchase": "return_without_purchase",
    "followup_scheduled": "recovery_scheduled",
    "recovery_needs_attention": "recovery_needs_attention",
    "purchase_confirmed": "purchase_confirmed",
    "cart_archived": "cart_lifecycle_event",
    "recovery_sequence_complete": "cart_lifecycle_event",
    "lifecycle_unavailable": "cart_lifecycle_event",
}

# explanation_id → default narrative_role
_EXPLANATION_NARRATIVE_ROLE: dict[str, str] = {
    "purchase_confirmed": NARRATIVE_CLOSURE,
    "return_without_purchase": NARRATIVE_FACT,
    "needs_merchant_attention": NARRATIVE_ATTENTION,
    "recovery_followup_complete": NARRATIVE_FACT,
    "cart_archived": NARRATIVE_CLOSURE,
}

# decision_id prefix → explanation_id link
_DECISION_EXPLANATION_LINK: dict[str, str] = {
    "decision_monitor_return": "return_without_purchase",
    "decision_contact_customer": "needs_merchant_attention",
    "decision_obtain_contact": "needs_merchant_attention",
    "decision_fix_channel": "needs_merchant_attention",
}

# insight_key → knowledge_type
_INSIGHT_KNOWLEDGE_TYPE: dict[str, str] = {
    "hesitation_top_reason": "hesitation_pattern",
    "hesitation_distribution": "hesitation_pattern",
    "hesitation_insufficient_sample": "hesitation_pattern",
    "conversion_cart_to_purchase": "merchant_achievement",
    "recovery_activity_summary": "merchant_achievement",
    "recovery_bottleneck": "merchant_achievement",
    "recovery_insufficient_sample": "operational_health",
    "traffic_visitor_unavailable": "operational_health",
    "traffic_cart_demand_trend": "operational_health",
    "conversion_funnel_gaps": "operational_health",
    "conversion_no_carts": "operational_health",
    "store_health_overview": "operational_health",
}

_KL_ELIGIBLE_SURFACES = ("knowledge_layer", "daily_brief")
_EXPL_ELIGIBLE_SURFACES = ("cart_detail", "cart_row_chip")
_DECISION_ELIGIBLE_SURFACES_DEFAULT = ("daily_brief", "cart_detail", "merchant_home")

_PROOF_CONFIDENCE_TO_GOV = {
    "confirmed": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "unknown": "insufficient",
    "insufficient": "insufficient",
}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sanitize_knowledge_segment(value: Any) -> str:
    """Normalize one knowledge_id segment (lowercase, stable, safe)."""
    raw = _norm(value).lower()
    if not raw:
        return "unknown"
    raw = raw.replace("/", "_").replace(" ", "_")
    raw = _SEGMENT_RE.sub("_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")
    return raw or "unknown"


def build_knowledge_id(
    *,
    prefix: str,
    type_key: str,
    scope: str,
    subject_key: str,
) -> str:
    """
    Deterministic knowledge_id: {prefix}:{type}:{scope}:{subject_key}

    Never random; stable across regeneration when inputs unchanged.
    """
    return ":".join(
        (
            sanitize_knowledge_segment(prefix),
            sanitize_knowledge_segment(type_key),
            sanitize_knowledge_segment(scope),
            sanitize_knowledge_segment(subject_key),
        )
    )


def resolve_store_scope(
    *,
    store_slug: str = "",
    recovery_key: str = "",
    abandoned_cart_id: Any = None,
) -> str:
    """Resolve store scope segment for knowledge_id."""
    slug = sanitize_knowledge_segment(store_slug)
    if slug != "unknown":
        return slug
    rk = _norm(recovery_key)
    if rk:
        head = rk.split(":")[0]
        seg = sanitize_knowledge_segment(head)
        if seg != "unknown":
            return seg
    cart_id = _norm(abandoned_cart_id)
    if cart_id:
        return f"cart_{sanitize_knowledge_segment(cart_id)}"
    return "unknown"


def resolve_subject_key(
    *,
    recovery_key: str = "",
    merge_key: str = "",
    insight_key: str = "",
    abandoned_cart_id: Any = None,
) -> str:
    """Resolve primary subject key for knowledge_id."""
    for candidate in (recovery_key, merge_key, insight_key):
        seg = sanitize_knowledge_segment(candidate)
        if seg != "unknown":
            return seg
    cart_id = _norm(abandoned_cart_id)
    if cart_id:
        return f"cart_{sanitize_knowledge_segment(cart_id)}"
    return "unknown"


def build_traceability_v1(
    *,
    origin_layer: str,
    origin_identifier: str,
    source_records: list[str],
    producer_version: str,
    created_from: list[str],
    published_at: Optional[str] = None,
) -> dict[str, Any]:
    """Traceability block — answers 'Why does this knowledge exist?'"""
    records = [r for r in (_norm(x) for x in source_records) if r]
    created = [c for c in (_norm(x) for x in created_from) if c]
    return {
        "origin_layer": _norm(origin_layer) or "unknown",
        "origin_identifier": _norm(origin_identifier) or "unknown",
        "source_records": records,
        "producer_version": _norm(producer_version) or KNOWLEDGE_METADATA_VERSION,
        "created_from": created or ["unknown"],
        "published_at": published_at or _utc_now_iso(),
    }


def _gov_confidence_from_proof(proof: Optional[Mapping[str, Any]]) -> str:
    if not isinstance(proof, Mapping):
        return "medium"
    raw = _norm(proof.get("confidence")).lower()
    return _PROOF_CONFIDENCE_TO_GOV.get(raw, "medium")


def _expiration_rule_from_decision(expiration: Any) -> dict[str, Any]:
    if isinstance(expiration, Mapping):
        ttl = expiration.get("ttl_hours")
    else:
        ttl = None
    return {
        "ttl_hours": ttl,
        "resolve_on_purchase": True,
        "resolve_on_archive": True,
    }


def _default_expiration_rule(*, resolve_on_purchase: bool = True) -> dict[str, Any]:
    return {
        "ttl_hours": None,
        "resolve_on_purchase": resolve_on_purchase,
        "resolve_on_archive": True,
    }


def _map_event_to_knowledge_type(knowledge_event_type: str, explanation_id: str) -> str:
    event = _norm(knowledge_event_type)
    if event in _EVENT_TO_KNOWLEDGE_TYPE:
        return _EVENT_TO_KNOWLEDGE_TYPE[event]
    expl = _norm(explanation_id)
    if expl in _EXPLANATION_NARRATIVE_ROLE or expl:
        return expl.replace("-", "_") if expl else "cart_lifecycle_event"
    return "cart_lifecycle_event"


def _narrative_role_for_explanation(explanation_id: str) -> str:
    return _EXPLANATION_NARRATIVE_ROLE.get(_norm(explanation_id), NARRATIVE_FACT)


def _link_explanation_id_for_decision(decision_id: str) -> str:
    did = _norm(decision_id)
    for prefix, expl_id in _DECISION_EXPLANATION_LINK.items():
        if did == prefix or did.startswith(f"{prefix}:"):
            return expl_id
    return ""


def _attention_for_decision_class(decision_class: str, merchant_action: str) -> str:
    cls = _norm(decision_class)
    action = _norm(merchant_action).lower()
    if cls == "critical_action":
        return "urgent"
    if cls in ("needs_attention", "suggested_action"):
        return "attention"
    if action == "monitor":
        return "informational"
    if cls == "observation":
        return "informational"
    return "informational"


def _narrative_role_for_decision(decision_class: str, merchant_action: str) -> str:
    cls = _norm(decision_class)
    action = _norm(merchant_action).lower()
    if cls == "observation" or action == "monitor":
        return NARRATIVE_ACHIEVEMENT
    if cls in ("needs_attention", "suggested_action", "critical_action"):
        return NARRATIVE_ATTENTION
    return NARRATIVE_FACT


def _knowledge_type_for_insight(insight_key: str, category: str) -> str:
    key = _norm(insight_key)
    if key in _INSIGHT_KNOWLEDGE_TYPE:
        return _INSIGHT_KNOWLEDGE_TYPE[key]
    cat = _norm(category)
    if cat == "hesitation":
        return "hesitation_pattern"
    if cat == "recovery":
        return "merchant_achievement"
    return "operational_health"


def _narrative_role_for_insight(insight_key: str, category: str) -> str:
    ktype = _knowledge_type_for_insight(insight_key, category)
    if ktype == "hesitation_pattern":
        return NARRATIVE_TREND
    if ktype == "merchant_achievement":
        return NARRATIVE_ACHIEVEMENT
    return NARRATIVE_FACT


def _attention_for_insight(severity: str, confidence: str) -> str:
    sev = _norm(severity)
    conf = _norm(confidence)
    if conf == "insufficient":
        return "none"
    if sev == "warning":
        return "attention"
    return "informational"


def enrich_explanation_knowledge_metadata_v1(
    expl: dict[str, Any],
    *,
    store_slug: str = "",
    recovery_key: str = "",
    abandoned_cart_id: Any = None,
    proof: Optional[Mapping[str, Any]] = None,
    lifecycle_state: str = "",
) -> dict[str, Any]:
    """Attach standardized producer metadata to merchant_explanation_v1 (additive)."""
    explanation_id = _norm(expl.get("explanation_id"))
    knowledge_event_type = _norm(expl.get("knowledge_event_type"))
    scope = resolve_store_scope(
        store_slug=store_slug,
        recovery_key=recovery_key,
        abandoned_cart_id=abandoned_cart_id,
    )
    subject = resolve_subject_key(
        recovery_key=recovery_key,
        abandoned_cart_id=abandoned_cart_id,
    )
    knowledge_type = _map_event_to_knowledge_type(knowledge_event_type, explanation_id)
    knowledge_id = build_knowledge_id(
        prefix=PREFIX_EXPL,
        type_key=explanation_id or knowledge_type,
        scope=scope,
        subject_key=subject,
    )
    evidence_ids: list[str] = []
    proof_sources: list[str] = []
    if isinstance(proof, Mapping):
        eid = _norm(proof.get("evidence_id"))
        if eid:
            evidence_ids.append(eid)
        ps = _norm(proof.get("proof_source"))
        if ps:
            proof_sources.append(ps)
    if recovery_key and recovery_key not in proof_sources:
        proof_sources.append(_norm(recovery_key))

    traceability = build_traceability_v1(
        origin_layer=_ORIGIN_EXPLANATION,
        origin_identifier=explanation_id or knowledge_event_type,
        source_records=proof_sources or ([_norm(lifecycle_state)] if lifecycle_state else []),
        producer_version=expl.get("version") or KNOWLEDGE_METADATA_VERSION,
        created_from=[
            "customer_lifecycle_state",
            "merchant_proof_surface_v1",
            "merchant_explanation_v1",
        ],
    )

    expl["knowledge_version"] = KNOWLEDGE_METADATA_VERSION
    expl["knowledge_id"] = knowledge_id
    expl["knowledge_type"] = knowledge_type
    expl["source_domain"] = DOMAIN_RECOVERY
    expl["evidence_ids"] = evidence_ids
    expl["proof_sources"] = proof_sources
    expl["decision_ids"] = []
    expl["explanation_id"] = explanation_id
    expl["confidence"] = _gov_confidence_from_proof(proof)
    if "admin_visibility" not in expl:
        expl["admin_visibility"] = VISIBILITY_ADMIN_ONLY
    expl["aggregation_key"] = subject
    expl["narrative_role"] = _narrative_role_for_explanation(explanation_id)
    expl["expiration_rule"] = _default_expiration_rule(
        resolve_on_purchase=explanation_id != "cart_archived",
    )
    expl["traceability"] = traceability
    return expl


def _decision_aggregation_key_v1(decision: Mapping[str, Any]) -> str:
    """Cross-cart aggregation key from decision metadata fields only."""
    decision_id = _norm(decision.get("decision_id"))
    family = decision_id.split(":")[0] if ":" in decision_id else decision_id
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
    if family == "decision_kl_observation":
        return f"{family}:{evidence}:{insight_key or goal}"
    return f"{family}:{action_key}:{goal}:{evidence}"


def enrich_decision_knowledge_metadata_v1(
    decision: dict[str, Any],
    *,
    store_slug: str = "",
    recovery_key: str = "",
    explanation_id: str = "",
) -> dict[str, Any]:
    """Attach standardized producer metadata to one merchant decision (additive)."""
    decision_id = _norm(decision.get("decision_id"))
    merge_key = _norm(decision.get("merge_key"))
    scope = resolve_store_scope(store_slug=store_slug, recovery_key=recovery_key)
    subject = resolve_subject_key(recovery_key=recovery_key, merge_key=merge_key)
    linked_expl = explanation_id or _link_explanation_id_for_decision(decision_id)
    family = decision_id.split(":")[0] if ":" in decision_id else decision_id
    knowledge_id = build_knowledge_id(
        prefix=PREFIX_DEC,
        type_key=family or "decision",
        scope=scope,
        subject_key=merge_key or subject,
    )
    proof_sources = list(decision.get("proof_sources") or [])
    decision_ids = [decision_id] if decision_id else []
    decision_class = _norm(decision.get("decision_class"))
    merchant_action = _norm(decision.get("merchant_action"))

    traceability = build_traceability_v1(
        origin_layer=_ORIGIN_DECISION,
        origin_identifier=decision_id,
        source_records=proof_sources,
        producer_version=KNOWLEDGE_METADATA_VERSION,
        created_from=[
            "merchant_proof_surface_v1",
            "merchant_decision_layer_v1",
        ],
    )
    if linked_expl:
        traceability["linked_explanation_id"] = linked_expl

    decision["knowledge_version"] = KNOWLEDGE_METADATA_VERSION
    decision["knowledge_id"] = knowledge_id
    decision["knowledge_type"] = family or "recovery_needs_attention"
    decision["source_domain"] = DOMAIN_DECISION
    decision["explanation_id"] = linked_expl
    decision["decision_ids"] = decision_ids
    decision["eligible_surfaces"] = list(_DECISION_ELIGIBLE_SURFACES_DEFAULT)
    decision["merchant_visibility"] = VISIBILITY_MERCHANT_ONLY
    decision["admin_visibility"] = VISIBILITY_ADMIN_ONLY
    decision["attention_level"] = _attention_for_decision_class(decision_class, merchant_action)
    decision["action_required"] = merchant_action == "execute"
    decision["aggregation_key"] = _decision_aggregation_key_v1(decision)
    decision["narrative_role"] = _narrative_role_for_decision(decision_class, merchant_action)
    decision["expiration_rule"] = _expiration_rule_from_decision(decision.get("expiration"))
    decision["traceability"] = traceability
    return decision


def enrich_kl_insight_knowledge_metadata_v1(
    insight: dict[str, Any],
    *,
    store_slug: str,
    window_days: int,
) -> dict[str, Any]:
    """Attach standardized producer metadata to one KL insight (additive)."""
    insight_key = _norm(insight.get("insight_key"))
    category = _norm(insight.get("category"))
    scope = sanitize_knowledge_segment(store_slug)
    window_label = f"{int(window_days)}d"
    knowledge_type = _knowledge_type_for_insight(insight_key, category)
    knowledge_id = build_knowledge_id(
        prefix=PREFIX_KL,
        type_key=insight_key or knowledge_type,
        scope=scope,
        subject_key=window_label,
    )
    evidence_ids: list[str] = []
    eid = _norm(insight.get("evidence_id"))
    if eid:
        evidence_ids.append(eid)
    proof_sources = [f"insight_key:{insight_key}"] if insight_key else []
    source_tables = insight.get("source_tables") or []
    source_records = proof_sources + [str(t) for t in source_tables if t]

    traceability = build_traceability_v1(
        origin_layer=_ORIGIN_KL_INSIGHT,
        origin_identifier=insight_key,
        source_records=source_records,
        producer_version=KNOWLEDGE_METADATA_VERSION,
        created_from=[
            "knowledge_metrics_v1",
            "knowledge_insights_v1",
        ],
    )

    insight["knowledge_version"] = KNOWLEDGE_METADATA_VERSION
    insight["knowledge_id"] = knowledge_id
    insight["knowledge_type"] = knowledge_type
    insight["source_domain"] = (
        DOMAIN_UNDERSTANDING if category == "hesitation" else DOMAIN_OPERATIONAL
    )
    insight["evidence_ids"] = evidence_ids
    insight["proof_sources"] = proof_sources
    insight["decision_ids"] = []
    insight["explanation_id"] = ""
    insight["confidence"] = _norm(insight.get("confidence")) or "insufficient"
    insight["merchant_visibility"] = VISIBILITY_MERCHANT_ONLY
    insight["admin_visibility"] = VISIBILITY_ADMIN_ONLY
    insight["eligible_surfaces"] = list(_KL_ELIGIBLE_SURFACES)
    insight["action_required"] = False
    insight["attention_level"] = _attention_for_insight(
        _norm(insight.get("severity")),
        _norm(insight.get("confidence")),
    )
    insight["aggregation_key"] = f"{insight_key}:{window_label}"
    insight["narrative_role"] = _narrative_role_for_insight(insight_key, category)
    insight["expiration_rule"] = _default_expiration_rule(resolve_on_purchase=False)
    insight["traceability"] = traceability
    return insight


def enrich_knowledge_report_producer_metadata_v1(
    target: Mapping[str, Any] | dict[str, Any],
) -> None:
    """Attach producer metadata to all insights in a KL report payload."""
    if not isinstance(target, dict):
        return
    store_slug = _norm(target.get("store_slug"))
    try:
        window_days = int(target.get("window_days") or 7)
    except (TypeError, ValueError):
        window_days = 7
    insights = target.get("insights")
    if not isinstance(insights, list):
        return
    for idx, raw in enumerate(insights):
        if not isinstance(raw, dict):
            continue
        enrich_kl_insight_knowledge_metadata_v1(
            raw,
            store_slug=store_slug,
            window_days=window_days,
        )
        insights[idx] = raw
    target["knowledge_producer_metadata_v1"] = {
        "version": KNOWLEDGE_METADATA_VERSION,
        "producer": PRODUCER_KL,
        "insight_count": len(insights),
    }


def validate_knowledge_metadata_v1(item: Mapping[str, Any]) -> list[str]:
    """Return missing required publisher metadata field names."""
    required = (
        "knowledge_version",
        "knowledge_id",
        "knowledge_type",
        "source_domain",
        "evidence_ids",
        "proof_sources",
        "decision_ids",
        "explanation_id",
        "confidence",
        "merchant_visibility",
        "admin_visibility",
        "eligible_surfaces",
        "action_required",
        "attention_level",
        "aggregation_key",
        "narrative_role",
        "expiration_rule",
        "traceability",
    )
    missing: list[str] = []
    for key in required:
        if key not in item:
            missing.append(key)
    trace = item.get("traceability")
    if not isinstance(trace, Mapping):
        missing.append("traceability.origin_layer")
    else:
        for tk in (
            "origin_layer",
            "origin_identifier",
            "source_records",
            "producer_version",
            "created_from",
        ):
            if tk not in trace:
                missing.append(f"traceability.{tk}")
    return missing


__all__ = [
    "KNOWLEDGE_METADATA_VERSION",
    "PREFIX_DEC",
    "PREFIX_EXPL",
    "PREFIX_KL",
    "build_knowledge_id",
    "build_traceability_v1",
    "enrich_decision_knowledge_metadata_v1",
    "enrich_explanation_knowledge_metadata_v1",
    "enrich_kl_insight_knowledge_metadata_v1",
    "enrich_knowledge_report_producer_metadata_v1",
    "resolve_store_scope",
    "resolve_subject_key",
    "sanitize_knowledge_segment",
    "validate_knowledge_metadata_v1",
]
