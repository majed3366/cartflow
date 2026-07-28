# -*- coding: utf-8 -*-
"""Decision Workspace V2 budget — 1 Primary + ≤3 Next."""
from __future__ import annotations

from services.decision_workspace_v2.budget_v1 import apply_decision_workspace_v2_budget


def test_budget_caps_next_at_three():
    cards = []
    for i in range(8):
        cards.append(
            {
                "decision_id": f"dce:{i}",
                "card_kind": "composed_decision",
                "constitution_v1": True,
                "is_primary_decision": i == 0,
                "why_ar": f"سبب {i}",
                "business_meaning_ar": f"تشخيص {i}",
                "evidence_summary": f"دليل {i}",
                "ignore_consequence_ar": f"أثر {i}",
                "first_step_ar": f"التزام {i}",
                "expected_outcome_ar": f"نتيجة {i}",
            }
        )
    out = apply_decision_workspace_v2_budget(
        {
            "zone_a": [{"decision_id": "vip:1"}],
            "zone_b": cards,
            "decision_composition_v1": {
                "category_landscape": [{"category": "x"}],
                "needs_action_now": 9,
                "monitor": 3,
            },
        }
    )
    assert out["decision_workspace_v2"] is True
    assert out["zone_a"] == []
    assert len(out["zone_b"]) == 4
    assert out["zone_b"][0]["is_primary_decision"] is True
    assert out["zone_b"][0]["diagnosis_ar"]
    assert out["zone_b"][0]["commitment_ar"]
    assert all(not c.get("is_primary_decision") for c in out["zone_b"][1:])
    assert out["decision_composition_v1"]["category_landscape"] == []
    assert out["decision_workspace_v2_budget"]["next"] == 3
    assert out["decision_workspace_v2_budget"]["future_waiting"] == 4


def test_commitment_not_used_as_diagnosis_when_identical():
    out = apply_decision_workspace_v2_budget(
        {
            "zone_a": [],
            "zone_b": [
                {
                    "decision_id": "dce:1",
                    "card_kind": "composed_decision",
                    "constitution_v1": True,
                    "is_primary_decision": True,
                    "decision_ar": "أصلح تكلفة الشحن",
                    "title_ar": "أصلح تكلفة الشحن",
                    "first_step_ar": "أصلح تكلفة الشحن",
                    "required_merchant_action": "أصلح تكلفة الشحن",
                    "business_meaning_ar": "العملاء يتركون السلة عند الشحن.",
                    "why_ar": "التكلفة تظهر متأخراً.",
                    "evidence_summary": "مغادرة عند مرحلة الشحن",
                    "ignore_consequence_ar": "استمرار الترك",
                    "expected_outcome_ar": "تشخيص أوضح",
                }
            ],
        }
    )
    card = out["zone_b"][0]
    assert "الشحن" in card["diagnosis_ar"] or "يتركون" in card["diagnosis_ar"]
    assert card["commitment_ar"] == "أصلح تكلفة الشحن"
    assert card["diagnosis_ar"] != card["commitment_ar"]
