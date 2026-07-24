# -*- coding: utf-8 -*-
"""Finding Decision Engine V1 — findings → decisions (no new findings)."""
from __future__ import annotations

from services.finding_decision_engine_v1 import (
    decide_from_finding_v1,
    finding_decision_engine_v1_enabled,
)
from services.merchant_experience_business_findings_binding_v1 import (
    project_finding_render_contract_v1,
)


def test_flag_default_on() -> None:
    assert finding_decision_engine_v1_enabled(environ={}) is True
    assert finding_decision_engine_v1_enabled(environ={"CARTFLOW_FINDING_DECISION_ENGINE_V1": "0"}) is False


def test_widget_contact_gap_is_decision() -> None:
    d = decide_from_finding_v1(
        {
            "finding_id": "finding:recovery_channel_effectiveness_v1:widget",
            "finding_type": "recovery_channel_effectiveness_v1",
            "confidence": "medium",
            "evidence_summary": "reasons=18 contacts=0",
        }
    )
    assert d["has_decision"] is True
    assert d["status"] == "DECISION"
    assert "تواصل" in d["decision"] or "التواصل" in d["required_merchant_action"]
    assert d["evidence_summary"] == "reasons=18 contacts=0"
    assert d["review_window"]
    assert d["success_metric"]


def test_whatsapp_no_return_is_decision_not_scale() -> None:
    d = decide_from_finding_v1(
        {
            "finding_id": "finding:recovery_channel_effectiveness_v1:whatsapp",
            "finding_type": "recovery_channel_effectiveness_v1",
            "confidence": "medium",
            "evidence_summary": "sent=13 returned=0 purchased=0 failed=0 suppressed=0",
        }
    )
    assert d["has_decision"] is True
    assert "لا توسّع" in d["decision"] or "واتساب" in d["decision"]


def test_insufficient_is_no_decision() -> None:
    d = decide_from_finding_v1(
        {
            "finding_id": "finding:traffic_versus_conversion_v1",
            "finding_type": "traffic_versus_conversion_v1",
            "confidence": "insufficient",
            "evidence_summary": "visitor_total=unavailable; carts_not_used_as_traffic_proxy",
        }
    )
    assert d["has_decision"] is False
    assert d["status"] == "NO_DECISION"
    assert d["missing_evidence"]


def test_not_dominant_hesitation_no_decision() -> None:
    d = decide_from_finding_v1(
        {
            "finding_id": "finding:dominant_hesitation_reason_v1:not_dominant",
            "finding_type": "dominant_hesitation_reason_v1",
            "confidence": "low",
            "evidence_summary": "top=delivery:4/18 share=22%",
        }
    )
    assert d["status"] == "NO_DECISION"


def test_mebf_contract_attaches_decision() -> None:
    c = project_finding_render_contract_v1(
        {
            "finding_id": "finding:recovery_channel_effectiveness_v1:widget",
            "finding_type": "recovery_channel_effectiveness_v1",
            "title": "تواصل ضعيف",
            "confidence": "medium",
            "evidence_summary": "reasons=18 contacts=0",
            "home_eligible": True,
        }
    )
    assert c is not None
    assert c["merchant_decision_v1"]["has_decision"] is True


def test_engine_does_not_create_findings() -> None:
    src = open("services/finding_decision_engine_v1.py", encoding="utf-8").read()
    assert "run_business_findings_engine_v1" not in src
    assert "materialize_business_findings" not in src
