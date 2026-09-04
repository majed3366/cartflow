# -*- coding: utf-8 -*-
"""Commercial Opportunity Layer V1 — contract + truth classes."""
from __future__ import annotations

from typing import Any, Mapping

LAYER_VERSION = "commercial_opportunity_layer_v1"
LAYER_SCHEMA = "commercial_opportunity_package_v1"
OPPORTUNITY_SCHEMA = "commercial_opportunity_object_v1"

TRUTH_PRODUCTION_READY = "PRODUCTION_TRUTH_READY"
TRUTH_PRODUCTION_PARTIAL = "PRODUCTION_PARTIAL"
TRUTH_SIMULATION_ONLY = "SIMULATION_ONLY"
TRUTH_INSUFFICIENT = "INSUFFICIENT"

TRUTH_CLASSES = frozenset(
    {
        TRUTH_PRODUCTION_READY,
        TRUTH_PRODUCTION_PARTIAL,
        TRUTH_SIMULATION_ONLY,
        TRUTH_INSUFFICIENT,
    }
)

# Families allowed when production evidence exists (no lab-only discount/channel/cross-sell).
FAMILY_SHIPPING_FRICTION = "shipping_friction"
FAMILY_PRICE_HESITATION = "price_hesitation"
FAMILY_PRODUCT_CONFIDENCE = "product_confidence"
FAMILY_RECOVERY_HESITATION = "recovery_hesitation"
FAMILY_COMMUNICATION_FOLLOWUP = "communication_followup"
FAMILY_CART_BEHAVIOR = "cart_behavior"

SUPPORTED_FAMILIES = frozenset(
    {
        FAMILY_SHIPPING_FRICTION,
        FAMILY_PRICE_HESITATION,
        FAMILY_PRODUCT_CONFIDENCE,
        FAMILY_RECOVERY_HESITATION,
        FAMILY_COMMUNICATION_FOLLOWUP,
        FAMILY_CART_BEHAVIOR,
    }
)

HOME_QUESTION_OPERATIONAL_AR = "ما الذي يحتاج انتباهي الآن؟"
HOME_QUESTION_COMMERCIAL_AR = "أين توجد أهم فرصة تجارية الآن؟"
PRIMARY_EYEBROW_AR = "أهم فرصة تجارية الآن"
EMPTY_STATE_AR = "لا توجد فرصة تجارية جاهزة من أدلة متجرك الآن."
PARTIAL_GAP_PREFIX_AR = "أدلة جزئية — "


def _norm(text: Any) -> str:
    return " ".join(str(text or "").strip().split())


FORBIDDEN_SIM_MARKERS = (
    "SIMULATION_TRUTH",
    "simulation_truth",
    "rrv_sim_store",
    "preview_version",
    "commercial_intelligence_preview",
)


def package_has_simulation_leak(pkg: Mapping[str, Any] | None) -> bool:
    """Detect simulation / preview stamps that must never render on /dashboard."""
    if not isinstance(pkg, Mapping):
        return False
    blob = str(pkg)
    for m in FORBIDDEN_SIM_MARKERS:
        if m in blob:
            return True
    if str(pkg.get("truth_boundary") or "") == "SIMULATION_TRUTH":
        return True
    if pkg.get("production_truth_present") is False and pkg.get("simulation"):
        return True
    return False


def empty_package_v1(*, enabled: bool = True, reason: str = "") -> dict[str, Any]:
    return {
        "ok": True,
        "enabled": bool(enabled),
        "schema": LAYER_SCHEMA,
        "layer_version": LAYER_VERSION,
        "truth_boundary": "PRODUCTION_TRUTH",
        "production_truth_present": True,
        "question_ar": HOME_QUESTION_COMMERCIAL_AR,
        "primary": None,
        "secondaries": [],
        "empty": True,
        "empty_state_ar": EMPTY_STATE_AR,
        "suppressed": [],
        "cost": {
            "ai_calls": 0,
            "external_api_calls": 0,
            "estimated_extra_queries": 0,
            "path": "summary_truth→bounded_candidates→rank→materialize",
        },
        "reason": _norm(reason),
    }


def validate_opportunity_v1(obj: Mapping[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if not isinstance(obj, Mapping):
        return ["not_a_mapping"]
    for key in (
        "opportunity_id",
        "family",
        "truth_class",
        "title_ar",
        "why_ar",
        "action_ar",
        "measure_ar",
        "recheck_ar",
        "objective_ar",
    ):
        if not _norm(obj.get(key)):
            errors.append(f"missing:{key}")
    tc = str(obj.get("truth_class") or "")
    if tc not in TRUTH_CLASSES:
        errors.append("bad_truth_class")
    if tc == TRUTH_SIMULATION_ONLY:
        errors.append("simulation_forbidden_on_dashboard")
    fam = str(obj.get("family") or "")
    if fam and fam not in SUPPORTED_FAMILIES:
        errors.append("unsupported_family")
    # No revenue claim without measurement path
    measure = _norm(obj.get("measure_ar"))
    why = _norm(obj.get("why_ar"))
    claim_markers = ("إيراد مضمون", "زيادة مبيعات مضمونة", "ROAS", "+%", "SAR+")
    text = why + " " + _norm(obj.get("title_ar"))
    if any(m in text for m in claim_markers) and (
        not measure or "لا قياس" in measure.lower()
    ):
        errors.append("revenue_claim_without_measurement")
    return errors


__all__ = [
    "EMPTY_STATE_AR",
    "FAMILY_CART_BEHAVIOR",
    "FAMILY_COMMUNICATION_FOLLOWUP",
    "FAMILY_PRICE_HESITATION",
    "FAMILY_PRODUCT_CONFIDENCE",
    "FAMILY_RECOVERY_HESITATION",
    "FAMILY_SHIPPING_FRICTION",
    "FORBIDDEN_SIM_MARKERS",
    "HOME_QUESTION_COMMERCIAL_AR",
    "HOME_QUESTION_OPERATIONAL_AR",
    "LAYER_SCHEMA",
    "LAYER_VERSION",
    "OPPORTUNITY_SCHEMA",
    "PARTIAL_GAP_PREFIX_AR",
    "PRIMARY_EYEBROW_AR",
    "SUPPORTED_FAMILIES",
    "TRUTH_CLASSES",
    "TRUTH_INSUFFICIENT",
    "TRUTH_PRODUCTION_PARTIAL",
    "TRUTH_PRODUCTION_READY",
    "TRUTH_SIMULATION_ONLY",
    "empty_package_v1",
    "package_has_simulation_leak",
    "validate_opportunity_v1",
]
