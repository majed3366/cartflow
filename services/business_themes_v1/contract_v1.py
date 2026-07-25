# -*- coding: utf-8 -*-
"""
Business Theme Contract V1.

A Theme is the canonical commercial truth — never a counter, recommendation, or UI card.
Constitution: One Business Theme. One Owner. Many Consumers.
"""
from __future__ import annotations

from typing import Any, Mapping

BUSINESS_THEMES_VERSION_V1 = "business_themes_v1"
THEME_SCHEMA_V1 = "business_theme_v1"

THEME_RECOVERY_OPPORTUNITY = "recovery_opportunity"
THEME_SHIPPING_FRICTION = "shipping_friction"
THEME_PRODUCT_DEMAND = "product_demand"
THEME_PRODUCT_CONVERSION = "product_conversion"
THEME_CUSTOMER_RETURN_BEHAVIOUR = "customer_return_behaviour"
THEME_COMMUNICATION_COVERAGE = "communication_coverage"
THEME_STORE_HEALTH = "store_health"
THEME_PRICING_OPPORTUNITY = "pricing_opportunity"
THEME_INVENTORY_RISK = "inventory_risk"

THEME_TYPES_V1 = (
    THEME_RECOVERY_OPPORTUNITY,
    THEME_SHIPPING_FRICTION,
    THEME_PRODUCT_DEMAND,
    THEME_PRODUCT_CONVERSION,
    THEME_CUSTOMER_RETURN_BEHAVIOUR,
    THEME_COMMUNICATION_COVERAGE,
    THEME_STORE_HEALTH,
    THEME_PRICING_OPPORTUNITY,
    THEME_INVENTORY_RISK,
)

# Primary owner surface per theme type.
OWNER_DECISION_WORKSPACE = "decision_workspace"
OWNER_HOME = "home"
OWNER_COMMUNICATION = "communication"
OWNER_CARTS = "carts"

THEME_PRIMARY_OWNER_V1 = {
    THEME_RECOVERY_OPPORTUNITY: OWNER_DECISION_WORKSPACE,
    THEME_SHIPPING_FRICTION: OWNER_DECISION_WORKSPACE,
    THEME_PRODUCT_DEMAND: OWNER_DECISION_WORKSPACE,
    THEME_PRODUCT_CONVERSION: OWNER_DECISION_WORKSPACE,
    THEME_CUSTOMER_RETURN_BEHAVIOUR: OWNER_DECISION_WORKSPACE,
    THEME_COMMUNICATION_COVERAGE: OWNER_COMMUNICATION,
    THEME_STORE_HEALTH: OWNER_HOME,
    THEME_PRICING_OPPORTUNITY: OWNER_DECISION_WORKSPACE,
    THEME_INVENTORY_RISK: OWNER_DECISION_WORKSPACE,
}

THEME_TITLE_AR_V1 = {
    THEME_RECOVERY_OPPORTUNITY: "فرصة استعادة المبيعات",
    THEME_SHIPPING_FRICTION: "احتكاك الشحن",
    THEME_PRODUCT_DEMAND: "طلب المنتجات",
    THEME_PRODUCT_CONVERSION: "تحويل المنتجات",
    THEME_CUSTOMER_RETURN_BEHAVIOUR: "سلوك عودة العملاء",
    THEME_COMMUNICATION_COVERAGE: "تغطية التواصل",
    THEME_STORE_HEALTH: "صحة المتجر",
    THEME_PRICING_OPPORTUNITY: "فرصة التسعير",
    THEME_INVENTORY_RISK: "مخاطر المخزون",
}

REQUIRED_THEME_FIELDS_V1 = (
    "theme_id",
    "theme_type",
    "title_ar",
    "executive_summary_ar",
    "supporting_fact_ids",
    "evidence",
    "confidence",
    "business_impact",
    "freshness",
    "priority",
    "primary_owner",
    "destination_surfaces",
)


def empty_theme_shell_v1() -> dict[str, Any]:
    return {
        "schema": THEME_SCHEMA_V1,
        "version": BUSINESS_THEMES_VERSION_V1,
        "theme_id": "",
        "theme_type": "",
        "title_ar": "",
        "title_en": "",
        "executive_summary_ar": "",
        "executive_summary_en": "",
        "supporting_fact_ids": [],
        "supporting_facts": [],
        "evidence": {"source_kinds": [], "fact_count": 0, "capability_ids": []},
        "confidence": {"level": "", "ar": "", "score": None},
        "business_impact": {"category": "", "ar": ""},
        "freshness": {"status": "current", "as_of_utc": ""},
        "priority": 0,
        "primary_owner": "",
        "destination_surfaces": {
            "home_teaser": False,
            "decision_workspace": False,
            "communication": False,
        },
        "admitted": False,
        "internal_only": True,
        "merchant_action_exists": False,
        "recommendation": None,
    }


def validate_business_theme_v1(theme: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(theme, Mapping):
        return ["not_a_mapping"]
    for key in REQUIRED_THEME_FIELDS_V1:
        if key not in theme:
            errors.append(f"missing:{key}")
    if str(theme.get("theme_type") or "") not in THEME_TYPES_V1:
        errors.append("invalid_theme_type")
    if not str(theme.get("executive_summary_ar") or "").strip():
        errors.append("missing_executive_summary")
    if not list(theme.get("supporting_fact_ids") or []):
        errors.append("no_supporting_facts")
    if theme.get("recommendation") not in (None, "", {}):
        errors.append("recommendation_forbidden")
    return errors


__all__ = [
    "BUSINESS_THEMES_VERSION_V1",
    "OWNER_CARTS",
    "OWNER_COMMUNICATION",
    "OWNER_DECISION_WORKSPACE",
    "OWNER_HOME",
    "REQUIRED_THEME_FIELDS_V1",
    "THEME_COMMUNICATION_COVERAGE",
    "THEME_CUSTOMER_RETURN_BEHAVIOUR",
    "THEME_PRIMARY_OWNER_V1",
    "THEME_PRODUCT_CONVERSION",
    "THEME_PRODUCT_DEMAND",
    "THEME_RECOVERY_OPPORTUNITY",
    "THEME_SCHEMA_V1",
    "THEME_SHIPPING_FRICTION",
    "THEME_STORE_HEALTH",
    "THEME_TITLE_AR_V1",
    "THEME_TYPES_V1",
    "empty_theme_shell_v1",
    "validate_business_theme_v1",
]
