# -*- coding: utf-8 -*-
"""Commercial Decision Intelligence V1 — three-mission refinement tests."""
from __future__ import annotations

from services.commercial_decision_intelligence_v1 import (
    CDI_CHANNEL,
    CDI_DISCOVERY,
    CDI_DISCOUNT,
    decision_packs_v1,
)
from services.revenue_reality_validation_v1.review_lab_v1 import build_review_lab_payload_v1


def test_phase_packs_distinctive_not_generic():
    packs = decision_packs_v1()
    assert "أوقف" in packs[CDI_DISCOUNT]["commercial_move_ar"] or "إيقاف" in packs[CDI_DISCOUNT]["commercial_move_ar"]
    assert "مترددين" in packs[CDI_DISCOUNT]["commercial_move_ar"]
    assert "هامش إنتاج" in packs[CDI_DISCOUNT]["what_happens_ar"] or "محاكاة" in packs[CDI_DISCOUNT]["what_happens_ar"]
    assert "لا يقنع" in packs[CDI_DISCOVERY]["what_happens_ar"]
    assert "موضع" in packs[CDI_DISCOVERY]["commercial_move_ar"]
    assert "داخل متجرك" in packs[CDI_CHANNEL]["what_happens_ar"]
    assert "ميزانية" not in packs[CDI_CHANNEL]["commercial_move_ar"]
    for p in packs.values():
        assert p["falsifier_ar"]
        assert "حسّن التسويق" not in p["commercial_move_ar"]


def test_cdi_home_three_missions():
    p = build_review_lab_payload_v1()
    assert p.get("cdi_version")
    primary = p["home"]["primary_mission"]
    assert primary["scenario_id"] == CDI_DISCOUNT
    assert "محاكاة" in primary["home_why_ar"]
    secs = p["home"]["secondary_opportunities"]
    assert len(secs) == 2
    # CDL V1.1 home integrates shipping + merchandising as competing secondaries
    assert {s["scenario_id"] for s in secs} == {
        "B_high_interest_low_conversion",
        "A_discovery",
    }
    assert p["home"]["priority_economics_ar"]


def test_cdi_workspace_contracts():
    p = build_review_lab_payload_v1()
    ws = p["workspace"]["cdi_missions"]
    assert len(ws) >= 3
    discount = next(m for m in ws if m["scenario_id"] == "D_discount_destroys_value")
    assert discount.get("decision_contract_ar") or discount.get("cdi_refined")
    assert discount.get("falsifier_ar") or discount.get("lens_conflict_ar")
    # discount lens conflict surfaced on CDI pack
    assert discount.get("lens_conflict_ar") or any(
        m.get("lens_conflict_ar") for m in ws if m.get("scenario_id") == "D_discount_destroys_value"
    )


def test_cdi_gates_and_laws():
    p = build_review_lab_payload_v1()
    assert p["intelligence_gates"]["cdi_generic"] == 0
    assert p["intelligence_gates"]["cdi_abbrev"] == 0
    assert p["intelligence_gates"]["cdi_falsifiers"] == 3
    assert p["laws"]["NO_RECOMMENDATION_WITHOUT_EVIDENCE"] == "PASS"
    assert p["laws"]["NO_REVENUE_CLAIM_WITHOUT_MEASUREMENT"] == "PASS"
    assert p["language_audit"]["primary_banned_abbrev_count"] == 0
