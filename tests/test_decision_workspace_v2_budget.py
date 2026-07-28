# -*- coding: utf-8 -*-
"""Decision Workspace V2 budget + Operational Language V1."""
from __future__ import annotations

from services.decision_workspace_v2.budget_v1 import apply_decision_workspace_v2_budget
from services.decision_workspace_v2.narrative_v1 import (
    EXEC_DOMAIN_INTERNAL,
    EXEC_DOMAIN_PLATFORM,
    EXTERNAL_DEPENDENCY,
    IDENTITY_OBSERVATION,
    NEEDS_MORE_EVIDENCE,
    READY,
    act_now_ar_v1,
    card_identity_v1,
    commitment_ar_v1,
    destination_for_commitment_v1,
    execution_domain_v1,
    execution_is_ready_v1,
    execution_readiness_v1,
    expected_outcome_ar_v1,
    how_execute_ar_v1,
    looks_like_cartflow_work,
    observation_ar_v1,
    operational_guidance_ar_v1,
    operational_meaning_ar_v1,
    priority_reason_ar_v1,
    where_execute_ar_v1,
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
                "business_meaning_ar": f"يغادر العملاء بعد الشحن للمنتج {i}",
                "observation_ar": f"يغادر العملاء بعد الشحن للمنتج {i}",
                "evidence_summary": f"دليل {i}",
                "ignore_consequence_ar": f"ضغط على إتمام الشراء {i}",
                "first_step_ar": f"راجع إعدادات الشحن للمنتج {i}",
                "expected_outcome_ar": f"انخفاض المغادرة بعد الشحن {i}",
                "diagnosis_status": "supported",
                "confidence_level": "medium",
                "business_domain": "shipping",
                "subject_ar": f"منتج {i}",
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
    assert out["decision_workspace_operational_language_v1"] is True
    assert out["mission_question"] == "ما الذي يحتاج انتباهك الآن؟"
    assert out["zone_a"] == []
    assert len(out["zone_b"]) == 4
    primary = out["zone_b"][0]
    assert primary["is_primary_decision"] is True
    assert primary["decision_workspace_operational_language_v1"] is True
    assert primary["observation_ar"]
    assert primary["operational_meaning_ar"]
    assert primary["operational_guidance_ar"]
    assert primary["priority_reason_ar"]
    assert primary["observation_ar"] != primary["priority_reason_ar"]
    assert primary["execution_readiness"]
    assert primary["execution_domain"]
    assert primary["card_identity"]
    assert primary["execution_available"] is True
    assert primary["execution_where_ar"]
    assert primary["execution_how_ar"]
    assert primary["expected_outcome_ar"]
    assert "موقفاً تجارياً" not in primary["operational_guidance_ar"]
    assert "بوعي" not in primary["operational_guidance_ar"]
    assert all(not c.get("is_primary_decision") for c in out["zone_b"][1:])
    assert out["zone_b"][1]["face_mode"] == "next_compact"


def test_commitment_rejects_investigative_and_management_jargon():
    assert looks_like_cartflow_work("اجمع المزيد من الأدلة")
    assert looks_like_cartflow_work("اتخذ موقفاً تجارياً بخصوص Nano")
    card = {
        "diagnosis_status": "supported",
        "first_step_ar": "اجمع المزيد من الأدلة عن Nano",
        "required_merchant_action": "اجمع المزيد من الأدلة عن Nano",
        "subject_ar": "Nano 20W",
        "business_domain": "shipping",
        "diagnosis_ar": "مغادرة عند الشحن.",
        "observation_ar": "يغادر العملاء بعد خطوة الشحن في مسار Nano 20W.",
    }
    text = commitment_ar_v1(card)
    assert "اجمع" not in text
    assert "موقفاً" not in text
    assert "راجع" in text or "إعدادات" in text


def test_insufficient_evidence_no_fake_execution_or_cta():
    card = {
        "diagnosis_status": "insufficient_evidence",
        "diagnosis_ar": "مغادرة عند الشحن دون سبب واضح.",
        "observation_ar": "يغادر العملاء بعد خطوة الشحن.",
        "first_step_ar": "اجمع المزيد من الأدلة",
        "business_domain": "shipping",
        "subject_ar": "Nano 20W",
    }
    text = operational_guidance_ar_v1(card)
    assert "لا تغيّر" in text or "لا تُجرِ" in text
    assert "اجمع" not in text
    assert execution_readiness_v1(card) == NEEDS_MORE_EVIDENCE
    assert execution_is_ready_v1(NEEDS_MORE_EVIDENCE) is False
    assert where_execute_ar_v1(card, EXEC_DOMAIN_PLATFORM, NEEDS_MORE_EVIDENCE) == ""
    assert how_execute_ar_v1(card, EXEC_DOMAIN_PLATFORM, NEEDS_MORE_EVIDENCE) == ""
    assert expected_outcome_ar_v1(card, "") == ""
    href, label = destination_for_commitment_v1(card)
    assert href == ""
    assert label == ""
    assert card_identity_v1(card, NEEDS_MORE_EVIDENCE) == IDENTITY_OBSERVATION
    out = apply_decision_workspace_v2_budget(
        {
            "zone_b": [
                {
                    **card,
                    "decision_id": "d1",
                    "card_kind": "composed_decision",
                    "constitution_v1": True,
                    "is_primary_decision": True,
                }
            ]
        }
    )
    primary = out["zone_b"][0]
    assert primary["execution_available"] is False
    assert primary["view_details_href"] == ""
    assert primary["cartflow_continues_ar"]
    assert primary["priority_reason_ar"]


def test_observation_before_guidance_and_meaning_not_repeat():
    card = {
        "diagnosis_status": "supported",
        "observation_ar": "يغادر العملاء بعد خطوة الشحن في مسار Nano 20W.",
        "business_domain": "shipping",
        "subject_ar": "Nano 20W",
        "ignore_consequence_ar": "هذه الخطوة تضغط على إتمام الشراء.",
        "has_decision": True,
    }
    obs = observation_ar_v1(card)
    meaning = operational_meaning_ar_v1(card, obs)
    guidance = operational_guidance_ar_v1(card)
    assert obs
    assert meaning
    assert meaning != obs
    assert guidance
    assert not guidance.startswith(obs[:12])


def test_priority_reason_is_evidence_specific():
    card = {
        "diagnosis_status": "supported",
        "observation_ar": "يغادر العملاء بعد خطوة الشحن في مسار Nano 20W.",
        "business_domain": "shipping",
        "subject_ar": "Nano 20W",
        "affected_customers_count": 42,
        "has_decision": True,
    }
    pr = priority_reason_ar_v1(card, is_primary=True)
    assert "42" in pr
    assert pr != observation_ar_v1(card)
    assert priority_reason_ar_v1(card, is_primary=False) == ""


def test_routing_follows_execution_domain_not_fixed_products():
    carts = {
        "diagnosis_status": "supported",
        "business_domain": "carts",
        "diagnosis_ar": "سلال تحتاج متابعة.",
        "observation_ar": "سلال بلا أرقام تحتاج متابعة.",
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
        "observation_ar": "مغادرة عند الشحن.",
        "has_decision": True,
    }
    assert execution_domain_v1(ship) == EXEC_DOMAIN_PLATFORM
    assert execution_readiness_v1(ship) == EXTERNAL_DEPENDENCY
    href2, label2 = destination_for_commitment_v1(ship)
    assert href2.startswith("#settings")
    assert "إعدادات" in label2 or "شحن" in label2

    biz = {
        "diagnosis_status": "supported",
        "business_domain": "packaging",
        "diagnosis_ar": "تحسين التغليف مطلوب.",
        "observation_ar": "التغليف يضعف ثقة العميل.",
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
        "observation_ar": "اهتمام مرتفع دون إتمام شراء.",
        "has_decision": True,
    }
    href, _ = destination_for_commitment_v1(card)
    assert not href.startswith("#workspace")


def test_executable_has_what_where_how_result():
    card = {
        "diagnosis_status": "supported",
        "business_domain": "shipping",
        "observation_ar": "يغادر العملاء بعد خطوة الشحن.",
        "subject_ar": "Nano 20W",
        "has_decision": True,
        "execution_readiness": READY,
    }
    assert execution_is_ready_v1(READY)
    assert where_execute_ar_v1(card, EXEC_DOMAIN_PLATFORM, READY)
    assert how_execute_ar_v1(card, EXEC_DOMAIN_PLATFORM, READY)
    assert expected_outcome_ar_v1(card, "")
    assert "راجع" in operational_guidance_ar_v1(card) or "إعدادات" in operational_guidance_ar_v1(
        card
    )
