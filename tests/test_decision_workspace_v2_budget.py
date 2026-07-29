# -*- coding: utf-8 -*-
"""Decision Workspace V2 — Simplification V1."""
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
    evidence_lines_ar_v1,
    execution_domain_v1,
    execution_readiness_v1,
    looks_like_cartflow_work,
    sanitize_merchant_story_text_v1,
)


def test_budget_simplification_primary():
    cards = []
    for i in range(8):
        cards.append(
            {
                "decision_id": f"dce:{i}",
                "card_kind": "composed_decision",
                "constitution_v1": True,
                "is_primary_decision": i == 0,
                "observation_ar": f"يغادر العملاء بعد خطوة الشحن للمنتج {i}",
                "first_step_ar": f"افتح إعدادات الشحن للمنتج {i}",
                "diagnosis_status": "supported",
                "confidence_level": "high",
                "business_domain": "shipping",
                "subject_ar": f"منتج {i}",
                "leave_rate_pct": 41,
                "execution_readiness": READY,
            }
        )
    out = apply_decision_workspace_v2_budget({"zone_b": cards})
    assert out["decision_workspace_simplification_v1"] is True
    primary = out["zone_b"][0]
    assert primary["priority_rank_label_ar"] == "الأولوية الأولى"
    assert primary["evidence_lines_ar"]
    assert any("41%" in x for x in primary["evidence_lines_ar"])
    assert any("الثقة" in x for x in primary["evidence_lines_ar"])
    assert primary["decision_sentence_ar"]
    assert primary["execution_available"] is True
    assert primary["view_details_href"]
    assert primary["priority_reason_ar"] == ""
    assert primary.get("why_believe_ar") == ""
    assert out["zone_b"][1]["priority_rank_label_ar"] == "الأولوية الثانية"


def test_needs_more_evidence_shows_wait_not_cta():
    card = {
        "diagnosis_status": "insufficient_evidence",
        "observation_ar": "يغادر العملاء بعد خطوة الشحن.",
        "business_domain": "shipping",
        "subject_ar": "Nano 20W",
        "decision_id": "d1",
        "card_kind": "composed_decision",
        "constitution_v1": True,
        "is_primary_decision": True,
        "confidence_level": "low",
    }
    assert execution_readiness_v1(card) == NEEDS_MORE_EVIDENCE
    assert action_is_ready_v1(NEEDS_MORE_EVIDENCE) is False
    assert "حتى تتضح" in decision_sentence_ar_v1(card)
    out = apply_decision_workspace_v2_budget({"zone_b": [card]})
    primary = out["zone_b"][0]
    assert primary["execution_available"] is False
    assert primary["view_details_href"] == ""
    assert primary["action_wait_lines_ar"]
    assert "لا يوجد إجراء" in primary["action_wait_lines_ar"][0]


def test_sanitize_strips_engine_ids():
    assert "cs:" not in sanitize_merchant_story_text_v1("cs:abc-123 يغادر العملاء")
    assert "DEMO-" not in sanitize_merchant_story_text_v1("DEMO-CHARGER غادر")
    assert "diagnostic:" not in sanitize_merchant_story_text_v1(
        "diagnostic:shipping يغادر"
    )


def test_external_platform_has_action():
    ship = {
        "diagnosis_status": "supported",
        "business_domain": "shipping",
        "observation_ar": "مغادرة عند الشحن.",
        "has_decision": True,
        "subject_ar": "Nano 20W",
    }
    assert execution_domain_v1(ship) == EXEC_DOMAIN_PLATFORM
    assert execution_readiness_v1(ship) == EXTERNAL_DEPENDENCY
    assert action_is_ready_v1(EXTERNAL_DEPENDENCY) is True
    assert "عدّل تكلفة الشحن" in decision_sentence_ar_v1(ship)
    href, label = destination_for_commitment_v1(ship)
    assert href.startswith("#settings")
    assert "شحن" in label or "زد" in label


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


def test_evidence_has_products_and_confidence():
    lines = evidence_lines_ar_v1(
        {
            "observation_ar": "يغادر العملاء بعد خطوة الشحن.",
            "business_domain": "shipping",
            "subject_ar": "Nano 20W",
            "product_name_ar": "TrueSound",
            "leave_rate_pct": 41,
            "confidence_level": "high",
            "diagnosis_status": "supported",
        }
    )
    assert any("41%" in x for x in lines)
    assert any("Nano" in x or "TrueSound" in x for x in lines)
    assert any("مرتفع" in x for x in lines)


def test_rejects_demo_slug_and_diagnostic_jargon():
    lines = evidence_lines_ar_v1(
        {
            "observation_ar": "يغادر العملاء بعد خطوة الشحن.",
            "subject_ar": "demo",
            "business_domain": "shipping",
            "confidence_level": "low",
        }
    )
    assert not any("demo" in x.casefold() for x in lines)
    text = decision_sentence_ar_v1(
        {
            "diagnosis_status": "supported",
            "first_step_ar": "قرّر الموقف التجاري بخصوص TrueSound بناءً على التشخيص.",
            "subject_ar": "TrueSound",
            "business_domain": "products",
            "observation_ar": "اهتمام مرتفع دون شراء.",
            "execution_readiness": READY,
        }
    )
    assert "التشخيص" not in text
    assert "الموقف التجاري" not in text
