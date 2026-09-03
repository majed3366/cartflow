# -*- coding: utf-8 -*-
"""Revenue Reality Validation V1 — contracts and permanent laws."""
from __future__ import annotations

from typing import Any, Mapping

VALIDATION_VERSION_V1 = "revenue_reality_validation_v1"
SIMULATION_STORE_SLUG = "rrv_sim_store_v1"  # isolated — never a production merchant slug
SIMULATION_DAYS = 30
SIMULATION_SEED = 20260902

LAW_NO_RECOMMENDATION_WITHOUT_EVIDENCE = "NO_RECOMMENDATION_WITHOUT_EVIDENCE"
LAW_NO_REVENUE_CLAIM_WITHOUT_MEASUREMENT = "NO_REVENUE_CLAIM_WITHOUT_MEASUREMENT"

MISSION_STATUS_PROPOSED = "proposed"
MISSION_STATUS_ACTIVE = "active"
MISSION_STATUS_MEASURING = "measuring"
MISSION_STATUS_WON = "won"
MISSION_STATUS_LOST = "lost"
MISSION_STATUS_INCONCLUSIVE = "inconclusive"
MISSION_STATUS_INSUFFICIENT = "insufficient_evidence"

MISSION_STATUSES = frozenset(
    {
        MISSION_STATUS_PROPOSED,
        MISSION_STATUS_ACTIVE,
        MISSION_STATUS_MEASURING,
        MISSION_STATUS_WON,
        MISSION_STATUS_LOST,
        MISSION_STATUS_INCONCLUSIVE,
        MISSION_STATUS_INSUFFICIENT,
    }
)

CHANNELS = ("direct", "organic", "tiktok", "instagram", "google")

CHANNEL_LABEL_AR = {
    "direct": "مباشر",
    "organic": "عضوي",
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "google": "بحث / Google",
}

SCENARIO_IDS = (
    "A_discovery",
    "B_high_interest_low_conversion",
    "C_price_sensitive",
    "D_discount_destroys_value",
    "E_bundle_cross_sell",
    "F_channel_quality",
    "G_retention",
    "H_insufficient_evidence",
)

CAPABILITY_SUPPORTED = "SUPPORTED_NOW"
CAPABILITY_PARTIAL = "PARTIAL"
CAPABILITY_MISSING_DATA = "MISSING_DATA"
CAPABILITY_MISSING_INSTRUMENTATION = "MISSING_INSTRUMENTATION"
CAPABILITY_NEEDS_EXTERNAL = "NEEDS_EXTERNAL_DATA"
CAPABILITY_UNSAFE = "UNSAFE_WITH_CURRENT_TRUTH"
CAPABILITY_DATA_GAP = "DATA_GAP"


def _norm(v: Any) -> str:
    return " ".join(str(v or "").strip().split())


def empty_opportunity_v1() -> dict[str, Any]:
    return {
        "ok": False,
        "schema": "revenue_opportunity_v1",
        "opportunity_id": "",
        "store_slug": SIMULATION_STORE_SLUG,
        "scope": {"type": "product", "id": ""},
        "evidence": [],
        "diagnosis": "",
        "commercial_opportunity": "",
        "recommended_action": "",
        "why": "",
        "measurement_plan": "",
        "recheck_condition": "",
        "confidence": "insufficient",
        "status": MISSION_STATUS_INSUFFICIENT,
        "scenario_id": "",
        "falsifiers": [],
        "simulation_only": True,
    }


def empty_mission_v1() -> dict[str, Any]:
    return {
        "ok": False,
        "schema": "revenue_mission_v1",
        "mission_id": "",
        "opportunity_id": "",
        "store_slug": SIMULATION_STORE_SLUG,
        "title_ar": "",
        "mission_ar": "",
        "why_matters_ar": "",
        "evidence_ar": [],
        "diagnosis_ar": "",
        "commercial_idea_ar": "",
        "action_ar": "",
        "measure_ar": "",
        "recheck_ar": "",
        "status": MISSION_STATUS_INSUFFICIENT,
        "confidence": "insufficient",
        "scenario_id": "",
        "what_not_to_do_ar": "",
        "alternatives_ar": [],
        "simulation_only": True,
    }


def validate_opportunity_v1(raw: Mapping[str, Any] | None) -> list[str]:
    o = raw if isinstance(raw, Mapping) else {}
    errors: list[str] = []
    for field in (
        "opportunity_id",
        "diagnosis",
        "commercial_opportunity",
        "recommended_action",
        "why",
        "measurement_plan",
        "recheck_condition",
    ):
        if not _norm(o.get(field)):
            errors.append(field)
    if not isinstance(o.get("evidence"), list) or not o.get("evidence"):
        errors.append("evidence")
    if o.get("status") not in MISSION_STATUSES:
        errors.append("status")
    for banned in ("chain_of_thought", "hidden_reasoning", "raw_model_trace"):
        if o.get(banned):
            errors.append(banned)
    return errors


def validate_mission_v1(raw: Mapping[str, Any] | None) -> list[str]:
    m = raw if isinstance(raw, Mapping) else {}
    errors: list[str] = []
    for field in (
        "mission_id",
        "mission_ar",
        "why_matters_ar",
        "diagnosis_ar",
        "commercial_idea_ar",
        "action_ar",
        "measure_ar",
        "recheck_ar",
    ):
        if not _norm(m.get(field)):
            errors.append(field)
    if not isinstance(m.get("evidence_ar"), list) or not m.get("evidence_ar"):
        errors.append("evidence_ar")
    if m.get("status") not in MISSION_STATUSES:
        errors.append("status")
    return errors


__all__ = [
    "CAPABILITY_DATA_GAP",
    "CAPABILITY_MISSING_DATA",
    "CAPABILITY_MISSING_INSTRUMENTATION",
    "CAPABILITY_NEEDS_EXTERNAL",
    "CAPABILITY_PARTIAL",
    "CAPABILITY_SUPPORTED",
    "CAPABILITY_UNSAFE",
    "CHANNELS",
    "CHANNEL_LABEL_AR",
    "LAW_NO_RECOMMENDATION_WITHOUT_EVIDENCE",
    "LAW_NO_REVENUE_CLAIM_WITHOUT_MEASUREMENT",
    "MISSION_STATUSES",
    "MISSION_STATUS_ACTIVE",
    "MISSION_STATUS_INCONCLUSIVE",
    "MISSION_STATUS_INSUFFICIENT",
    "MISSION_STATUS_LOST",
    "MISSION_STATUS_MEASURING",
    "MISSION_STATUS_PROPOSED",
    "MISSION_STATUS_WON",
    "SCENARIO_IDS",
    "SIMULATION_DAYS",
    "SIMULATION_SEED",
    "SIMULATION_STORE_SLUG",
    "VALIDATION_VERSION_V1",
    "empty_mission_v1",
    "empty_opportunity_v1",
    "validate_mission_v1",
    "validate_opportunity_v1",
]
