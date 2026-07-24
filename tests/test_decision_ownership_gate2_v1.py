# -*- coding: utf-8 -*-
"""Gate 2 — Single Decision Owner."""
from __future__ import annotations

import unittest

from services.cart_workspace.business_findings_enrichment_v1 import (
    decision_dual_stack_v1_enabled,
    enrich_projection_with_fde_v1,
    fde_card_from_contract_v1,
)
from services.cart_workspace.projection_v1 import MISSION_QUESTION_AR
from services.home_executive_summary_v1.compose_v1 import (
    DECISIONS_EMPTY_AR,
    DECISIONS_VIEW_DETAILS_AR,
    SECTION_OWNERSHIP_HREF_V1,
    build_home_executive_summary_v1,
)


class Gate2DecisionOwnershipTests(unittest.TestCase):
    def test_dual_stack_default_off(self) -> None:
        self.assertFalse(decision_dual_stack_v1_enabled(environ={}))
        self.assertTrue(
            decision_dual_stack_v1_enabled(
                environ={"CARTFLOW_DECISION_DUAL_STACK_V1": "1"}
            )
        )

    def test_mission_question_constitutional(self) -> None:
        self.assertIn("أقرر", MISSION_QUESTION_AR)

    def test_fde_card_decision(self) -> None:
        card = fde_card_from_contract_v1(
            {
                "finding_id": "f1",
                "finding_type": "dominant_hesitation_reason_v1",
                "title": "تردّد على الشحن",
                "explanation": "سبب التردد ظاهر",
                "evidence_summary": "evidence=4",
                "confidence": "high",
                "merchant_decision_v1": {
                    "has_decision": True,
                    "status": "DECISION",
                    "decision": "راجع تكلفة الشحن.",
                    "why": "السبب الأقوى للتردد هو الشحن.",
                    "expected_business_impact": "رفع التحويل",
                    "required_merchant_action": "راجع تكلفة الشحن.",
                    "decision_confidence": "high",
                    "evidence_summary": "evidence=4",
                },
            }
        )
        assert card is not None
        self.assertEqual(card["card_kind"], "business_finding")
        self.assertTrue(card["has_decision"])
        self.assertEqual(card["decision_id"], "fde:f1")
        self.assertIn("الشحن", card["title_ar"])
        self.assertFalse(card["commands_enabled"])

    def test_fde_card_no_decision(self) -> None:
        card = fde_card_from_contract_v1(
            {
                "finding_id": "f2",
                "title": "نمط غير كافٍ",
                "evidence_summary": "n=1",
                "confidence": "low",
                "merchant_decision_v1": {
                    "has_decision": False,
                    "status": "NO_DECISION",
                    "missing_evidence": "مطلوب أدلة أقوى",
                    "decision_confidence": "none",
                },
            }
        )
        assert card is not None
        self.assertFalse(card["has_decision"])
        self.assertEqual(card["decision_status"], "NO_DECISION")

    def test_enrich_prepends_business_cards(self) -> None:
        proj = {
            "store_slug": "s",
            "zone_a": [],
            "zone_b": [
                {
                    "decision_id": "ops-1",
                    "required_action": "take_over_conversation",
                    "decision_class": "judgment",
                }
            ],
            "quiet": False,
            "zone_labels": {},
        }
        # Monkey via direct card merge path: enrich with empty FDE still keeps ops
        out = enrich_projection_with_fde_v1(proj, "")
        self.assertEqual(out["mission_question"], "ماذا يجب أن أقرر الآن، ولماذا؟")
        self.assertTrue(out.get("gate_2_single_decision_owner"))
        ids = [c.get("decision_id") for c in out.get("zone_b") or []]
        self.assertIn("ops-1", ids)

    def test_home_decisions_route_workspace_only(self) -> None:
        hes = build_home_executive_summary_v1(
            {},
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        dec = next(s for s in hes["sections"] if s["id"] == "decisions")
        self.assertEqual(dec["view_details_href"], "#workspace")
        self.assertEqual(dec["view_details_ar"], DECISIONS_VIEW_DETAILS_AR)
        self.assertEqual(SECTION_OWNERSHIP_HREF_V1["decisions"], "#workspace")
        self.assertEqual(dec["summary_ar"], DECISIONS_EMPTY_AR)


if __name__ == "__main__":
    unittest.main()
