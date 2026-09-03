# -*- coding: utf-8 -*-
"""Revenue Intelligence Model V1 — lab layer tests."""
from __future__ import annotations

from services.revenue_intelligence_model_v1.contracts_v1 import BANNED_PRIMARY_ABBREVIATIONS
from services.revenue_reality_validation_v1.contracts_v1 import SCENARIO_IDS
from services.revenue_reality_validation_v1.review_lab_v1 import build_review_lab_payload_v1


def test_priority_explainable_and_home_caps():
    p = build_review_lab_payload_v1()
    primary = p["home"]["primary_mission"]
    assert primary is not None
    assert primary["priority_tier_ar"] == "تحتاج قرارك الآن"
    assert "أولوية" in primary["why_prioritized_ar"] or "لأن" in primary["why_prioritized_ar"]
    assert "Priority score" not in primary["why_prioritized_ar"]
    assert primary.get("forecast_used") is False
    assert p["home"]["secondary_count"] <= 2
    assert len(p["home"]["secondary_opportunities"]) <= 2


def test_commercial_imagination_not_generic():
    p = build_review_lab_payload_v1()
    assert p["intelligence_gates"]["generic_commercial_ideas"] == 0
    primary = p["home"]["primary_mission"]
    idea = primary["commercial_idea_ar"]
    assert any(tok in idea for tok in ("اختبر", "إيقاف", "أوقف", "إبراز", "وضّح", "توضيح", "شغّل", "أرسل", "فعّل"))
    assert "Increase exposure" not in idea
    assert len(idea) > 20
    # every proposed mission has a concrete idea + objective (except insufficient)
    for m in p["missions"]["groups"]["تحتاج قرارك"]:
        assert m.get("commercial_idea_ar")
        assert m.get("commercial_objective")


def test_multi_lens_conflict_surfaced_when_present():
    p = build_review_lab_payload_v1()
    # C or D should expose lens conflict on enriched mission
    conflicts = [
        m
        for m in p["missions"]["all"]
        if m.get("lens_conflict_ar") and m.get("scenario_id") in ("C_price_sensitive", "D_discount_destroys_value")
    ]
    assert conflicts


def test_merchant_language_no_primary_abbrev():
    p = build_review_lab_payload_v1()
    assert p["language_audit"]["primary_banned_abbrev_count"] == 0
    primary = p["home"]["primary_mission"]
    blob = " ".join(
        [
            primary.get("home_why_ar") or "",
            primary.get("home_action_ar") or "",
            primary.get("commercial_idea_ar") or "",
            primary.get("why_prioritized_ar") or "",
        ]
    )
    for abbr in BANNED_PRIMARY_ABBREVIATIONS:
        assert abbr not in blob


def test_missions_grouped_not_flat_and_ordered():
    p = build_review_lab_payload_v1()
    assert p["missions"]["flat_list"] == 0
    groups = p["missions"]["groups"]
    assert "تحتاج قرارك" in groups
    decide = groups["تحتاج قرارك"]
    assert decide
    scores = [int(m.get("internal_priority_score") or 0) for m in decide]
    assert scores == sorted(scores, reverse=True)


def test_product_commercial_state_not_analytics_table_primary():
    p = build_review_lab_payload_v1()
    assert p["product_intelligence"]["mode"] == "commercial_state"
    argan = next(s for s in p["product_intelligence"]["states"] if "أرغان" in (s.get("name_ar") or ""))
    assert argan["states"]["الاكتشاف"] == "ضعيف"
    assert argan["states"]["الاهتمام"] == "قوي"
    assert "موضع" in argan["states"]["الفرصة الحالية"] or "اكتشاف" in argan["states"]["الفرصة الحالية"]


def test_insufficient_and_won_and_objectives():
    p = build_review_lab_payload_v1()
    insuf = p["missions"]["groups"]["الدليل غير كافٍ"]
    assert insuf
    assert "لا" in insuf[0]["action_ar"] or "غير كاف" in insuf[0]["commercial_idea_ar"]
    won = [m for m in p["missions"]["groups"]["مكتملة"] if m.get("status") == "won"]
    assert won
    assert any(m.get("commercial_objective") for m in p["missions"]["all"] if m.get("status") == "proposed")


def test_all_scenarios_intelligence_validated():
    p = build_review_lab_payload_v1()
    assert p["scoreboard_seed"]["scenarios_validated"] == len(SCENARIO_IDS)
    for s in p["scenarios"]:
        assert s["ready"] is True, s
