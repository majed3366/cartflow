# -*- coding: utf-8 -*-
"""Constitutional Decision categories + mapping (Gate 2C Portfolio)."""
from __future__ import annotations

from typing import Any, Mapping

CATEGORY_STORE_HEALTH = "store_health"
CATEGORY_REVENUE = "revenue"
CATEGORY_PRODUCTS = "products"
CATEGORY_RECOVERY = "recovery"
CATEGORY_COMMUNICATION = "communication"
CATEGORY_CUSTOMER_BEHAVIOUR = "customer_behaviour"
CATEGORY_OPERATIONS = "operations"

ALL_CATEGORIES_V1 = (
    CATEGORY_STORE_HEALTH,
    CATEGORY_REVENUE,
    CATEGORY_PRODUCTS,
    CATEGORY_RECOVERY,
    CATEGORY_COMMUNICATION,
    CATEGORY_CUSTOMER_BEHAVIOUR,
    CATEGORY_OPERATIONS,
)

CATEGORY_LABEL_AR = {
    CATEGORY_STORE_HEALTH: "صحة المتجر",
    CATEGORY_REVENUE: "الإيرادات",
    CATEGORY_PRODUCTS: "المنتجات",
    CATEGORY_RECOVERY: "الاسترجاع",
    CATEGORY_COMMUNICATION: "التواصل",
    CATEGORY_CUSTOMER_BEHAVIOUR: "سلوك العملاء",
    CATEGORY_OPERATIONS: "التشغيل",
}

# Max 1 primary visible decision per category in the portfolio.
CATEGORY_PRIMARY_CAP_V1 = {c: 1 for c in ALL_CATEGORIES_V1}

NO_ACTION_AR = "لا إجراء مطلوب."


def _norm(v: Any) -> str:
    return str(v or "").strip().lower()


def map_decision_category_v1(candidate: Mapping[str, Any]) -> str:
    dtype = _norm(candidate.get("decision_type"))
    ftype = _norm(candidate.get("finding_type"))
    sources = " ".join(str(x) for x in (candidate.get("source_truth_types") or [])).lower()

    if dtype == "recoverability_gap" or "missing_contact" in ftype:
        return CATEGORY_RECOVERY
    if dtype == "waiting_recovery_work":
        return CATEGORY_OPERATIONS
    if any(
        t in ftype
        for t in (
            "high_interest_low_purchase",
            "low_product_interest",
            "repeated_interest",
            "return_without_purchase",
        )
    ):
        return CATEGORY_PRODUCTS
    if "dominant_hesitation" in ftype or "hesitation" in ftype:
        return CATEGORY_CUSTOMER_BEHAVIOUR
    if any(
        t in ftype
        for t in ("whatsapp", "recovery_channel", "message_timing", "communication")
    ) or "whatsapp" in sources:
        return CATEGORY_COMMUNICATION
    if "traffic" in ftype or "conversion" in ftype or "revenue" in ftype:
        return CATEGORY_REVENUE
    if dtype == "verified_existing_finding":
        return CATEGORY_STORE_HEALTH
    return CATEGORY_STORE_HEALTH


def attach_category_v1(candidate: dict[str, Any]) -> dict[str, Any]:
    cat = map_decision_category_v1(candidate)
    candidate["decision_category"] = cat
    candidate["decision_category_ar"] = CATEGORY_LABEL_AR.get(cat, cat)
    return candidate


__all__ = [
    "ALL_CATEGORIES_V1",
    "CATEGORY_LABEL_AR",
    "CATEGORY_PRIMARY_CAP_V1",
    "NO_ACTION_AR",
    "attach_category_v1",
    "map_decision_category_v1",
]
