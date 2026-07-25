# -*- coding: utf-8 -*-
"""
Commerce Situation Contract V1.

Canonical merchant-understandable commercial situation.
Entity-bound — never a type-only Theme bucket.

One Situation may consume many Business Facts.
Facts / Themes must not publish to merchant surfaces when Situations are enabled.
"""
from __future__ import annotations

from typing import Any, Mapping

COMMERCE_SITUATIONS_VERSION_V1 = "commerce_situations_v1"
SITUATION_SCHEMA_V1 = "commerce_situation_v1"

# Situation kinds = commercial situations (Principle 7), not fact_type taxonomy.
KIND_INTEREST_WITHOUT_PURCHASE = "interest_without_purchase"
KIND_SHIPPING_FRICTION = "shipping_friction"
KIND_RECOVERY_OPPORTUNITY = "recovery_opportunity"
KIND_COMMUNICATION = "communication_coverage"
KIND_STORE_HEALTH = "store_health"
KIND_PRODUCT_DEMAND = "product_demand"
KIND_CHECKOUT_ABANDONMENT = "checkout_abandonment"

SITUATION_KINDS_V1 = (
    KIND_INTEREST_WITHOUT_PURCHASE,
    KIND_SHIPPING_FRICTION,
    KIND_RECOVERY_OPPORTUNITY,
    KIND_COMMUNICATION,
    KIND_STORE_HEALTH,
    KIND_PRODUCT_DEMAND,
    KIND_CHECKOUT_ABANDONMENT,
)

OWNER_DECISION_WORKSPACE = "decision_workspace"
OWNER_HOME = "home"
OWNER_COMMUNICATION = "communication"
OWNER_CARTS = "carts"

REQUIRED_SITUATION_FIELDS_V1 = (
    "situation_id",
    "situation_kind",
    "title_ar",
    "business_question_ar",
    "why_it_matters_ar",
    "affected_products",
    "affected_customers",
    "affected_carts",
    "supporting_fact_ids",
    "evidence",
    "confidence",
    "merchant_action_ar",
    "expected_business_impact_ar",
    "primary_owner",
)


def empty_situation_shell_v1() -> dict[str, Any]:
    return {
        "schema": SITUATION_SCHEMA_V1,
        "version": COMMERCE_SITUATIONS_VERSION_V1,
        "situation_id": "",
        "situation_kind": "",
        "title_ar": "",
        "title_en": "",
        "business_question_ar": "",
        "business_question_en": "",
        "why_it_matters_ar": "",
        "why_it_matters_en": "",
        "executive_summary_ar": "",
        "affected_products": [],
        "affected_customers": {"summary_ar": "", "count": None},
        "affected_carts": {"summary_ar": "", "count": None},
        "supporting_fact_ids": [],
        "supporting_facts": [],
        "evidence": {
            "source_kinds": ["business_facts_v1"],
            "fact_count": 0,
            "capability_ids": [],
            "observation_ids": [],
        },
        "confidence": {"level": "", "ar": "", "score": None},
        "merchant_action_ar": "",
        "expected_business_impact_ar": "",
        "freshness": {"status": "current", "as_of_utc": ""},
        "priority": 0,
        "primary_owner": OWNER_DECISION_WORKSPACE,
        "destination_surfaces": {
            "home_teaser": False,
            "decision_workspace": False,
            "carts": False,
            "communication": False,
            "products": False,
        },
        "admitted": False,
        "subject": {"kind": "", "id": "", "name_ar": ""},
        "recommendation": None,
        "product_intelligence": False,
    }


def validate_commerce_situation_v1(situation: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(situation, Mapping):
        return ["not_a_mapping"]
    for key in REQUIRED_SITUATION_FIELDS_V1:
        if key not in situation:
            errors.append(f"missing:{key}")
    if str(situation.get("situation_kind") or "") not in SITUATION_KINDS_V1:
        errors.append("invalid_situation_kind")
    if not str(situation.get("executive_summary_ar") or situation.get("why_it_matters_ar") or "").strip():
        errors.append("missing_executive_summary")
    if not list(situation.get("supporting_fact_ids") or []):
        errors.append("no_supporting_facts")
    if situation.get("recommendation") not in (None, "", {}):
        errors.append("recommendation_forbidden")
    if situation.get("product_intelligence") not in (False, None, 0):
        errors.append("product_intelligence_forbidden")
    return errors


__all__ = [
    "COMMERCE_SITUATIONS_VERSION_V1",
    "KIND_CHECKOUT_ABANDONMENT",
    "KIND_COMMUNICATION",
    "KIND_INTEREST_WITHOUT_PURCHASE",
    "KIND_PRODUCT_DEMAND",
    "KIND_RECOVERY_OPPORTUNITY",
    "KIND_SHIPPING_FRICTION",
    "KIND_STORE_HEALTH",
    "OWNER_CARTS",
    "OWNER_COMMUNICATION",
    "OWNER_DECISION_WORKSPACE",
    "OWNER_HOME",
    "REQUIRED_SITUATION_FIELDS_V1",
    "SITUATION_KINDS_V1",
    "SITUATION_SCHEMA_V1",
    "empty_situation_shell_v1",
    "validate_commerce_situation_v1",
]
