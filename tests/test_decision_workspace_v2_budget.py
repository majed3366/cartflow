# -*- coding: utf-8 -*-
"""Decision Workspace V2 budget + Refinement V1 narrative."""
from __future__ import annotations

from services.decision_workspace_v2.budget_v1 import apply_decision_workspace_v2_budget
from services.decision_workspace_v2.narrative_v1 import (
    commitment_ar_v1,
    looks_like_cartflow_work,
)


def test_budget_caps_next_at_three():
    cards = []
    for i in range(8):
        cards.append(
            {
                "decision_id": f"dce:{i}",
                "card_kind": "composed_decision",
                "constitution_v1": True,
                "is_primary_decision": i == 0,
                "why_ar": f"سبب واضح رقم {i}",
                "business_meaning_ar": f"تشخيص تجاري {i}",
                "evidence_summary": f"دليل {i}",
                "ignore_consequence_ar": f"أثر إن تجاهلنا {i}",
                "first_step_ar": f"قرّر بخصوص المنتج {i}",
                "expected_outcome_ar": f"تحسن الإيراد {i}",
                "diagnosis_status": "supported",
                "confidence_level": "medium",
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
    assert out["decision_workspace_refinement_v1"] is True
    assert out["zone_a"] == []
    assert len(out["zone_b"]) == 4
    primary = out["zone_b"][0]
    assert primary["is_primary_decision"] is True
    assert primary["diagnosis_ar"]
    assert primary["confidence_ar"]
    assert primary["cartflow_responsibility_ar"]
    assert primary["commitment_ar"]
    assert "راجع" not in primary["commitment_ar"]
    assert all(not c.get("is_primary_decision") for c in out["zone_b"][1:])
    assert out["zone_b"][1]["face_mode"] == "next_compact"


def test_commitment_rejects_cartflow_investigative_work():
    assert looks_like_cartflow_work("راجع مسار التحويل للمنتج")
    card = {
        "diagnosis_status": "supported",
        "first_step_ar": "راجع مسار التحويل لـ Nano",
        "required_merchant_action": "راجع مسار التحويل لـ Nano",
        "subject_ar": "Nano 20W",
        "business_domain": "products",
        "diagnosis_ar": "اهتمام دون إتمام شراء.",
    }
    text = commitment_ar_v1(card)
    assert "راجع" not in text
    assert "قرّر" in text or "قرار" in text


def test_insufficient_evidence_commitment_is_wait():
    card = {
        "diagnosis_status": "insufficient_evidence",
        "diagnosis_ar": "مغادرة عند الشحن دون سبب واضح.",
        "first_step_ar": "اجمع المزيد من الأدلة",
    }
    text = commitment_ar_v1(card)
    assert "انتظر" in text or "لا تغيّر" in text
    assert "اجمع" not in text
