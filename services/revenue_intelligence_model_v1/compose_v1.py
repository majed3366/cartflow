# -*- coding: utf-8 -*-
"""Compose Revenue Intelligence Model V1 on top of RRV missions."""
from __future__ import annotations

from typing import Any

from services.revenue_intelligence_model_v1.commercial_imagination_v1 import (
    apply_commercial_imagination_v1,
)
from services.revenue_intelligence_model_v1.contracts_v1 import (
    INTELLIGENCE_VERSION_V1,
    TIER_COMPLETED,
    TIER_DECIDE_NOW,
    TIER_IMPORTANT,
    TIER_INSUFFICIENT,
    TIER_IN_PROGRESS,
    TIER_LABEL_AR,
    TIER_MEASURING,
    TIER_MONITOR,
)
from services.revenue_intelligence_model_v1.merchant_language_v1 import (
    apply_merchant_language_to_mission_v1,
    commercial_state_for_product_v1,
    count_banned_abbreviations,
)
from services.revenue_intelligence_model_v1.priority_model_v1 import assign_tiers_and_sort_v1


def _is_primary_candidate(m: dict[str, Any]) -> bool:
    oid = str(m.get("opportunity_id") or "")
    if oid.endswith(("_measuring", "_active", "_fail")) or "measurement_won" in oid:
        return False
    return m.get("status") == "proposed" and m.get("scenario_id") != "H_insufficient_evidence"


def enrich_missions_v1(
    missions: list[dict[str, Any]],
    world: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    prioritized = assign_tiers_and_sort_v1(missions, world)
    out: list[dict[str, Any]] = []
    for m in prioritized:
        m2 = apply_commercial_imagination_v1(m)
        # refresh why_now after imagination (priority text already set)
        m2["why_now_short_ar"] = (m2.get("why_prioritized_ar") or "")[:220]
        m2 = apply_merchant_language_to_mission_v1(m2)
        out.append(m2)
    return out


def group_missions_commercial_v1(missions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {
        "تحتاج قرارك": [],
        "قيد التنفيذ": [],
        "تحت القياس": [],
        "مكتملة": [],
        "للمراقبة": [],
        "الدليل غير كافٍ": [],
    }
    for m in missions:
        st = m.get("status")
        tier = m.get("priority_tier")
        if st == "insufficient_evidence" or tier == TIER_INSUFFICIENT:
            groups["الدليل غير كافٍ"].append(m)
        elif st == "active" or tier == TIER_IN_PROGRESS:
            groups["قيد التنفيذ"].append(m)
        elif st == "measuring" or tier == TIER_MEASURING:
            groups["تحت القياس"].append(m)
        elif st in ("won", "lost", "inconclusive") or tier == TIER_COMPLETED:
            groups["مكتملة"].append(m)
        elif tier == TIER_MONITOR and st == "proposed":
            groups["للمراقبة"].append(m)
        elif st == "proposed":
            groups["تحتاج قرارك"].append(m)
        else:
            groups["للمراقبة"].append(m)

    # Order تحتاج قرارك by internal priority
    groups["تحتاج قرارك"] = sorted(
        groups["تحتاج قرارك"],
        key=lambda x: int(x.get("internal_priority_score") or 0),
        reverse=True,
    )
    return groups


def home_composition_v1(missions: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [m for m in missions if _is_primary_candidate(m)]
    candidates = sorted(
        candidates,
        key=lambda x: int(x.get("internal_priority_score") or 0),
        reverse=True,
    )
    primary = candidates[0] if candidates else None
    secondary = candidates[1:3] if len(candidates) > 1 else []
    return {
        "question_ar": "أين توجد أهم فرصة إيراد الآن؟",
        "primary_mission": primary,
        "secondary_opportunities": secondary,
        "secondary_count": len(secondary),
    }


def workspace_for_mission_v1(m: dict[str, Any] | None) -> dict[str, Any]:
    if not m:
        return {"selected_mission": None}
    alts = m.get("alternatives_ar") or []
    # Only keep alternatives that materially affect decision (cap 2)
    material = alts[:2] if alts else []
    return {
        "selected_mission": m,
        "sections": {
            "الدليل": m.get("evidence_ar") or [],
            "التشخيص": m.get("diagnosis_short_ar") or m.get("diagnosis_ar"),
            "الفكرة التجارية": m.get("commercial_idea_ar"),
            "لماذا تناسب": m.get("why_idea_fits_ar"),
            "الإجراء": m.get("action_ar"),
            "ما لا ننصح به": m.get("what_not_to_do_ar"),
            "القياس": m.get("measure_ar"),
            "متى نعيد النظر": m.get("recheck_ar"),
            "تعارض العدسات": m.get("lens_conflict_ar"),
            "بدائل مؤثرة": material,
            "لماذا الأولوية": m.get("why_prioritized_ar"),
        },
    }


def product_commercial_states_v1(pi_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [commercial_state_for_product_v1(r) for r in pi_rows]


def scenario_intelligence_answers_v1(missions: list[dict[str, Any]], scenario_id: str) -> dict[str, Any]:
    matches = [
        m
        for m in missions
        if m.get("scenario_id") == scenario_id
        and not str(m.get("opportunity_id") or "").endswith(("_measuring", "_active", "_fail"))
        and "measurement_won" not in str(m.get("opportunity_id") or "")
    ]
    if not matches and scenario_id == "H_insufficient_evidence":
        matches = [m for m in missions if m.get("scenario_id") == scenario_id]
    m = matches[0] if matches else None
    if not m:
        return {"scenario_id": scenario_id, "ready": False, "status": "NOT READY"}

    answers = {
        "why_prioritized": m.get("why_prioritized_ar") or "",
        "commercial_idea": m.get("commercial_idea_ar") or "",
        "evidence": " | ".join(m.get("evidence_ar") or []),
        "merchant_do": m.get("action_ar") or "",
        "merchant_not": m.get("what_not_to_do_ar") or "",
        "measure": m.get("measure_ar") or "",
        "change_mind": m.get("recheck_ar") or "",
    }
    generic_fail = any(
        g in (answers["commercial_idea"] or "").lower()
        for g in ("زد التعرض", "حسّن التسويق", "increase exposure", "run ads")
    )
    ready = all(answers.values()) and not generic_fail
    if scenario_id == "H_insufficient_evidence":
        ready = "غير كاف" in answers["commercial_idea"] or "لا" in answers["merchant_do"]
    return {
        "scenario_id": scenario_id,
        "ready": ready,
        "status": "VALIDATED" if ready else "FAIL",
        "answers": answers,
        "generic_idea": generic_fail,
        "objective": m.get("commercial_objective_ar"),
        "tier": m.get("priority_tier_ar"),
    }


def audit_primary_surfaces_language_v1(payload: dict[str, Any]) -> dict[str, Any]:
    home = payload.get("home") or {}
    primary = home.get("primary_mission") or {}
    texts = [
        primary.get("mission_ar"),
        primary.get("home_why_ar"),
        primary.get("home_action_ar"),
        primary.get("home_measure_ar"),
        primary.get("commercial_idea_ar"),
        primary.get("why_prioritized_ar"),
    ]
    for s in home.get("secondary_opportunities") or []:
        texts.extend([s.get("mission_ar"), s.get("commercial_idea_ar"), s.get("why_now_short_ar")])
    banned = count_banned_abbreviations(*[str(t or "") for t in texts])
    return {"primary_banned_abbrev_count": banned}


def build_intelligence_overlay_v1(
    *,
    missions: list[dict[str, Any]],
    world: dict[str, Any],
    product_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    enriched = enrich_missions_v1(missions, world)
    home = home_composition_v1(enriched)
    groups = group_missions_commercial_v1(enriched)
    product_states = product_commercial_states_v1(product_rows)
    return {
        "ok": True,
        "intelligence_version": INTELLIGENCE_VERSION_V1,
        "missions_enriched": enriched,
        "home": home,
        "workspace": workspace_for_mission_v1(home.get("primary_mission")),
        "mission_groups": groups,
        "product_commercial_states": product_states,
        "tier_labels": TIER_LABEL_AR,
    }


__all__ = [
    "audit_primary_surfaces_language_v1",
    "build_intelligence_overlay_v1",
    "enrich_missions_v1",
    "group_missions_commercial_v1",
    "home_composition_v1",
    "scenario_intelligence_answers_v1",
    "workspace_for_mission_v1",
]
