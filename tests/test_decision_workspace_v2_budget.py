# -*- coding: utf-8 -*-
"""Decision Workspace V2 budget + Refinement V2 narrative / routing."""
from __future__ import annotations

from services.decision_workspace_v2.budget_v1 import apply_decision_workspace_v2_budget
from services.decision_workspace_v2.narrative_v1 import (
    EXEC_DOMAIN_INTERNAL,
    EXEC_DOMAIN_PLATFORM,
    EXTERNAL_DEPENDENCY,
    NEEDS_MORE_EVIDENCE,
    commitment_ar_v1,
    destination_for_commitment_v1,
    execution_domain_v1,
    execution_readiness_v1,
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
    assert out["decision_workspace_refinement_v2"] is True
    assert out["zone_a"] == []
    assert len(out["zone_b"]) == 4
    primary = out["zone_b"][0]
    assert primary["is_primary_decision"] is True
    assert primary["diagnosis_ar"]
    assert primary["confidence_ar"]
    assert primary["cartflow_responsibility_ar"]
    assert primary["commitment_ar"]
    assert primary["execution_readiness"]
    assert primary["execution_domain"]
    assert primary["execution_where_ar"]
    assert primary["execution_how_ar"]
    assert primary["execution_verify_ar"]
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
    assert execution_readiness_v1(card) == NEEDS_MORE_EVIDENCE
    href, label = destination_for_commitment_v1(card)
    assert href == "#home"
    assert "ملخص" in label or "أدلة" in label


def test_routing_follows_execution_domain_not_fixed_products():
    carts = {
        "diagnosis_status": "supported",
        "business_domain": "carts",
        "diagnosis_ar": "سلال تحتاج متابعة.",
        "has_decision": True,
    }
    assert execution_domain_v1(carts) == EXEC_DOMAIN_INTERNAL
    href, label = destination_for_commitment_v1(carts)
    assert href.startswith("#carts")
    assert "Products" not in label
    assert "#workspace" not in href

    ship = {
        "diagnosis_status": "supported",
        "business_domain": "shipping",
        "diagnosis_ar": "مغادرة عند الشحن.",
        "has_decision": True,
    }
    assert execution_domain_v1(ship) == EXEC_DOMAIN_PLATFORM
    assert execution_readiness_v1(ship) == EXTERNAL_DEPENDENCY
    href2, label2 = destination_for_commitment_v1(ship)
    assert href2.startswith("#settings")
    assert "منصة" in label2 or "إعدادات" in label2

    biz = {
        "diagnosis_status": "supported",
        "business_domain": "packaging",
        "diagnosis_ar": "تحسين التغليف مطلوب.",
        "has_decision": True,
        "execution_domain": "business",
    }
    href3, label3 = destination_for_commitment_v1(biz)
    assert href3 == ""
    assert "عملك" in label3


def test_never_routes_to_workspace():
    card = {
        "diagnosis_status": "supported",
        "view_details_href": "#workspace",
        "business_domain": "products",
        "diagnosis_ar": "اهتمام دون شراء.",
        "has_decision": True,
    }
    href, _ = destination_for_commitment_v1(card)
    assert not href.startswith("#workspace")
