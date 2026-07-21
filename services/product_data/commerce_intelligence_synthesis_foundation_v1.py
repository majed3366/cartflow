# -*- coding: utf-8 -*-
"""
Commerce Intelligence Synthesis Foundation V1.

Cross-domain pattern qualification from governed source contracts only.
No Guidance, Presentation, UI, AI, or action execution.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CommerceIntelligenceSynthesis
from schema_commerce_intelligence_synthesis_v1 import (
    ensure_commerce_intelligence_synthesis_schema,
)
from services.product_data.commerce_intelligence_synthesis_flag_v1 import (
    commerce_intelligence_synthesis_v1_enabled,
)
from services.product_data.commerce_intelligence_synthesis_rule_registry_v1 import (
    active_synthesis_rules_v1,
    rule_registry_valid_v1,
)
from services.product_data.commerce_intelligence_synthesis_source_registry_v1 import (
    source_registry_valid_v1,
)
from services.product_data.commerce_intelligence_synthesis_sources_v1 import (
    knowledge_index_v1,
    load_synthesis_sources_v1,
    purchase_count_for_product_v1,
)
from services.product_data.commerce_intelligence_synthesis_types_v1 import (
    DIRECTION_COMPARISON,
    DIRECTION_CONFLICTING,
    DIRECTION_GAP,
    DIRECTION_INFLUENCE_BOUNDARY,
    DIRECTION_INSUFFICIENT,
    DIRECTION_OBSERVING,
    DIRECTION_REPEATED_INTEREST,
    DIRECTION_RETURN_WITHOUT_PURCHASE,
    GENERATION_VERSION_V1,
    OUTPUT_CONTRACT_VERSION_V1,
    PATTERN_CONFLICTING_EVIDENCE,
    PATTERN_DISCOUNT_MESSAGE_WEAKNESS,
    PATTERN_HIGH_TRAFFIC_WEAK_CONVERSION,
    PATTERN_INSUFFICIENT_EVIDENCE,
    PATTERN_PRODUCT_INTEREST_WITHOUT_PURCHASE,
    PATTERN_RECOVERY_INFLUENCE_BOUNDARY,
    PATTERN_REPEATED_INTEREST,
    PATTERN_SHIPPING_HESITATION_RECOVERY,
    PATTERN_VIP_FOLLOWUP_OUTCOME,
    PATTERN_WHATSAPP_RETURN_WITHOUT_PURCHASE,
    RECOVERY_CLASSIFICATIONS,
    RULE_REGISTRY_VERSION_V1,
    SOURCE_CONTRACT_REGISTRY_VERSION_V1,
    STATE_BLOCKED,
    STATE_CONFLICTING,
    STATE_FAILED,
    STATE_INSUFFICIENT,
    STATE_OBSERVING,
    STATE_QUALIFIED,
    STATE_SUPERSEDED,
    SUBJECT_HESITATION,
    SUBJECT_PRODUCT,
    SUBJECT_RECOVERY_STRATEGY,
    SUBJECT_STORE,
    SUBJECT_VIP_COHORT,
    SYNTHESIS_VERSION_V1,
    WINDOW_LENGTH_DAYS,
)

log = logging.getLogger("cartflow")


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _floor_second(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0)


def _as_of_key(dt: datetime) -> str:
    return _floor_second(dt).strftime("%Y%m%d%H%M%S")


def _sha(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        raw = payload
    else:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_iso(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _floor_second(value)
    try:
        return _floor_second(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def _domains_ok(rule: dict[str, Any], available: set[str]) -> tuple[bool, list[str]]:
    required = list(rule.get("required_source_domains") or [])
    missing = [d for d in required if d not in available]
    return (len(missing) == 0, missing)


def _build_synthesis(
    *,
    store_slug: str,
    rule: dict[str, Any],
    subject_type: str,
    subject_id: str,
    time_window_key: str,
    window_start: datetime,
    window_end: datetime,
    synthesis_state: str,
    pattern_direction: str,
    commercial_domain: str,
    source_domains: list[str],
    source_record_ids: list[str],
    source_contributions: dict[str, Any],
    required_source_domains: list[str],
    missing_source_domains: list[str],
    known_facts: list[str],
    unknown_facts: list[str],
    conflicting_facts: list[str],
    prohibited_claims: list[str],
    supporting_evidence_count: int,
    contradicting_evidence_count: int,
    sample_size: int,
    minimum_sample_size: int,
    evidence_coverage: float,
    confidence_input: dict[str, Any],
    significance_input: dict[str, Any],
    commercial_relevance_input: dict[str, Any],
    synthesis_summary_key: str,
    comparison_subject_type: str = "",
    comparison_subject_id: str = "",
    failure_reason: str = "",
) -> dict[str, Any]:
    rule_key = str(rule["synthesis_rule_key"])
    rule_version = str(rule.get("version") or "1")
    pattern_type = str(rule["pattern_type"])
    synthesis_key = _sha(
        {
            "v": SYNTHESIS_VERSION_V1,
            "store": store_slug,
            "rule": rule_key,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "comparison": f"{comparison_subject_type}:{comparison_subject_id}",
            "window": time_window_key,
            "contract": OUTPUT_CONTRACT_VERSION_V1,
            "rule_version": rule_version,
        }
    )[:32]
    input_fingerprint = _sha(
        {
            "sources": sorted(source_domains),
            "source_record_ids": sorted(source_record_ids),
            "known": known_facts,
            "unknown": unknown_facts,
            "conflict": conflicting_facts,
            "state": synthesis_state,
            "sample": sample_size,
            "window": time_window_key,
            "as_of": window_end.isoformat(sep=" "),
        }
    )
    synthesis_fingerprint = _sha(
        {
            "synthesis_key": synthesis_key,
            "state": synthesis_state,
            "pattern_type": pattern_type,
            "pattern_direction": pattern_direction,
            "known": known_facts,
            "unknown": unknown_facts,
            "prohibited": prohibited_claims,
            "contributions": source_contributions,
            "input_fingerprint": input_fingerprint,
        }
    )
    synthesis_id = _sha(
        {
            "key": synthesis_key,
            "fp": synthesis_fingerprint,
            "gen": GENERATION_VERSION_V1,
        }
    )[:32]
    return {
        "synthesis_id": synthesis_id,
        "store_slug": store_slug,
        "synthesis_key": synthesis_key,
        "synthesis_rule_key": rule_key,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "comparison_subject_type": comparison_subject_type,
        "comparison_subject_id": comparison_subject_id,
        "time_window_key": time_window_key,
        "window_start": window_start.isoformat(sep=" "),
        "window_end": window_end.isoformat(sep=" "),
        "synthesis_state": synthesis_state,
        "pattern_type": pattern_type,
        "pattern_direction": pattern_direction,
        "commercial_domain": commercial_domain,
        "source_domains": source_domains,
        "source_record_ids": source_record_ids,
        "source_contributions": source_contributions,
        "required_source_domains": required_source_domains,
        "missing_source_domains": missing_source_domains,
        "known_facts": known_facts,
        "unknown_facts": unknown_facts,
        "conflicting_facts": conflicting_facts,
        "prohibited_claims": prohibited_claims,
        "supporting_evidence_count": supporting_evidence_count,
        "contradicting_evidence_count": contradicting_evidence_count,
        "sample_size": sample_size,
        "minimum_sample_size": minimum_sample_size,
        "evidence_coverage": evidence_coverage,
        "confidence_input": confidence_input,
        "significance_input": significance_input,
        "commercial_relevance_input": commercial_relevance_input,
        "synthesis_summary_key": synthesis_summary_key,
        "input_fingerprint": input_fingerprint,
        "synthesis_fingerprint": synthesis_fingerprint,
        "rule_version": rule_version,
        "contract_version": OUTPUT_CONTRACT_VERSION_V1,
        "synthesis_version": SYNTHESIS_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "rule_registry_version": RULE_REGISTRY_VERSION_V1,
        "source_contract_registry_version": SOURCE_CONTRACT_REGISTRY_VERSION_V1,
        "failure_reason": failure_reason,
        "valid_from": window_end.isoformat(sep=" "),
        "valid_until": (window_end + timedelta(days=WINDOW_LENGTH_DAYS.get(time_window_key, 7))).isoformat(
            sep=" "
        ),
        "is_current": True,
    }


def _blocked(
    *,
    store_slug: str,
    rule: dict[str, Any],
    subject_type: str,
    subject_id: str,
    time_window_key: str,
    window_start: datetime,
    window_end: datetime,
    missing: list[str],
    reason: str,
) -> dict[str, Any]:
    return _build_synthesis(
        store_slug=store_slug,
        rule=rule,
        subject_type=subject_type,
        subject_id=subject_id,
        time_window_key=time_window_key,
        window_start=window_start,
        window_end=window_end,
        synthesis_state=STATE_BLOCKED,
        pattern_direction=DIRECTION_OBSERVING,
        commercial_domain="cross_channel",
        source_domains=[],
        source_record_ids=[],
        source_contributions={},
        required_source_domains=list(rule.get("required_source_domains") or []),
        missing_source_domains=missing,
        known_facts=[],
        unknown_facts=["required_canonical_source_unavailable"],
        conflicting_facts=[],
        prohibited_claims=list(rule.get("prohibited_claims") or []),
        supporting_evidence_count=0,
        contradicting_evidence_count=0,
        sample_size=0,
        minimum_sample_size=int(rule.get("minimum_sample_size") or 0),
        evidence_coverage=0.0,
        confidence_input={"source_agreement": 0.0, "blocked": True},
        significance_input={"blocked": True},
        commercial_relevance_input={"blocked": True},
        synthesis_summary_key=f"{rule['synthesis_rule_key']}.blocked",
        failure_reason=reason,
    )


def _failed(
    *,
    store_slug: str,
    rule: dict[str, Any],
    subject_type: str,
    subject_id: str,
    time_window_key: str,
    window_start: datetime,
    window_end: datetime,
    reason: str,
) -> dict[str, Any]:
    return _build_synthesis(
        store_slug=store_slug,
        rule=rule,
        subject_type=subject_type,
        subject_id=subject_id,
        time_window_key=time_window_key,
        window_start=window_start,
        window_end=window_end,
        synthesis_state=STATE_FAILED,
        pattern_direction=DIRECTION_OBSERVING,
        commercial_domain="cross_channel",
        source_domains=[],
        source_record_ids=[],
        source_contributions={},
        required_source_domains=list(rule.get("required_source_domains") or []),
        missing_source_domains=[],
        known_facts=[],
        unknown_facts=["technical_failure_prevented_synthesis"],
        conflicting_facts=[],
        prohibited_claims=list(rule.get("prohibited_claims") or []),
        supporting_evidence_count=0,
        contradicting_evidence_count=0,
        sample_size=0,
        minimum_sample_size=int(rule.get("minimum_sample_size") or 0),
        evidence_coverage=0.0,
        confidence_input={"failed": True},
        significance_input={"failed": True},
        commercial_relevance_input={"failed": True},
        synthesis_summary_key=f"{rule['synthesis_rule_key']}.failed",
        failure_reason=reason,
    )


def _eval_product_interest(
    rule: dict[str, Any],
    *,
    store_slug: str,
    sources: dict[str, Any],
    kidx: dict[str, Any],
    window_start: datetime,
    window_end: datetime,
    time_window_key: str,
) -> list[dict[str, Any]]:
    products = sorted(set(kidx.get("cart_interest_products") or []))
    if not products:
        return [
            _build_synthesis(
                store_slug=store_slug,
                rule=rule,
                subject_type=SUBJECT_STORE,
                subject_id=store_slug,
                time_window_key=time_window_key,
                window_start=window_start,
                window_end=window_end,
                synthesis_state=STATE_INSUFFICIENT,
                pattern_direction=DIRECTION_INSUFFICIENT,
                commercial_domain="product",
                source_domains=["knowledge"],
                source_record_ids=[],
                source_contributions={
                    "knowledge": {
                        "supporting_records": int(kidx.get("statement_count") or 0),
                        "role": "interest_scan",
                    }
                },
                required_source_domains=["knowledge"],
                missing_source_domains=[],
                known_facts=[
                    f"knowledge_statements={kidx.get('statement_count') or 0}",
                    "no_product_cart_interest_trends_observed",
                ],
                unknown_facts=["product_interest_without_purchase_not_established"],
                conflicting_facts=[],
                prohibited_claims=list(rule.get("prohibited_claims") or []),
                supporting_evidence_count=0,
                contradicting_evidence_count=0,
                sample_size=0,
                minimum_sample_size=int(rule.get("minimum_sample_size") or 0),
                evidence_coverage=0.0,
                confidence_input={"evidence_coverage": 0.0, "sample_maturity": "low"},
                significance_input={"sample_size": 0},
                commercial_relevance_input={"pattern": PATTERN_PRODUCT_INTEREST_WITHOUT_PURCHASE},
                synthesis_summary_key="product_interest_without_purchase.insufficient",
            )
        ]

    out: list[dict[str, Any]] = []
    by_product = kidx.get("by_product") or {}
    for pid in products[:25]:
        meta = by_product.get(pid) or {}
        purchase_n = purchase_count_for_product_v1(store_slug, pid)
        purchase_gap = bool(meta.get("purchase_gap")) or purchase_n == 0
        sample = 1 + purchase_n
        domains = ["knowledge"]
        contributions: dict[str, Any] = {
            "knowledge": {"supporting_records": 1, "role": "cart_interest"},
        }
        if "product_purchase" in (sources.get("available_source_domains") or []):
            domains.append("product_purchase")
            contributions["product_purchase"] = {
                "supporting_records": purchase_n,
                "role": "completed_purchase",
            }
        if purchase_gap and sample >= int(rule.get("minimum_sample_size") or 0):
            state = STATE_QUALIFIED
            known = [
                f"product={pid}",
                "cart_interest_trend_observed",
                f"purchase_mappings={purchase_n}",
            ]
            unknown = [
                "why_purchase_completion_is_weak",
                "whether_price_or_checkout_is_involved",
            ]
            direction = DIRECTION_GAP
            summary = "product_interest_without_purchase.qualified"
            supporting = 1
        else:
            state = STATE_OBSERVING
            known = [f"product={pid}", "cart_interest_trend_observed"]
            unknown = ["purchase_completion_gap_not_yet_mature"]
            direction = DIRECTION_OBSERVING
            summary = "product_interest_without_purchase.observing"
            supporting = 1
        out.append(
            _build_synthesis(
                store_slug=store_slug,
                rule=rule,
                subject_type=SUBJECT_PRODUCT,
                subject_id=pid,
                time_window_key=time_window_key,
                window_start=window_start,
                window_end=window_end,
                synthesis_state=state,
                pattern_direction=direction,
                commercial_domain="product",
                source_domains=domains,
                source_record_ids=[f"product:{pid}"],
                source_contributions=contributions,
                required_source_domains=["knowledge"],
                missing_source_domains=[],
                known_facts=known,
                unknown_facts=unknown,
                conflicting_facts=[],
                prohibited_claims=list(rule.get("prohibited_claims") or []),
                supporting_evidence_count=supporting,
                contradicting_evidence_count=0,
                sample_size=sample,
                minimum_sample_size=int(rule.get("minimum_sample_size") or 0),
                evidence_coverage=min(1.0, len(domains) / 2.0),
                confidence_input={
                    "evidence_coverage": min(1.0, len(domains) / 2.0),
                    "sample_maturity": "medium" if sample >= 3 else "low",
                    "contradiction_level": 0.0,
                    "source_diversity": len(domains),
                },
                significance_input={"sample_size": sample},
                commercial_relevance_input={
                    "pattern": PATTERN_PRODUCT_INTEREST_WITHOUT_PURCHASE
                },
                synthesis_summary_key=summary,
            )
        )
    return out


def _eval_high_traffic(
    rule: dict[str, Any],
    *,
    store_slug: str,
    sources: dict[str, Any],
    kidx: dict[str, Any],
    window_start: datetime,
    window_end: datetime,
    time_window_key: str,
) -> list[dict[str, Any]]:
    engagement = int(kidx.get("engagement_trend_count") or 0)
    purchase_trends = int(kidx.get("purchase_trend_count") or 0)
    purchase_maps = int(
        (sources.get("sources") or {})
        .get("product_purchase", {})
        .get("store_purchase_mapping_count")
        or 0
    )
    domains = ["knowledge"]
    contributions: dict[str, Any] = {
        "knowledge": {
            "supporting_records": engagement + purchase_trends,
            "role": "engagement_vs_purchase",
        }
    }
    if purchase_maps:
        domains.append("product_purchase")
        contributions["product_purchase"] = {
            "supporting_records": purchase_maps,
            "role": "completed_purchase",
        }

    if engagement >= 1 and purchase_maps == 0 and purchase_trends == 0:
        state = STATE_QUALIFIED
        known = [
            f"engagement_trend_observations={engagement}",
            f"purchase_mappings={purchase_maps}",
            "store_activity_present_with_weak_purchase_completion",
        ]
        unknown = ["root_cause_of_weak_conversion", "specific_funnel_stage_fault"]
        direction = DIRECTION_GAP
        summary = "high_traffic_weak_conversion.qualified"
        supporting = engagement
    elif engagement >= 1:
        state = STATE_OBSERVING
        known = [
            f"engagement_trend_observations={engagement}",
            f"purchase_mappings={purchase_maps}",
        ]
        unknown = ["whether_conversion_weakness_is_material"]
        direction = DIRECTION_OBSERVING
        summary = "high_traffic_weak_conversion.observing"
        supporting = engagement
    else:
        state = STATE_INSUFFICIENT
        known = [f"engagement_trend_observations={engagement}"]
        unknown = ["traffic_and_conversion_pattern_not_established"]
        direction = DIRECTION_INSUFFICIENT
        summary = "high_traffic_weak_conversion.insufficient"
        supporting = 0

    return [
        _build_synthesis(
            store_slug=store_slug,
            rule=rule,
            subject_type=SUBJECT_STORE,
            subject_id=store_slug,
            time_window_key=time_window_key,
            window_start=window_start,
            window_end=window_end,
            synthesis_state=state,
            pattern_direction=direction,
            commercial_domain="store_conversion",
            source_domains=domains,
            source_record_ids=[f"store:{store_slug}"],
            source_contributions=contributions,
            required_source_domains=["knowledge"],
            missing_source_domains=[],
            known_facts=known,
            unknown_facts=unknown,
            conflicting_facts=[],
            prohibited_claims=list(rule.get("prohibited_claims") or []),
            supporting_evidence_count=supporting,
            contradicting_evidence_count=0,
            sample_size=engagement + purchase_maps,
            minimum_sample_size=int(rule.get("minimum_sample_size") or 0),
            evidence_coverage=min(1.0, len(domains) / 2.0),
            confidence_input={
                "evidence_coverage": min(1.0, len(domains) / 2.0),
                "sample_maturity": "low" if engagement < 3 else "medium",
                "contradiction_level": 0.0,
                "source_diversity": len(domains),
            },
            significance_input={"engagement": engagement, "purchases": purchase_maps},
            commercial_relevance_input={
                "pattern": PATTERN_HIGH_TRAFFIC_WEAK_CONVERSION
            },
            synthesis_summary_key=summary,
        )
    ]


def _eval_whatsapp_return(
    rule: dict[str, Any],
    *,
    store_slug: str,
    sources: dict[str, Any],
    available: set[str],
    window_start: datetime,
    window_end: datetime,
    time_window_key: str,
) -> list[dict[str, Any]]:
    ok_domains, missing = _domains_ok(rule, available)
    if not ok_domains:
        return [
            _blocked(
                store_slug=store_slug,
                rule=rule,
                subject_type=SUBJECT_STORE,
                subject_id=store_slug,
                time_window_key=time_window_key,
                window_start=window_start,
                window_end=window_end,
                missing=missing,
                reason="missing_required_source",
            )
        ]
    signals = list(
        (sources.get("sources") or {}).get("commerce_signals", {}).get("signals") or []
    )
    recovery = [
        s
        for s in signals
        if str(s.get("signal_type") or "").startswith("recovery_")
        or str(s.get("signal_type") or "") in {"customer_return", "return_to_site"}
    ]
    purchases = [
        s for s in signals if str(s.get("signal_type") or "") == "purchase_confirmed"
    ]
    sample = len(recovery)
    min_n = int(rule.get("minimum_sample_size") or 0)
    contributions = {
        "commerce_signals": {
            "supporting_records": sample,
            "role": "recovery_contact_or_return",
        }
    }
    if purchases:
        contributions["commerce_signals_purchase"] = {
            "supporting_records": len(purchases),
            "role": "completed_purchase",
        }

    if sample < min_n:
        state = STATE_INSUFFICIENT
        known = [f"recovery_or_return_signals={sample}", f"purchase_signals={len(purchases)}"]
        unknown = ["whatsapp_return_without_purchase_not_established"]
        direction = DIRECTION_INSUFFICIENT
        summary = "whatsapp_return_without_purchase.insufficient"
        supporting = sample
    elif len(purchases) == 0 and sample >= min_n:
        state = STATE_QUALIFIED
        known = [
            f"recovery_or_return_signals={sample}",
            "no_purchase_confirmed_signals_in_window",
        ]
        unknown = ["whether_whatsapp_content_or_timing_is_involved"]
        direction = DIRECTION_RETURN_WITHOUT_PURCHASE
        summary = "whatsapp_return_without_purchase.qualified"
        supporting = sample
    else:
        state = STATE_OBSERVING
        known = [
            f"recovery_or_return_signals={sample}",
            f"purchase_signals={len(purchases)}",
        ]
        unknown = ["share_returning_without_purchase_not_yet_stable"]
        direction = DIRECTION_OBSERVING
        summary = "whatsapp_return_without_purchase.observing"
        supporting = sample

    return [
        _build_synthesis(
            store_slug=store_slug,
            rule=rule,
            subject_type=SUBJECT_STORE,
            subject_id=store_slug,
            time_window_key=time_window_key,
            window_start=window_start,
            window_end=window_end,
            synthesis_state=state,
            pattern_direction=direction,
            commercial_domain="recovery",
            source_domains=["commerce_signals"],
            source_record_ids=[f"signal:{i}" for i, _ in enumerate(recovery[:20])],
            source_contributions=contributions,
            required_source_domains=["commerce_signals"],
            missing_source_domains=[],
            known_facts=known,
            unknown_facts=unknown,
            conflicting_facts=[],
            prohibited_claims=list(rule.get("prohibited_claims") or []),
            supporting_evidence_count=supporting,
            contradicting_evidence_count=len(purchases),
            sample_size=sample,
            minimum_sample_size=min_n,
            evidence_coverage=1.0 if sample else 0.0,
            confidence_input={
                "evidence_coverage": 1.0 if sample else 0.0,
                "sample_maturity": "medium" if sample >= min_n else "low",
                "contradiction_level": 0.0,
                "source_diversity": 1,
            },
            significance_input={"sample_size": sample},
            commercial_relevance_input={
                "pattern": PATTERN_WHATSAPP_RETURN_WITHOUT_PURCHASE
            },
            synthesis_summary_key=summary,
        )
    ]


def _eval_shipping(
    rule: dict[str, Any],
    *,
    store_slug: str,
    sources: dict[str, Any],
    available: set[str],
    window_start: datetime,
    window_end: datetime,
    time_window_key: str,
) -> list[dict[str, Any]]:
    ok_domains, missing = _domains_ok(rule, available)
    if not ok_domains:
        return [
            _blocked(
                store_slug=store_slug,
                rule=rule,
                subject_type=SUBJECT_HESITATION,
                subject_id="shipping",
                time_window_key=time_window_key,
                window_start=window_start,
                window_end=window_end,
                missing=missing,
                reason="missing_required_source",
            )
        ]
    rows = list(
        (sources.get("sources") or {})
        .get("product_hesitation", {})
        .get("shipping_hesitation_rows")
        or []
    )
    sample = len(rows)
    min_n = int(rule.get("minimum_sample_size") or 0)
    domains = ["product_hesitation"]
    contributions: dict[str, Any] = {
        "product_hesitation": {
            "supporting_records": sample,
            "role": "hesitation_reason",
        }
    }
    purchase_n = int(
        (sources.get("sources") or {})
        .get("product_purchase", {})
        .get("store_purchase_mapping_count")
        or 0
    )
    if "product_purchase" in available:
        domains.append("product_purchase")
        contributions["product_purchase"] = {
            "supporting_records": purchase_n,
            "role": "completed_purchase",
        }
    has_wa = "commerce_signals" in available
    if has_wa:
        domains.append("commerce_signals")
        contributions["commerce_signals"] = {
            "supporting_records": int(
                (sources.get("sources") or {})
                .get("commerce_signals", {})
                .get("signal_count")
                or 0
            ),
            "role": "recovery_contact",
        }

    if sample < min_n:
        state = STATE_INSUFFICIENT
        known = [f"shipping_hesitation_rows={sample}"]
        unknown = ["shipping_hesitation_recovery_outcome_not_established"]
        direction = DIRECTION_INSUFFICIENT
        summary = "shipping_hesitation_recovery_outcome.insufficient"
    elif not has_wa:
        state = STATE_OBSERVING
        known = [
            f"shipping_hesitation_rows={sample}",
            f"store_purchase_mappings={purchase_n}",
        ]
        unknown = [
            "post_recovery_return_rate_for_shipping_hesitation",
            "whether_shipping_price_delivery_speed_or_other_issue",
        ]
        direction = DIRECTION_OBSERVING
        summary = "shipping_hesitation_recovery_outcome.observing"
    else:
        state = STATE_QUALIFIED
        known = [
            f"shipping_hesitation_rows={sample}",
            f"store_purchase_mappings={purchase_n}",
            "recovery_signals_available",
        ]
        unknown = [
            "whether_shipping_price_is_the_cause",
            "whether_lowering_shipping_increases_purchases",
        ]
        direction = DIRECTION_RETURN_WITHOUT_PURCHASE
        summary = "shipping_hesitation_recovery_outcome.qualified"

    return [
        _build_synthesis(
            store_slug=store_slug,
            rule=rule,
            subject_type=SUBJECT_HESITATION,
            subject_id="shipping",
            time_window_key=time_window_key,
            window_start=window_start,
            window_end=window_end,
            synthesis_state=state,
            pattern_direction=direction,
            commercial_domain="hesitation_recovery",
            source_domains=domains,
            source_record_ids=[f"hesitation:{r.get('id')}" for r in rows[:20]],
            source_contributions=contributions,
            required_source_domains=["product_hesitation"],
            missing_source_domains=[],
            known_facts=known,
            unknown_facts=unknown,
            conflicting_facts=[],
            prohibited_claims=list(rule.get("prohibited_claims") or []),
            supporting_evidence_count=sample,
            contradicting_evidence_count=0,
            sample_size=sample,
            minimum_sample_size=min_n,
            evidence_coverage=min(1.0, len(domains) / 3.0),
            confidence_input={
                "evidence_coverage": min(1.0, len(domains) / 3.0),
                "sample_maturity": "medium" if sample >= min_n else "low",
                "source_diversity": len(domains),
            },
            significance_input={"sample_size": sample},
            commercial_relevance_input={
                "pattern": PATTERN_SHIPPING_HESITATION_RECOVERY
            },
            synthesis_summary_key=summary,
        )
    ]


def _eval_repeated_interest(
    rule: dict[str, Any],
    *,
    store_slug: str,
    kidx: dict[str, Any],
    window_start: datetime,
    window_end: datetime,
    time_window_key: str,
) -> list[dict[str, Any]]:
    products = sorted(
        set(kidx.get("return_trend_products") or [])
        | set(kidx.get("cart_interest_products") or [])
    )
    if not products:
        return [
            _build_synthesis(
                store_slug=store_slug,
                rule=rule,
                subject_type=SUBJECT_STORE,
                subject_id=store_slug,
                time_window_key=time_window_key,
                window_start=window_start,
                window_end=window_end,
                synthesis_state=STATE_INSUFFICIENT,
                pattern_direction=DIRECTION_INSUFFICIENT,
                commercial_domain="product",
                source_domains=["knowledge"],
                source_record_ids=[],
                source_contributions={
                    "knowledge": {
                        "supporting_records": int(kidx.get("statement_count") or 0),
                        "role": "repeated_interest_scan",
                    }
                },
                required_source_domains=["knowledge"],
                missing_source_domains=[],
                known_facts=["no_repeated_interest_trends_observed"],
                unknown_facts=["repeated_interest_pattern_not_established"],
                conflicting_facts=[],
                prohibited_claims=list(rule.get("prohibited_claims") or []),
                supporting_evidence_count=0,
                contradicting_evidence_count=0,
                sample_size=0,
                minimum_sample_size=int(rule.get("minimum_sample_size") or 0),
                evidence_coverage=0.0,
                confidence_input={"evidence_coverage": 0.0},
                significance_input={"sample_size": 0},
                commercial_relevance_input={"pattern": PATTERN_REPEATED_INTEREST},
                synthesis_summary_key="repeated_interest_pattern.insufficient",
            )
        ]
    out: list[dict[str, Any]] = []
    by_product = kidx.get("by_product") or {}
    for pid in products[:20]:
        meta = by_product.get(pid) or {}
        repeated = bool(meta.get("return_interest")) and bool(meta.get("cart_interest"))
        state = STATE_QUALIFIED if repeated else STATE_OBSERVING
        out.append(
            _build_synthesis(
                store_slug=store_slug,
                rule=rule,
                subject_type=SUBJECT_PRODUCT,
                subject_id=pid,
                time_window_key=time_window_key,
                window_start=window_start,
                window_end=window_end,
                synthesis_state=state,
                pattern_direction=DIRECTION_REPEATED_INTEREST
                if repeated
                else DIRECTION_OBSERVING,
                commercial_domain="product",
                source_domains=["knowledge"],
                source_record_ids=[f"product:{pid}"],
                source_contributions={
                    "knowledge": {"supporting_records": 1, "role": "repeated_interest"}
                },
                required_source_domains=["knowledge"],
                missing_source_domains=[],
                known_facts=[
                    f"product={pid}",
                    f"cart_interest={bool(meta.get('cart_interest'))}",
                    f"return_interest={bool(meta.get('return_interest'))}",
                ],
                unknown_facts=["why_journey_remains_unresolved"],
                conflicting_facts=[],
                prohibited_claims=list(rule.get("prohibited_claims") or []),
                supporting_evidence_count=1,
                contradicting_evidence_count=0,
                sample_size=1,
                minimum_sample_size=int(rule.get("minimum_sample_size") or 0),
                evidence_coverage=0.5,
                confidence_input={"evidence_coverage": 0.5, "source_diversity": 1},
                significance_input={"sample_size": 1},
                commercial_relevance_input={"pattern": PATTERN_REPEATED_INTEREST},
                synthesis_summary_key=(
                    "repeated_interest_pattern.qualified"
                    if repeated
                    else "repeated_interest_pattern.observing"
                ),
            )
        )
    return out


def _eval_discount(
    rule: dict[str, Any],
    *,
    store_slug: str,
    available: set[str],
    window_start: datetime,
    window_end: datetime,
    time_window_key: str,
) -> list[dict[str, Any]]:
    ok_domains, missing = _domains_ok(rule, available)
    if not ok_domains:
        return [
            _blocked(
                store_slug=store_slug,
                rule=rule,
                subject_type=SUBJECT_RECOVERY_STRATEGY,
                subject_id="discount",
                time_window_key=time_window_key,
                window_start=window_start,
                window_end=window_end,
                missing=missing,
                reason="missing_required_source",
            )
        ]
    return [
        _build_synthesis(
            store_slug=store_slug,
            rule=rule,
            subject_type=SUBJECT_RECOVERY_STRATEGY,
            subject_id="discount",
            time_window_key=time_window_key,
            window_start=window_start,
            window_end=window_end,
            synthesis_state=STATE_INSUFFICIENT,
            pattern_direction=DIRECTION_INSUFFICIENT,
            commercial_domain="recovery_strategy",
            source_domains=sorted(available & {"commerce_signals", "product_hesitation"}),
            source_record_ids=[],
            source_contributions={},
            required_source_domains=list(rule.get("required_source_domains") or []),
            missing_source_domains=[
                "message_strategy_classification"
            ],
            known_facts=["discount_message_strategy_classification_not_available"],
            unknown_facts=[
                "discount_oriented_recovery_outcome_for_hesitation_condition"
            ],
            conflicting_facts=[],
            prohibited_claims=list(rule.get("prohibited_claims") or []),
            supporting_evidence_count=0,
            contradicting_evidence_count=0,
            sample_size=0,
            minimum_sample_size=int(rule.get("minimum_sample_size") or 0),
            evidence_coverage=0.0,
            confidence_input={"evidence_coverage": 0.0},
            significance_input={"sample_size": 0},
            commercial_relevance_input={"pattern": PATTERN_DISCOUNT_MESSAGE_WEAKNESS},
            synthesis_summary_key="discount_message_weakness.insufficient",
        )
    ]


def _eval_vip(
    rule: dict[str, Any],
    *,
    store_slug: str,
    available: set[str],
    window_start: datetime,
    window_end: datetime,
    time_window_key: str,
) -> list[dict[str, Any]]:
    ok_domains, missing = _domains_ok(rule, available)
    if not ok_domains:
        return [
            _blocked(
                store_slug=store_slug,
                rule=rule,
                subject_type=SUBJECT_VIP_COHORT,
                subject_id="vip",
                time_window_key=time_window_key,
                window_start=window_start,
                window_end=window_end,
                missing=missing,
                reason="missing_required_source",
            )
        ]
    # Comparison governance: without comparable merchant-vs-automated cohorts, abstain.
    return [
        _build_synthesis(
            store_slug=store_slug,
            rule=rule,
            subject_type=SUBJECT_VIP_COHORT,
            subject_id="vip",
            time_window_key=time_window_key,
            window_start=window_start,
            window_end=window_end,
            synthesis_state=STATE_INSUFFICIENT,
            pattern_direction=DIRECTION_COMPARISON,
            commercial_domain="vip_recovery",
            source_domains=["commerce_signals"],
            source_record_ids=[],
            source_contributions={
                "commerce_signals": {
                    "supporting_records": 0,
                    "role": "vip_comparison_scan",
                }
            },
            required_source_domains=["commerce_signals"],
            missing_source_domains=["comparable_vip_followup_cohorts"],
            known_facts=["vip_comparison_cohorts_not_materialized"],
            unknown_facts=[
                "merchant_followup_vs_automated_outcome_for_vip_carts"
            ],
            conflicting_facts=[],
            prohibited_claims=list(rule.get("prohibited_claims") or []),
            supporting_evidence_count=0,
            contradicting_evidence_count=0,
            sample_size=0,
            minimum_sample_size=int(rule.get("minimum_sample_size") or 0),
            evidence_coverage=0.0,
            confidence_input={"evidence_coverage": 0.0, "comparison_ready": False},
            significance_input={"sample_size": 0},
            commercial_relevance_input={"pattern": PATTERN_VIP_FOLLOWUP_OUTCOME},
            synthesis_summary_key="vip_followup_outcome.insufficient",
            comparison_subject_type=SUBJECT_VIP_COHORT,
            comparison_subject_id="automated_vs_merchant",
        )
    ]


def _eval_insufficient_store(
    rule: dict[str, Any],
    *,
    store_slug: str,
    sources: dict[str, Any],
    kidx: dict[str, Any],
    window_start: datetime,
    window_end: datetime,
    time_window_key: str,
) -> list[dict[str, Any]]:
    available = list(sources.get("available_source_domains") or [])
    coverage = len(available) / 4.0
    stmt_n = int(kidx.get("statement_count") or 0)
    # This rule always accounts for store-level sufficiency.
    if coverage < 0.5 or stmt_n < 2:
        state = STATE_QUALIFIED  # qualified as an insufficiency pattern
        known = [
            f"available_source_domains={available}",
            f"knowledge_statements={stmt_n}",
            "current_data_not_sufficient_for_reliable_conclusion",
        ]
        summary = "insufficient_evidence_store.qualified"
    else:
        state = STATE_OBSERVING
        known = [
            f"available_source_domains={available}",
            f"knowledge_statements={stmt_n}",
            "partial_coverage_present",
        ]
        summary = "insufficient_evidence_store.observing"
    return [
        _build_synthesis(
            store_slug=store_slug,
            rule=rule,
            subject_type=SUBJECT_STORE,
            subject_id=store_slug,
            time_window_key=time_window_key,
            window_start=window_start,
            window_end=window_end,
            synthesis_state=state,
            pattern_direction=DIRECTION_INSUFFICIENT,
            commercial_domain="evidence_sufficiency",
            source_domains=available,
            source_record_ids=[],
            source_contributions={
                d: {"supporting_records": 1, "role": "coverage"} for d in available
            },
            required_source_domains=["knowledge"],
            missing_source_domains=list(sources.get("missing_source_domains") or []),
            known_facts=known,
            unknown_facts=["reliable_commercial_conclusion"],
            conflicting_facts=[],
            prohibited_claims=list(rule.get("prohibited_claims") or []),
            supporting_evidence_count=stmt_n,
            contradicting_evidence_count=0,
            sample_size=stmt_n,
            minimum_sample_size=0,
            evidence_coverage=coverage,
            confidence_input={
                "evidence_coverage": coverage,
                "sample_maturity": "low" if stmt_n < 2 else "medium",
                "source_diversity": len(available),
            },
            significance_input={"statement_count": stmt_n},
            commercial_relevance_input={"pattern": PATTERN_INSUFFICIENT_EVIDENCE},
            synthesis_summary_key=summary,
        )
    ]


def _eval_conflicting_store(
    rule: dict[str, Any],
    *,
    store_slug: str,
    kidx: dict[str, Any],
    window_start: datetime,
    window_end: datetime,
    time_window_key: str,
) -> list[dict[str, Any]]:
    conflicts = int(kidx.get("conflict_count") or 0)
    if conflicts > 0:
        state = STATE_CONFLICTING
        known = [f"knowledge_conflict_flags={conflicts}"]
        conflicting = ["source_domains_disagree_materially"]
        summary = "conflicting_evidence_store.conflicting"
        direction = DIRECTION_CONFLICTING
    else:
        state = STATE_INSUFFICIENT
        known = ["no_knowledge_conflict_flags"]
        conflicting = []
        summary = "conflicting_evidence_store.insufficient"
        direction = DIRECTION_INSUFFICIENT
    return [
        _build_synthesis(
            store_slug=store_slug,
            rule=rule,
            subject_type=SUBJECT_STORE,
            subject_id=store_slug,
            time_window_key=time_window_key,
            window_start=window_start,
            window_end=window_end,
            synthesis_state=state,
            pattern_direction=direction,
            commercial_domain="evidence_conflict",
            source_domains=["knowledge"],
            source_record_ids=[],
            source_contributions={
                "knowledge": {
                    "supporting_records": conflicts,
                    "role": "conflict_flags",
                }
            },
            required_source_domains=["knowledge"],
            missing_source_domains=[],
            known_facts=known,
            unknown_facts=["single_reliable_explanation"],
            conflicting_facts=conflicting,
            prohibited_claims=list(rule.get("prohibited_claims") or []),
            supporting_evidence_count=0,
            contradicting_evidence_count=conflicts,
            sample_size=conflicts,
            minimum_sample_size=0,
            evidence_coverage=1.0 if conflicts else 0.0,
            confidence_input={
                "contradiction_level": 1.0 if conflicts else 0.0,
                "source_agreement": 0.0 if conflicts else 1.0,
            },
            significance_input={"conflict_count": conflicts},
            commercial_relevance_input={"pattern": PATTERN_CONFLICTING_EVIDENCE},
            synthesis_summary_key=summary,
        )
    ]


def _eval_recovery_influence(
    rule: dict[str, Any],
    *,
    store_slug: str,
    sources: dict[str, Any],
    available: set[str],
    window_start: datetime,
    window_end: datetime,
    time_window_key: str,
) -> list[dict[str, Any]]:
    ok_domains, missing = _domains_ok(rule, available)
    if not ok_domains:
        return [
            _blocked(
                store_slug=store_slug,
                rule=rule,
                subject_type=SUBJECT_STORE,
                subject_id=store_slug,
                time_window_key=time_window_key,
                window_start=window_start,
                window_end=window_end,
                missing=missing,
                reason="missing_required_source",
            )
        ]
    signals = list(
        (sources.get("sources") or {}).get("commerce_signals", {}).get("signals") or []
    )
    counts = {c: 0 for c in RECOVERY_CLASSIFICATIONS}
    purchase_confirmed = 0
    for s in signals:
        st = str(s.get("signal_type") or "")
        if st == "purchase_confirmed":
            purchase_confirmed += 1
        # Preserve classification if present on signal payload; never collapse.
        cls = str(s.get("recovery_classification") or s.get("influence_class") or "")
        if cls in counts:
            counts[cls] += 1
    sample = purchase_confirmed + sum(counts.values())
    if sample < int(rule.get("minimum_sample_size") or 0):
        state = STATE_INSUFFICIENT
        summary = "recovery_influence_boundary.insufficient"
        known = [
            f"purchase_confirmed_signals={purchase_confirmed}",
            "influence_class_counts="
            + json.dumps(counts, sort_keys=True, separators=(",", ":")),
        ]
    else:
        state = STATE_QUALIFIED
        summary = "recovery_influence_boundary.qualified"
        known = [
            f"purchase_confirmed_signals={purchase_confirmed}",
            "influence_class_counts="
            + json.dumps(counts, sort_keys=True, separators=(",", ":")),
            "classifications_preserved_not_collapsed",
        ]
    return [
        _build_synthesis(
            store_slug=store_slug,
            rule=rule,
            subject_type=SUBJECT_STORE,
            subject_id=store_slug,
            time_window_key=time_window_key,
            window_start=window_start,
            window_end=window_end,
            synthesis_state=state,
            pattern_direction=DIRECTION_INFLUENCE_BOUNDARY,
            commercial_domain="recovery_influence",
            source_domains=["commerce_signals"],
            source_record_ids=[],
            source_contributions={
                "commerce_signals": {
                    "supporting_records": sample,
                    "role": "influence_boundary",
                },
                "purchase_truth": {
                    "supporting_records": purchase_confirmed,
                    "role": "completed_purchase",
                },
            },
            required_source_domains=["commerce_signals"],
            missing_source_domains=[],
            known_facts=known,
            unknown_facts=["causal_recovery_effect"],
            conflicting_facts=[],
            prohibited_claims=list(rule.get("prohibited_claims") or []),
            supporting_evidence_count=sample,
            contradicting_evidence_count=0,
            sample_size=sample,
            minimum_sample_size=int(rule.get("minimum_sample_size") or 0),
            evidence_coverage=1.0 if sample else 0.0,
            confidence_input={
                "evidence_coverage": 1.0 if sample else 0.0,
                "attribution_collapsed": False,
            },
            significance_input={"sample_size": sample, "classes": counts},
            commercial_relevance_input={
                "pattern": PATTERN_RECOVERY_INFLUENCE_BOUNDARY
            },
            synthesis_summary_key=summary,
        )
    ]


_RULE_EVALUATORS = {
    "product_interest_without_purchase": _eval_product_interest,
    "high_traffic_weak_conversion": _eval_high_traffic,
    "whatsapp_return_without_purchase": _eval_whatsapp_return,
    "shipping_hesitation_recovery_outcome": _eval_shipping,
    "repeated_interest_pattern": _eval_repeated_interest,
    "discount_message_weakness": _eval_discount,
    "vip_followup_outcome": _eval_vip,
    "insufficient_evidence_store": _eval_insufficient_store,
    "conflicting_evidence_store": _eval_conflicting_store,
    "recovery_influence_boundary": _eval_recovery_influence,
}


def generate_commerce_intelligence_syntheses_v1(
    store_slug: str,
    *,
    time_window_key: str = "d7",
    as_of: Optional[datetime] = None,
    rule_keys: Optional[list[str]] = None,
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (time_window_key or "d7").strip().lower()
    if window not in WINDOW_LENGTH_DAYS:
        window = "d7"
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "time_window_key": window,
        "as_of": None,
        "registry_version": RULE_REGISTRY_VERSION_V1,
        "source_contract_registry_version": SOURCE_CONTRACT_REGISTRY_VERSION_V1,
        "output_contract_version": OUTPUT_CONTRACT_VERSION_V1,
        "provider_independent": True,
        "syntheses": [],
        "candidate_count": 0,
        "expected_candidate_count": 0,
        "canonical_fingerprint": "",
        "rejected_input_count": 0,
        "unsupported_input_reasons": {},
        "errors": [],
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not rule_registry_valid_v1() or not source_registry_valid_v1():
        out["errors"].append("registry_invalid")
        return out

    anchor = _floor_second(as_of or _utc_naive_now())
    out["as_of"] = anchor.isoformat(sep=" ")
    sources = load_synthesis_sources_v1(slug, time_window_key=window, as_of=anchor)
    out["rejected_input_count"] = len(sources.get("rejected_inputs") or [])
    out["unsupported_input_reasons"] = dict(
        sources.get("unsupported_input_reasons") or {}
    )
    window_start = _parse_iso(sources.get("window_start")) or (
        anchor - timedelta(days=WINDOW_LENGTH_DAYS[window])
    )
    window_end = _parse_iso(sources.get("window_end")) or anchor
    available = set(sources.get("available_source_domains") or [])
    kidx = knowledge_index_v1(sources)

    rules = active_synthesis_rules_v1()
    if rule_keys:
        allow = set(rule_keys)
        rules = [r for r in rules if r["synthesis_rule_key"] in allow]

    syntheses: list[dict[str, Any]] = []
    expected = 0
    for rule in rules:
        if window not in (rule.get("allowed_windows") or ()):
            # Still account: blocked for temporal incompatibility.
            expected += 1
            syntheses.append(
                _blocked(
                    store_slug=slug,
                    rule=rule,
                    subject_type=SUBJECT_STORE,
                    subject_id=slug,
                    time_window_key=window,
                    window_start=window_start,
                    window_end=window_end,
                    missing=["temporal_window_compatible_inputs"],
                    reason="window_not_allowed_for_rule",
                )
            )
            continue
        key = str(rule["synthesis_rule_key"])
        evaluator = _RULE_EVALUATORS.get(key)
        try:
            if evaluator is None:
                expected += 1
                syntheses.append(
                    _failed(
                        store_slug=slug,
                        rule=rule,
                        subject_type=SUBJECT_STORE,
                        subject_id=slug,
                        time_window_key=window,
                        window_start=window_start,
                        window_end=window_end,
                        reason="evaluator_missing",
                    )
                )
                continue
            # Domain gate for rules that need required sources before subject fan-out.
            ok_domains, missing = _domains_ok(rule, available)
            if not ok_domains and key not in {
                # Evaluators that emit their own blocked/insufficient accounting
                "whatsapp_return_without_purchase",
                "shipping_hesitation_recovery_outcome",
                "discount_message_weakness",
                "vip_followup_outcome",
                "recovery_influence_boundary",
            }:
                expected += 1
                syntheses.append(
                    _blocked(
                        store_slug=slug,
                        rule=rule,
                        subject_type=SUBJECT_STORE,
                        subject_id=slug,
                        time_window_key=window,
                        window_start=window_start,
                        window_end=window_end,
                        missing=missing,
                        reason="missing_required_source",
                    )
                )
                continue

            kwargs: dict[str, Any] = {
                "store_slug": slug,
                "window_start": window_start,
                "window_end": window_end,
                "time_window_key": window,
            }
            if key in {
                "product_interest_without_purchase",
                "high_traffic_weak_conversion",
                "insufficient_evidence_store",
            }:
                kwargs["sources"] = sources
                kwargs["kidx"] = kidx
            elif key in {
                "whatsapp_return_without_purchase",
                "shipping_hesitation_recovery_outcome",
                "recovery_influence_boundary",
            }:
                kwargs["sources"] = sources
                kwargs["available"] = available
            elif key == "repeated_interest_pattern":
                kwargs["kidx"] = kidx
            elif key in {"discount_message_weakness", "vip_followup_outcome"}:
                kwargs["available"] = available
            elif key == "conflicting_evidence_store":
                kwargs["kidx"] = kidx

            batch = evaluator(rule, **kwargs)
            if not batch:
                expected += 1
                syntheses.append(
                    _failed(
                        store_slug=slug,
                        rule=rule,
                        subject_type=SUBJECT_STORE,
                        subject_id=slug,
                        time_window_key=window,
                        window_start=window_start,
                        window_end=window_end,
                        reason="silent_skip_prevented",
                    )
                )
                continue
            if subject_type:
                batch = [
                    s
                    for s in batch
                    if s.get("subject_type") == subject_type
                    and (
                        not subject_id
                        or s.get("subject_id") == subject_id
                    )
                ]
                if not batch:
                    # Scoped refresh still accounts the empty filter as observing.
                    expected += 1
                    syntheses.append(
                        _build_synthesis(
                            store_slug=slug,
                            rule=rule,
                            subject_type=subject_type,
                            subject_id=subject_id or "",
                            time_window_key=window,
                            window_start=window_start,
                            window_end=window_end,
                            synthesis_state=STATE_INSUFFICIENT,
                            pattern_direction=DIRECTION_INSUFFICIENT,
                            commercial_domain="scoped_refresh",
                            source_domains=sorted(available),
                            source_record_ids=[],
                            source_contributions={},
                            required_source_domains=list(
                                rule.get("required_source_domains") or []
                            ),
                            missing_source_domains=[],
                            known_facts=["no_matching_subject_in_scope"],
                            unknown_facts=["scoped_pattern_not_established"],
                            conflicting_facts=[],
                            prohibited_claims=list(
                                rule.get("prohibited_claims") or []
                            ),
                            supporting_evidence_count=0,
                            contradicting_evidence_count=0,
                            sample_size=0,
                            minimum_sample_size=int(
                                rule.get("minimum_sample_size") or 0
                            ),
                            evidence_coverage=0.0,
                            confidence_input={"scoped": True},
                            significance_input={},
                            commercial_relevance_input={},
                            synthesis_summary_key=f"{key}.scoped_insufficient",
                        )
                    )
                    continue
            expected += len(batch)
            syntheses.extend(batch)
        except Exception as exc:  # noqa: BLE001 — isolate rule failures
            expected += 1
            syntheses.append(
                _failed(
                    store_slug=slug,
                    rule=rule,
                    subject_type=SUBJECT_STORE,
                    subject_id=slug,
                    time_window_key=window,
                    window_start=window_start,
                    window_end=window_end,
                    reason=f"exception:{type(exc).__name__}",
                )
            )
            out["errors"].append(f"rule_fail:{key}:{type(exc).__name__}")

    syntheses = sorted(
        syntheses,
        key=lambda s: (
            s.get("synthesis_rule_key") or "",
            s.get("subject_type") or "",
            s.get("subject_id") or "",
            s.get("synthesis_id") or "",
        ),
    )
    out["syntheses"] = syntheses
    out["candidate_count"] = len(syntheses)
    out["expected_candidate_count"] = expected
    out["canonical_fingerprint"] = _sha(
        {
            "v": GENERATION_VERSION_V1,
            "store": slug,
            "window": window,
            "as_of": out["as_of"],
            "syntheses": [
                {
                    "synthesis_id": s["synthesis_id"],
                    "synthesis_key": s["synthesis_key"],
                    "state": s["synthesis_state"],
                    "fingerprint": s["synthesis_fingerprint"],
                }
                for s in syntheses
            ],
        }
    )
    out["ok"] = out["candidate_count"] == out["expected_candidate_count"]
    if not out["ok"]:
        out["errors"].append("candidate_accounting_mismatch")
    return out


def materialize_commerce_intelligence_syntheses_v1(
    store_slug: str,
    *,
    time_window_key: str = "d7",
    as_of: Optional[datetime] = None,
    rule_keys: Optional[list[str]] = None,
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
) -> dict[str, Any]:
    if not commerce_intelligence_synthesis_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "upserted": 0,
            "superseded": 0,
            "errors": ["commerce_intelligence_synthesis_disabled"],
        }

    report = generate_commerce_intelligence_syntheses_v1(
        store_slug,
        time_window_key=time_window_key,
        as_of=as_of,
        rule_keys=rule_keys,
        subject_type=subject_type,
        subject_id=subject_id,
    )
    if report.get("candidate_count", 0) == 0 and not report.get("ok"):
        return {
            "ok": False,
            "upserted": 0,
            "superseded": 0,
            "errors": list(report.get("errors") or []),
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    ensure_commerce_intelligence_synthesis_schema(db)
    anchor = _parse_iso(report.get("as_of")) or _floor_second(as_of or _utc_naive_now())
    as_key = _as_of_key(anchor)
    now = _utc_naive_now()
    upserted = 0
    superseded = 0
    errors: list[str] = list(report.get("errors") or [])

    for rec in report.get("syntheses") or []:
        try:
            sid = str(rec["synthesis_id"])
            store = str(rec["store_slug"])
            skey = str(rec["synthesis_key"])

            currents = (
                db.session.query(CommerceIntelligenceSynthesis)
                .filter(
                    CommerceIntelligenceSynthesis.store_slug == store,
                    CommerceIntelligenceSynthesis.synthesis_key == skey,
                    CommerceIntelligenceSynthesis.is_current.is_(True),
                    CommerceIntelligenceSynthesis.synthesis_id != sid,
                )
                .all()
            )
            for row in currents:
                row.is_current = False
                row.synthesis_state = STATE_SUPERSEDED
                row.superseded_at = now
                superseded += 1

            existing = (
                db.session.query(CommerceIntelligenceSynthesis)
                .filter(CommerceIntelligenceSynthesis.synthesis_id == sid)
                .first()
            )
            fields = dict(
                store_slug=store,
                synthesis_key=skey,
                synthesis_rule_key=str(rec.get("synthesis_rule_key") or ""),
                subject_type=str(rec.get("subject_type") or ""),
                subject_id=str(rec.get("subject_id") or ""),
                comparison_subject_type=str(rec.get("comparison_subject_type") or ""),
                comparison_subject_id=str(rec.get("comparison_subject_id") or ""),
                time_window_key=str(rec.get("time_window_key") or ""),
                window_start=_parse_iso(rec.get("window_start")) or anchor,
                window_end=_parse_iso(rec.get("window_end")) or anchor,
                synthesis_state=str(rec.get("synthesis_state") or STATE_FAILED),
                pattern_type=str(rec.get("pattern_type") or ""),
                pattern_direction=str(rec.get("pattern_direction") or ""),
                commercial_domain=str(rec.get("commercial_domain") or ""),
                source_domains_json=json.dumps(
                    rec.get("source_domains") or [], sort_keys=True
                ),
                source_record_ids_json=json.dumps(
                    rec.get("source_record_ids") or [], sort_keys=True
                ),
                source_contributions_json=json.dumps(
                    rec.get("source_contributions") or {}, sort_keys=True
                ),
                required_source_domains_json=json.dumps(
                    rec.get("required_source_domains") or [], sort_keys=True
                ),
                missing_source_domains_json=json.dumps(
                    rec.get("missing_source_domains") or [], sort_keys=True
                ),
                known_facts_json=json.dumps(
                    rec.get("known_facts") or [], sort_keys=True, ensure_ascii=False
                ),
                unknown_facts_json=json.dumps(
                    rec.get("unknown_facts") or [], sort_keys=True, ensure_ascii=False
                ),
                conflicting_facts_json=json.dumps(
                    rec.get("conflicting_facts") or [], sort_keys=True, ensure_ascii=False
                ),
                prohibited_claims_json=json.dumps(
                    rec.get("prohibited_claims") or [], sort_keys=True
                ),
                supporting_evidence_count=int(
                    rec.get("supporting_evidence_count") or 0
                ),
                contradicting_evidence_count=int(
                    rec.get("contradicting_evidence_count") or 0
                ),
                sample_size=int(rec.get("sample_size") or 0),
                minimum_sample_size=int(rec.get("minimum_sample_size") or 0),
                evidence_coverage=float(rec.get("evidence_coverage") or 0.0),
                confidence_input_json=json.dumps(
                    rec.get("confidence_input") or {}, sort_keys=True
                ),
                significance_input_json=json.dumps(
                    rec.get("significance_input") or {}, sort_keys=True
                ),
                commercial_relevance_input_json=json.dumps(
                    rec.get("commercial_relevance_input") or {}, sort_keys=True
                ),
                synthesis_summary_key=str(rec.get("synthesis_summary_key") or ""),
                input_fingerprint=str(rec.get("input_fingerprint") or ""),
                synthesis_fingerprint=str(rec.get("synthesis_fingerprint") or ""),
                rule_version=str(rec.get("rule_version") or ""),
                contract_version=str(
                    rec.get("contract_version") or OUTPUT_CONTRACT_VERSION_V1
                ),
                synthesis_version=SYNTHESIS_VERSION_V1,
                generation_version=GENERATION_VERSION_V1,
                failure_reason=str(rec.get("failure_reason") or ""),
                valid_from=_parse_iso(rec.get("valid_from")) or anchor,
                valid_until=_parse_iso(rec.get("valid_until")) or anchor,
                is_current=True,
                as_of=anchor,
                as_of_key=as_key,
                created_at=existing.created_at if existing else now,
                refreshed_at=now,
                superseded_at=None,
            )
            if existing is None:
                db.session.add(
                    CommerceIntelligenceSynthesis(synthesis_id=sid, **fields)
                )
            else:
                for k, v in fields.items():
                    setattr(existing, k, v)
            db.session.commit()
            upserted += 1
        except SQLAlchemyError as exc:
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass
            errors.append(
                f"materialize:{rec.get('synthesis_rule_key')}:{type(exc).__name__}"
            )
            log.debug("cisyn materialize failed: %s", exc)

    return {
        "ok": upserted > 0 and not any(e.startswith("materialize:") for e in errors),
        "upserted": upserted,
        "superseded": superseded,
        "candidate_count": report.get("candidate_count") or 0,
        "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        "errors": errors,
    }


def verify_commerce_intelligence_synthesis_determinism_v1(
    store_slug: str,
    *,
    time_window_key: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    anchor = _floor_second(as_of or _utc_naive_now())
    a = generate_commerce_intelligence_syntheses_v1(
        store_slug, time_window_key=time_window_key, as_of=anchor
    )
    b = generate_commerce_intelligence_syntheses_v1(
        store_slug, time_window_key=time_window_key, as_of=anchor
    )
    return {
        "deterministic": (
            a.get("canonical_fingerprint")
            and a.get("canonical_fingerprint") == b.get("canonical_fingerprint")
            and a.get("candidate_count") == b.get("candidate_count")
        ),
        "fingerprint_a": a.get("canonical_fingerprint") or "",
        "fingerprint_b": b.get("canonical_fingerprint") or "",
        "as_of": anchor.isoformat(sep=" "),
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "generate_commerce_intelligence_syntheses_v1",
    "materialize_commerce_intelligence_syntheses_v1",
    "verify_commerce_intelligence_synthesis_determinism_v1",
]
