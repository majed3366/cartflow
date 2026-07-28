# -*- coding: utf-8 -*-
"""Decision Workspace V2 — Decision Storytelling face (DIF V1)."""
from __future__ import annotations

from services.decision_workspace_v2.budget_v1 import apply_decision_workspace_v2_budget
from services.decision_workspace_v2.narrative_v1 import (
    EXEC_DOMAIN_INTERNAL,
    EXEC_DOMAIN_PLATFORM,
    EXTERNAL_DEPENDENCY,
    NEEDS_MORE_EVIDENCE,
    READY,
    action_is_ready_v1,
    commitment_ar_v1,
    decision_sentence_ar_v1,
    destination_for_commitment_v1,
    execution_domain_v1,
    execution_readiness_v1,
    looks_like_cartflow_work,
    observation_ar_v1,
    priority_reason_ar_v1,
    sanitize_merchant_story_text_v1,
)


def test_budget_storytelling_face_primary():
    cards = []
    for i in range(8):
        cards.append(
            {
                "decision_id": f"dce:{i}",
                "card_kind": "composed_decision",
                "constitution_v1": True,
                "is_primary_decision": i == 0,
                "observation_ar": f"يغادر العملاء بعد خطوة الشحن للمنتج {i}",
                "ignore_consequence_ar": f"ضغط على إتمام الشراء {i}",
                "first_step_ar": f"افتح إعدادات الشحن للمنتج {i}",
                "diagnosis_status": "supported",
                "confidence_level": "medium",
                "business_domain": "shipping",
                "subject_ar": f"منتج {i}",
                "execution_readiness": READY,
            }
        )
    out = apply_decision_workspace_v2_budget(
        {
            "zone_a": [{"decision_id": "vip:1"}],
            "zone_b": cards,
        }
    )
    assert out["decision_workspace_storytelling_face_v1"] is True
    assert out["mission_question"] == "ما الذي يحتاج انتباهك الآن؟"
    assert len(out["zone_b"]) == 4
    primary = out["zone_b"][0]
    assert primary["priority_reason_ar"]
    assert primary["observation_ar"]
    assert primary["decision_sentence_ar"]
    assert primary["priority_rank_label_ar"] == "الأولوية الأولى"
    assert primary["execution_available"] is True
    assert primary["view_details_href"]
    assert primary.get("cartflow_continues_ar") == ""
    assert "موقفاً تجارياً" not in primary["decision_sentence_ar"]
    assert out["zone_b"][1]["priority_rank_label_ar"] == "بعدها"


def test_needs_more_evidence_no_action_cta():
    card = {
        "diagnosis_status": "insufficient_evidence",
        "observation_ar": "يغادر العملاء بعد خطوة الشحن.",
        "business_domain": "shipping",
        "subject_ar": "Nano 20W",
        "decision_id": "d1",
        "card_kind": "composed_decision",
        "constitution_v1": True,
        "is_primary_decision": True,
    }
    assert execution_readiness_v1(card) == NEEDS_MORE_EVIDENCE
    assert action_is_ready_v1(NEEDS_MORE_EVIDENCE) is False
    assert decision_sentence_ar_v1(card) == "لا تغيّر سياسة الشحن الآن."
    href, label = destination_for_commitment_v1(card)
    assert href == ""
    assert label == ""
    out = apply_decision_workspace_v2_budget({"zone_b": [card]})
    primary = out["zone_b"][0]
    assert primary["execution_available"] is False
    assert primary["view_details_href"] == ""
    assert primary["priority_reason_ar"]
    assert "cs:" not in primary["observation_ar"]


def test_sanitize_strips_engine_ids():
    assert "cs:" not in sanitize_merchant_story_text_v1("cs:abc-123 يغادر العملاء")
    assert "diagnostic:" not in sanitize_merchant_story_text_v1(
        "diagnostic:shipping يغادر"
    )


def test_external_dependency_has_decision_but_no_action_cta():
    ship = {
        "diagnosis_status": "supported",
        "business_domain": "shipping",
        "observation_ar": "مغادرة عند الشحن.",
        "has_decision": True,
    }
    assert execution_domain_v1(ship) == EXEC_DOMAIN_PLATFORM
    assert execution_readiness_v1(ship) == EXTERNAL_DEPENDENCY
    assert action_is_ready_v1(EXTERNAL_DEPENDENCY) is False
    href, _ = destination_for_commitment_v1(ship)
    assert href == ""
    assert decision_sentence_ar_v1(ship)


def test_ready_internal_has_action():
    carts = {
        "diagnosis_status": "supported",
        "business_domain": "carts",
        "observation_ar": "سلال بلا أرقام تحتاج متابعة.",
        "has_decision": True,
        "execution_readiness": READY,
    }
    assert execution_domain_v1(carts) == EXEC_DOMAIN_INTERNAL
    href, label = destination_for_commitment_v1(carts)
    assert href.startswith("#carts")
    assert label


def test_never_routes_to_workspace():
    card = {
        "diagnosis_status": "supported",
        "view_details_href": "#workspace",
        "business_domain": "products",
        "observation_ar": "اهتمام مرتفع دون إتمام شراء.",
        "has_decision": True,
        "execution_readiness": READY,
    }
    href, _ = destination_for_commitment_v1(card)
    assert not href.startswith("#workspace")


def test_commitment_rejects_investigative_jargon():
    assert looks_like_cartflow_work("اجمع المزيد من الأدلة")
    text = commitment_ar_v1(
        {
            "diagnosis_status": "supported",
            "first_step_ar": "اجمع المزيد من الأدلة عن Nano",
            "subject_ar": "Nano 20W",
            "business_domain": "shipping",
            "observation_ar": "يغادر العملاء بعد خطوة الشحن.",
            "execution_readiness": READY,
        }
    )
    assert "اجمع" not in text


def test_priority_not_repeat_observation():
    card = {
        "diagnosis_status": "supported",
        "observation_ar": "يغادر العملاء بعد خطوة الشحن في مسار Nano 20W.",
        "business_domain": "shipping",
        "subject_ar": "Nano 20W",
        "affected_customers_count": 42,
        "has_decision": True,
        "execution_readiness": READY,
    }
    pr = priority_reason_ar_v1(card, is_primary=True)
    assert pr
    assert pr != observation_ar_v1(card)
