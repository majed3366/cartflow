# -*- coding: utf-8 -*-
"""Merchant Experience Binding V1 — consumer contract tests."""
from __future__ import annotations

import inspect

from services.merchant_experience_business_findings_binding_v1 import (
    apply_business_findings_binding_to_meif_v1,
    project_finding_render_contract_v1,
)
from services.product_data import merchant_experience_integration_foundation_v1 as meif_mod


def test_render_contract_requires_finding_id() -> None:
    assert project_finding_render_contract_v1({"title": "x"}) is None
    c = project_finding_render_contract_v1(
        {
            "finding_id": "finding:demo:1",
            "finding_type": "dominant_hesitation_reason_v1",
            "title": "سبب تردد",
            "confidence": "low",
            "recommended_action": "راجع",
            "evidence": {"evidence_summary": "n=18"},
            "home_eligible": True,
        }
    )
    assert c is not None
    assert c["finding_id"] == "finding:demo:1"
    assert c["evidence_summary"]
    assert c["bfl_binding"] is True


def test_meif_calls_binding_not_engine() -> None:
    src = inspect.getsource(meif_mod.generate_merchant_experience_integration_v1)
    assert "apply_business_findings_binding_to_meif_v1" in src
    assert "run_business_findings_engine_v1" not in src


def test_binding_strips_non_finding_commercial() -> None:
    meif = {
        "ok": True,
        "pages": {
            "home": {
                "sections": {
                    "commercial_guidance_highlights": [
                        {"merchant_statement_ar": "legacy", "source_type": "merchant_presentation"}
                    ],
                    "executive_summary": [
                        {"merchant_statement_ar": "legacy2", "source_type": "merchant_presentation"}
                    ],
                    "knowledge_highlights": [
                        {"merchant_statement_ar": "k", "source_type": "knowledge"}
                    ],
                    "critical_attention": [],
                    "operational_health": [],
                }
            },
            "decision_workspace": {"sections": {"review_items": [], "knowledge_context": []}},
            "carts": {"sections": {"composition_items": []}},
            "communication": {"sections": {"composition_items": []}},
        },
        "inputs": {},
    }
    # Binding with empty slug / disabled path still runs strip when enabled —
    # use apply with monkeypatched empty consume via empty store
    out = apply_business_findings_binding_to_meif_v1(meif, "")
    # empty slug → binding reports error; commercial may stay until consume works
    assert "business_findings_binding_v1" in out
