# -*- coding: utf-8 -*-
"""Constitutional Decision categories + mapping (Gate 2C/2D Portfolio)."""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_composition_engine_v1.business_domains_v1 import (
    DOMAIN_LABEL_AR,
    map_finding_to_domain_v1,
)

CATEGORY_STORE_HEALTH = "store_health"
CATEGORY_REVENUE = "revenue"
CATEGORY_PRODUCTS = "products"
CATEGORY_PRICING = "pricing"
CATEGORY_SHIPPING = "shipping"
CATEGORY_RECOVERY = "recovery"
CATEGORY_COMMUNICATION = "communication"
CATEGORY_CUSTOMER_BEHAVIOUR = "customer_behaviour"
CATEGORY_OPERATIONS = "operations"

ALL_CATEGORIES_V1 = (
    CATEGORY_STORE_HEALTH,
    CATEGORY_REVENUE,
    CATEGORY_PRODUCTS,
    CATEGORY_PRICING,
    CATEGORY_SHIPPING,
    CATEGORY_RECOVERY,
    CATEGORY_COMMUNICATION,
    CATEGORY_CUSTOMER_BEHAVIOUR,
    CATEGORY_OPERATIONS,
)

CATEGORY_LABEL_AR = {
    CATEGORY_STORE_HEALTH: DOMAIN_LABEL_AR["store_health"],
    CATEGORY_REVENUE: DOMAIN_LABEL_AR["revenue"],
    CATEGORY_PRODUCTS: DOMAIN_LABEL_AR["products"],
    CATEGORY_PRICING: DOMAIN_LABEL_AR["pricing"],
    CATEGORY_SHIPPING: DOMAIN_LABEL_AR["shipping"],
    CATEGORY_RECOVERY: DOMAIN_LABEL_AR["recovery"],
    CATEGORY_COMMUNICATION: DOMAIN_LABEL_AR["communication"],
    CATEGORY_CUSTOMER_BEHAVIOUR: DOMAIN_LABEL_AR["customer_behaviour"],
    CATEGORY_OPERATIONS: DOMAIN_LABEL_AR["operations"],
}

# Max 1 primary visible decision per category in the portfolio.
CATEGORY_PRIMARY_CAP_V1 = {c: 1 for c in ALL_CATEGORIES_V1}

NO_ACTION_AR = "لا إجراء مطلوب."


def _norm(v: Any) -> str:
    return str(v or "").strip().lower()


def map_decision_category_v1(candidate: Mapping[str, Any]) -> str:
    # Prefer Gate 2D business_domain when stamped.
    domain = _norm(candidate.get("business_domain"))
    if domain in ALL_CATEGORIES_V1:
        return domain

    dtype = _norm(candidate.get("decision_type"))
    if dtype == "recoverability_gap":
        return CATEGORY_RECOVERY
    if dtype == "waiting_recovery_work":
        return CATEGORY_OPERATIONS

    finding_like = {
        "finding_type": candidate.get("finding_type"),
        "title": candidate.get("title"),
        "merchant_statement_ar": candidate.get("merchant_decision"),
        "tags": candidate.get("source_truth_types") or [],
    }
    mapped = map_finding_to_domain_v1(finding_like)
    if mapped in ALL_CATEGORIES_V1:
        return mapped
    return CATEGORY_STORE_HEALTH


def attach_category_v1(candidate: dict[str, Any]) -> dict[str, Any]:
    cat = map_decision_category_v1(candidate)
    candidate["decision_category"] = cat
    candidate["decision_category_ar"] = CATEGORY_LABEL_AR.get(cat, cat)
    if not candidate.get("business_domain"):
        candidate["business_domain"] = cat
    return candidate


__all__ = [
    "ALL_CATEGORIES_V1",
    "CATEGORY_LABEL_AR",
    "CATEGORY_PRIMARY_CAP_V1",
    "NO_ACTION_AR",
    "attach_category_v1",
    "map_decision_category_v1",
]
