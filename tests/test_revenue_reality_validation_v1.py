# -*- coding: utf-8 -*-
"""Revenue Reality Validation V1 — isolated simulation tests."""
from __future__ import annotations

from services.revenue_reality_validation_v1.contracts_v1 import (
    LAW_NO_RECOMMENDATION_WITHOUT_EVIDENCE,
    LAW_NO_REVENUE_CLAIM_WITHOUT_MEASUREMENT,
    SCENARIO_IDS,
    SIMULATION_DAYS,
    SIMULATION_STORE_SLUG,
)
from services.revenue_reality_validation_v1.opportunity_detector_v1 import detect_opportunities_v1
from services.revenue_reality_validation_v1.review_lab_v1 import build_review_lab_payload_v1
from services.revenue_reality_validation_v1.simulation_world_v1 import build_simulation_world_v1


def test_simulation_world_isolated_and_sized():
    world = build_simulation_world_v1()
    assert world["ok"] is True
    assert world["simulation_only"] is True
    assert world["store_slug"] == SIMULATION_STORE_SLUG
    assert world["days"] == SIMULATION_DAYS
    assert 8 <= world["product_count"] <= 12
    assert world["margin_intelligence"]["production_status"] == "DATA_GAP"
    assert world["comparative_market_pricing"]["classification"] == "UNSAFE_WITH_CURRENT_TRUTH"
    # must not look like a production merchant slug
    assert world["store_slug"] != "demo"
    assert "production" not in world["store_slug"]


def test_scenarios_a_through_h_validated():
    world = build_simulation_world_v1()
    opps = detect_opportunities_v1(world)
    by_sc = {s: [o for o in opps if o.get("scenario_id") == s] for s in SCENARIO_IDS}
    for sid in SCENARIO_IDS:
        assert by_sc[sid], f"missing scenario {sid}"
    # A discovery proposed
    a = next(o for o in by_sc["A_discovery"] if o["status"] == "proposed")
    assert a["ok"] and a["falsifiers"]
    # B shipping not discount-first
    b = by_sc["B_high_interest_low_conversion"][0]
    assert "خصم" in b["why"] or "خصم" in b["recommended_action"] or "لا" in (b.get("why") or "")
    assert "شحن" in b["diagnosis"]
    # C bounded experiment
    c = next(o for o in by_sc["C_price_sensitive"] if o["status"] == "proposed")
    assert "14" in c["recheck_condition"] or "10" in c["recommended_action"]
    # D stop promo
    d = by_sc["D_discount_destroys_value"][0]
    assert "إيقاف" in d["recommended_action"] or "إيقاف" in d["commercial_opportunity"]
    # E bundle
    e = by_sc["E_bundle_cross_sell"][0]
    assert e["scope"]["type"] == "product_pair"
    # F channel
    f = next(o for o in by_sc["F_channel_quality"] if "tiktok_vs_google" in o["opportunity_id"])
    assert "TikTok" in str(f["evidence"])
    assert "عامة" in f["why"] or "لهذا المنتج" in f["diagnosis"]
    # G retention
    g = by_sc["G_retention"][0]
    assert g["scope"]["type"] == "customer_segment"
    assert "اكتساب" in g["evidence"][2] or "احتفاظ" in g["diagnosis"]
    # H refuse
    h = by_sc["H_insufficient_evidence"][0]
    assert h["status"] == "insufficient_evidence"
    assert h["confidence"] == "insufficient"


def test_review_lab_laws_and_home_mission():
    payload = build_review_lab_payload_v1()
    assert payload["ok"] is True
    assert payload["production_mutation"] is False
    assert payload["laws"][LAW_NO_RECOMMENDATION_WITHOUT_EVIDENCE] == "PASS"
    assert payload["laws"][LAW_NO_REVENUE_CLAIM_WITHOUT_MEASUREMENT] == "PASS"
    assert payload["home"]["primary_mission"] is not None
    assert payload["home"]["primary_mission"]["status"] == "proposed"
    assert payload["scoreboard_seed"]["scenarios_validated"] == len(SCENARIO_IDS)
    assert payload["missions"]["groups"]["الدليل غير كافٍ"]
    assert any(m["status"] == "won" for m in payload["missions"]["groups"]["مكتملة"])
    assert any(m["status"] == "measuring" for m in payload["missions"]["groups"]["تحت القياس"])


def test_discount_trap_uses_simulation_only_cost_label():
    world = build_simulation_world_v1()
    eco = world["aggregates"]["rrv_p04_discount_trap"]["promo_economics_simulation_only"]
    assert "SIMULATION-ONLY" in eco["label"]
    assert eco["contribution_worse_on_promo"] is True
