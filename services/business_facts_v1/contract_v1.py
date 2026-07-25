# -*- coding: utf-8 -*-
"""
Business Facts Contract V1.

Observations answer: What happened?
Business Facts answer: What does this mean for the merchant?

No AI. No prediction. No recommendations.
"""
from __future__ import annotations

from typing import Any, Mapping

BUSINESS_FACTS_VERSION_V1 = "business_facts_v1"
FACT_SCHEMA_V1 = "business_fact_v1"

# Fact type categories (merchant-readable buckets).
FACT_TYPE_PRODUCT_DEMAND = "product_demand"
FACT_TYPE_CONVERSION = "conversion"
FACT_TYPE_CUSTOMER_BEHAVIOUR = "customer_behaviour"
FACT_TYPE_RECOVERY = "recovery"
FACT_TYPE_COMMUNICATION = "communication"
FACT_TYPE_STORE_HEALTH = "store_health"

FACT_TYPES_V1 = (
    FACT_TYPE_PRODUCT_DEMAND,
    FACT_TYPE_CONVERSION,
    FACT_TYPE_CUSTOMER_BEHAVIOUR,
    FACT_TYPE_RECOVERY,
    FACT_TYPE_COMMUNICATION,
    FACT_TYPE_STORE_HEALTH,
)

# Impact categories for routing (not recommendations).
IMPACT_REVENUE = "revenue"
IMPACT_CONVERSION = "conversion"
IMPACT_DEMAND = "demand"
IMPACT_OPERATIONS = "operations"
IMPACT_COMMUNICATION = "communication"
IMPACT_STORE = "store_health"

IMPACT_CATEGORIES_V1 = (
    IMPACT_REVENUE,
    IMPACT_CONVERSION,
    IMPACT_DEMAND,
    IMPACT_OPERATIONS,
    IMPACT_COMMUNICATION,
    IMPACT_STORE,
)

REQUIRED_FACT_FIELDS_V1 = (
    "fact_id",
    "fact_type",
    "subject",
    "business_meaning_ar",
    "evidence",
    "confidence",
    "freshness",
    "impact_category",
)


def empty_fact_shell_v1() -> dict[str, Any]:
    return {
        "schema": FACT_SCHEMA_V1,
        "version": BUSINESS_FACTS_VERSION_V1,
        "fact_id": "",
        "fact_type": "",
        "subject": {"kind": "", "id": "", "name_ar": ""},
        "business_meaning_ar": "",
        "business_meaning_en": "",
        "evidence": {
            "source_kinds": [],
            "observation_ids": [],
            "correlation_kinds": [],
            "capability_ids": [],
            "refs": [],
        },
        "confidence": {"level": "", "ar": "", "score": None, "source": ""},
        "freshness": {"status": "current", "as_of_utc": ""},
        "impact_category": "",
        "recommendation": None,  # explicitly absent in V1
        "surfaces": {"home": False, "decision_workspace": False},
    }


def validate_business_fact_v1(fact: Mapping[str, Any]) -> list[str]:
    """Return missing/invalid field reasons (empty = valid)."""
    errors: list[str] = []
    if not isinstance(fact, Mapping):
        return ["not_a_mapping"]
    for key in REQUIRED_FACT_FIELDS_V1:
        if key not in fact or fact.get(key) in (None, "", {}, []):
            # confidence/evidence/subject may be nested — check deeper below
            if key in ("evidence", "confidence", "freshness", "subject"):
                continue
            errors.append(f"missing:{key}")
    if str(fact.get("fact_type") or "") not in FACT_TYPES_V1:
        errors.append("invalid_fact_type")
    if str(fact.get("impact_category") or "") not in IMPACT_CATEGORIES_V1:
        errors.append("invalid_impact_category")
    subject = fact.get("subject")
    if not isinstance(subject, Mapping) or not str(subject.get("name_ar") or subject.get("id") or "").strip():
        errors.append("missing_subject")
    meaning = str(fact.get("business_meaning_ar") or "").strip()
    if not meaning:
        errors.append("missing_business_meaning_ar")
    if fact.get("recommendation") not in (None, "", {}):
        errors.append("recommendation_forbidden_in_v1")
    conf = fact.get("confidence")
    if not isinstance(conf, Mapping) or not str(conf.get("level") or conf.get("ar") or "").strip():
        errors.append("missing_confidence")
    evid = fact.get("evidence")
    if not isinstance(evid, Mapping):
        errors.append("missing_evidence")
    elif not (
        evid.get("source_kinds")
        or evid.get("observation_ids")
        or evid.get("correlation_kinds")
        or evid.get("capability_ids")
        or evid.get("refs")
    ):
        errors.append("evidence_empty")
    return errors


__all__ = [
    "BUSINESS_FACTS_VERSION_V1",
    "FACT_SCHEMA_V1",
    "FACT_TYPES_V1",
    "FACT_TYPE_COMMUNICATION",
    "FACT_TYPE_CONVERSION",
    "FACT_TYPE_CUSTOMER_BEHAVIOUR",
    "FACT_TYPE_PRODUCT_DEMAND",
    "FACT_TYPE_RECOVERY",
    "FACT_TYPE_STORE_HEALTH",
    "IMPACT_CATEGORIES_V1",
    "IMPACT_COMMUNICATION",
    "IMPACT_CONVERSION",
    "IMPACT_DEMAND",
    "IMPACT_OPERATIONS",
    "IMPACT_REVENUE",
    "IMPACT_STORE",
    "REQUIRED_FACT_FIELDS_V1",
    "empty_fact_shell_v1",
    "validate_business_fact_v1",
]
