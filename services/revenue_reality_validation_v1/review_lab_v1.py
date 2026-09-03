# -*- coding: utf-8 -*-
"""Scenario reality validation + Revenue Intelligence Model V1 lab orchestration."""
from __future__ import annotations

from typing import Any

from services.commercial_decision_intelligence_v1 import (
    CDI_VERSION_V1,
    apply_cdi_overlay_v1,
    audit_cdi_generic_and_abbrev,
    cdi_workspace_missions_v1,
)
from services.commercial_decision_library_v1_1 import (
    CDL_VERSION_V1_1,
    apply_cdl_overlay_v1_1,
    audit_cdl_v1_1,
    cdl_home_pick_v1_1,
    cdl_workspace_missions_v1_1,
)
from services.revenue_intelligence_model_v1.compose_v1 import (
    audit_primary_surfaces_language_v1,
    build_intelligence_overlay_v1,
    group_missions_commercial_v1,
    scenario_intelligence_answers_v1,
    workspace_for_mission_v1,
)
from services.revenue_intelligence_model_v1.contracts_v1 import INTELLIGENCE_VERSION_V1
from services.revenue_reality_validation_v1.capability_matrix_v1 import build_capability_matrix_v1
from services.revenue_reality_validation_v1.contracts_v1 import (
    LAW_NO_RECOMMENDATION_WITHOUT_EVIDENCE,
    LAW_NO_REVENUE_CLAIM_WITHOUT_MEASUREMENT,
    SCENARIO_IDS,
    SIMULATION_DAYS,
    SIMULATION_STORE_SLUG,
    VALIDATION_VERSION_V1,
)
from services.revenue_reality_validation_v1.mission_composer_v1 import compose_missions_v1
from services.revenue_reality_validation_v1.opportunity_detector_v1 import detect_opportunities_v1
from services.revenue_reality_validation_v1.simulation_world_v1 import build_simulation_world_v1


def product_intelligence_rows_v1(world: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for pid, a in (world.get("aggregates") or {}).items():
        hes = a.get("hesitation") or {}
        ab = max(1, int(a.get("abandons") or 0))
        top_hes = max(hes, key=lambda k: hes.get(k, 0)) if hes else "none"
        ch = a.get("channels") or {}
        best_ch = None
        best_score = -1.0
        for cname, cv in ch.items():
            if int(cv.get("views") or 0) < 50:
                continue
            score = float(cv.get("purchase_rate_of_atc") or 0) * float(cv.get("aov") or 0)
            if score > best_score:
                best_score = score
                best_ch = cname
        roles = a.get("scenario_roles") or []
        if "H_insufficient_evidence" in roles:
            question_answer = "الدليل غير كافٍ — لا توصية تجارية بعد."
        elif "A_discovery" in roles:
            question_answer = "موضع/اكتشاف — رفع الترتيب في التصنيف"
        elif "B_high_interest_low_conversion" in roles:
            question_answer = "احتكاك تكلفة الشحن"
        elif "C_price_sensitive" in roles:
            question_answer = "تجربة عرض محدودة"
        elif "D_discount_destroys_value" in roles:
            question_answer = "إيقاف أو إعادة تصميم الخصم"
        elif "F_channel_quality" in roles:
            question_answer = "اختبار جودة قناة اكتساب"
        elif "E_bundle_cross_sell" in roles or "G_retention" in roles:
            question_answer = "عرض مكمل بعد الشراء"
        else:
            question_answer = "لا مهمة أولوية فورية"
        rows.append(
            {
                "product_id": pid,
                "name_ar": a.get("name_ar"),
                "category": a.get("category"),
                "discovery": {
                    "views": a.get("views"),
                    "signal": "low" if int(a.get("views") or 0) < 800 else "ok",
                },
                "interest": {"atc": a.get("atc"), "atc_rate": a.get("atc_rate")},
                "conversion": {
                    "purchases": a.get("purchases"),
                    "purchase_rate_of_atc": a.get("purchase_rate_of_atc"),
                },
                "revenue_contribution": {"revenue": a.get("revenue"), "aov": a.get("aov")},
                "hesitation": {
                    "top": top_hes,
                    "share": round(float(hes.get(top_hes) or 0) / ab, 3),
                    "counts": hes,
                },
                "channel_quality_best": best_ch,
                "retention_relationship": pid in ("rrv_p05_bundle_a", "rrv_p06_bundle_b"),
                "commercial_question_ar": "ما الفرصة أو المشكلة التجارية لهذا المنتج؟",
                "commercial_answer_ar": question_answer,
                "scenario_roles": roles,
            }
        )
    return rows


def build_review_lab_payload_v1() -> dict[str, Any]:
    world = build_simulation_world_v1()
    opportunities = detect_opportunities_v1(world)
    missions = compose_missions_v1(opportunities)
    product_rows = product_intelligence_rows_v1(world)
    intel = build_intelligence_overlay_v1(
        missions=missions,
        world=world,
        product_rows=product_rows,
    )
    # Commercial Decision Intelligence V1 then Library V1.1 (D/E/F families)
    enriched = apply_cdi_overlay_v1(intel["missions_enriched"])
    enriched = apply_cdl_overlay_v1_1(enriched)
    home = cdl_home_pick_v1_1(enriched)
    primary = home.get("primary_mission")
    secondary = home.get("secondary_opportunities") or []
    groups = group_missions_commercial_v1(enriched)
    # Workspace: CDL families + CDI discount for continuity
    cdi_ws = cdi_workspace_missions_v1(enriched)
    cdl_ws = cdl_workspace_missions_v1_1(enriched)
    seen = set()
    ws_missions: list[dict[str, Any]] = []
    for m in list(cdl_ws) + list(cdi_ws):
        sid = m.get("scenario_id")
        if sid in seen:
            continue
        seen.add(sid)
        ws_missions.append(m)
    cdi_audit = audit_cdi_generic_and_abbrev(enriched)
    cdl_audit = audit_cdl_v1_1(enriched)

    scenario_rows = [
        scenario_intelligence_answers_v1(enriched, s) for s in SCENARIO_IDS
    ]
    validated = sum(1 for s in scenario_rows if s.get("ready"))
    matrix = build_capability_matrix_v1()

    law_rec = True
    for o in opportunities:
        if o.get("scenario_id") == "H_insufficient_evidence":
            if o.get("status") != "insufficient_evidence":
                law_rec = False
            if o.get("confidence") != "insufficient":
                law_rec = False
        if not o.get("evidence") and o.get("status") == "proposed":
            law_rec = False
        if o.get("status") == "proposed" and not o.get("falsifiers"):
            law_rec = False

    law_rev = True
    for o in opportunities:
        if o.get("status") == "won" and "إيراد" not in str(o.get("evidence") or []):
            law_rev = False

    for m in enriched:
        if m.get("status") in ("proposed", "active", "measuring", "won"):
            if m.get("scenario_id") == "H_insufficient_evidence":
                continue
            if not (m.get("measure_ar") and m.get("recheck_ar")):
                law_rev = False

    generic_ideas = sum(1 for m in enriched if m.get("generic_idea_flag"))
    flat_list = 0

    payload = {
        "ok": True,
        "schema": "commercial_decision_library_lab_v1_1",
        "validation_version": VALIDATION_VERSION_V1,
        "intelligence_version": INTELLIGENCE_VERSION_V1,
        "cdi_version": CDI_VERSION_V1,
        "cdl_version": CDL_VERSION_V1_1,
        "simulation_only": True,
        "production_mutation": False,
        "store_slug": SIMULATION_STORE_SLUG,
        "laws": {
            LAW_NO_RECOMMENDATION_WITHOUT_EVIDENCE: "PASS" if law_rec else "FAIL",
            LAW_NO_REVENUE_CLAIM_WITHOUT_MEASUREMENT: "PASS" if law_rev else "FAIL",
        },
        "world_meta": {
            "days": world.get("days"),
            "product_count": world.get("product_count"),
            "seed": world.get("seed"),
            "margin_intelligence": world.get("margin_intelligence"),
            "comparative_market_pricing": world.get("comparative_market_pricing"),
        },
        "home": {
            "question_ar": home.get("question_ar"),
            "primary_mission": primary,
            "secondary_opportunities": secondary,
            "secondary_count": len(secondary),
            "priority_economics_ar": home.get("priority_economics_ar"),
        },
        "workspace": {
            **workspace_for_mission_v1(primary),
            "cdi_missions": ws_missions,
            "note_ar": "مكتبة قرارات تجارية: بيع متقاطع، شحن، موضع — مع قرارات CDI السابقة.",
        },
        "product_intelligence": {
            "question_ar": "ما الفرصة أو المشكلة التجارية لهذا المنتج؟",
            "mode": "commercial_state",
            "states": intel["product_commercial_states"],
            "rows_supporting": product_rows,
        },
        "missions": {
            "groups": groups,
            "all": enriched,
            "flat_list": flat_list,
        },
        "opportunities": opportunities,
        "scenarios": scenario_rows,
        "capability_matrix": matrix,
        "intelligence_gates": {
            "generic_commercial_ideas": generic_ideas,
            "flat_mission_list": flat_list,
            "scenarios_validated": validated,
            "cdi_generic": cdi_audit["generic_advice_count"],
            "cdi_abbrev": cdi_audit["primary_tech_abbrev_count"],
            "cdi_falsifiers": cdi_audit["falsifier_count"],
            "cdl_generic": cdl_audit["generic_advice_count"],
            "cdl_abbrev": cdl_audit["primary_tech_abbrev_count"],
            "cdl_falsifiers": cdl_audit["falsifier_count"],
        },
        "scoreboard_seed": {
            "products_simulated": world.get("product_count"),
            "days_simulated": SIMULATION_DAYS,
            "revenue_scenarios": len(SCENARIO_IDS),
            "scenarios_validated": validated,
            "revenue_missions_generated": len(enriched),
            "home_secondary": len(secondary),
        },
    }
    payload["language_audit"] = audit_primary_surfaces_language_v1(payload)
    return payload


__all__ = ["build_review_lab_payload_v1"]
