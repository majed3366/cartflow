# -*- coding: utf-8 -*-
"""Commercial Decision Library V1.1 tests."""
from __future__ import annotations

from services.commercial_decision_library_v1_1 import (
    CDL_CROSS_SELL,
    CDL_MERCHANDISING,
    CDL_SHIPPING,
    decision_packs_v1_1,
)
from services.revenue_reality_validation_v1.review_lab_v1 import build_review_lab_payload_v1


def test_packs_distinctive():
    packs = decision_packs_v1_1()
    assert packs[CDL_CROSS_SELL]["relationship_class"] == "POST_PURCHASE_OFFER"
    assert "خصم حزمة" in packs[CDL_CROSS_SELL]["commercial_move_ar"] or "بدون خصم" in packs[CDL_CROSS_SELL]["commercial_move_ar"]
    assert "شحنًا مجانيًا" in packs[CDL_SHIPPING]["what_not_ar"] or "شحن مجاني" in packs[CDL_SHIPPING]["what_not_ar"]
    assert "تكلفة الشحن" in packs[CDL_SHIPPING]["what_happens_ar"]
    assert "تصنيف" in packs[CDL_MERCHANDISING]["commercial_move_ar"]
    assert "زيادة الظهور" not in packs[CDL_MERCHANDISING]["commercial_move_ar"]
    for p in packs.values():
        assert p["falsifier_ar"]


def test_cdl_home_priority_integration():
    p = build_review_lab_payload_v1()
    assert p.get("cdl_version")
    assert p["home"]["primary_mission"]["scenario_id"] == "D_discount_destroys_value"
    secs = {s["scenario_id"] for s in p["home"]["secondary_opportunities"]}
    assert CDL_SHIPPING in secs
    assert CDL_MERCHANDISING in secs
    assert p["home"]["secondary_count"] <= 2
    assert "شحن" in p["home"]["priority_economics_ar"]


def test_cdl_workspace_and_gates():
    p = build_review_lab_payload_v1()
    sids = {m["scenario_id"] for m in p["workspace"]["cdi_missions"]}
    assert CDL_CROSS_SELL in sids and CDL_SHIPPING in sids and CDL_MERCHANDISING in sids
    for m in p["workspace"]["cdi_missions"]:
        if m.get("cdl_refined"):
            assert m.get("decision_contract_ar")
            assert m.get("falsifier_ar")
    assert p["intelligence_gates"]["cdl_generic"] == 0
    assert p["intelligence_gates"]["cdl_abbrev"] == 0
    assert p["intelligence_gates"]["cdl_falsifiers"] == 3
    assert p["laws"]["NO_RECOMMENDATION_WITHOUT_EVIDENCE"] == "PASS"
    assert p["laws"]["NO_REVENUE_CLAIM_WITHOUT_MEASUREMENT"] == "PASS"


def test_cross_sell_class_and_shipping_not_free():
    p = build_review_lab_payload_v1()
    xs = next(m for m in p["missions"]["all"] if m.get("scenario_id") == CDL_CROSS_SELL and m.get("cdl_refined") and m.get("status") == "proposed")
    assert xs.get("relationship_class") == "POST_PURCHASE_OFFER"
    sh = next(m for m in p["missions"]["all"] if m.get("scenario_id") == CDL_SHIPPING and m.get("cdl_refined") and m.get("status") == "proposed")
    assert "مجاني" in sh["what_not_to_do_ar"]
    assert sh.get("friction_class") == "shipping_price_friction"
