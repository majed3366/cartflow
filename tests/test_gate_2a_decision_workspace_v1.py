# -*- coding: utf-8 -*-
"""Gate 2A — Decision Workspace Completion."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class Gate2AOperationalTruthTests(unittest.TestCase):
    def test_no_phone_card_constitution_fields(self) -> None:
        from services.cart_workspace.operational_truth_decision_cards_v1 import (
            card_no_phone_v1,
        )

        card = card_no_phone_v1(count=43)
        assert card is not None
        self.assertEqual(card["card_kind"], "operational_truth")
        self.assertTrue(card["constitution_v1"])
        self.assertIn("بلا رقم", card["decision_ar"])
        self.assertIn("43", card["why_ar"])
        self.assertIn("43", card["evidence_summary"])
        self.assertEqual(card["decision_confidence_ar"], "مرتفع")
        self.assertTrue(card["view_details_href"].startswith("#carts"))
        self.assertIsNone(card_no_phone_v1(count=0))

    def test_waiting_card(self) -> None:
        from services.cart_workspace.operational_truth_decision_cards_v1 import (
            card_waiting_customers_v1,
        )

        card = card_waiting_customers_v1(count=12)
        assert card is not None
        self.assertIn("المنتظرين", card["decision_ar"])
        self.assertEqual(card["view_details_href"], "#carts")

    def test_list_skips_when_fde_covers_no_phone(self) -> None:
        from services.cart_workspace.operational_truth_decision_cards_v1 import (
            list_operational_truth_decision_cards_v1,
        )

        with patch(
            "services.cart_workspace.operational_truth_decision_cards_v1._load_store_counts",
            return_value={"no_phone_total": 5, "waiting_total": 5},
        ):
            cards = list_operational_truth_decision_cards_v1(
                "s",
                existing_cards=[
                    {
                        "finding_type": "missing_contact_blocks",
                        "decision_id": "fde:x",
                    }
                ],
            )
        ids = [c["decision_id"] for c in cards]
        self.assertNotIn("ops-truth:no_phone", ids)


class Gate2AEnrichmentTests(unittest.TestCase):
    def test_enrich_marks_gate_2a_and_hides_status_zones(self) -> None:
        from services.cart_workspace.business_findings_enrichment_v1 import (
            enrich_projection_with_fde_v1,
        )

        with patch(
            "services.cart_workspace.business_findings_enrichment_v1.list_fde_workspace_cards_v1",
            return_value=[],
        ), patch(
            "services.cart_workspace.operational_truth_decision_cards_v1.list_operational_truth_decision_cards_v1",
            return_value=[
                {
                    "decision_id": "ops-truth:no_phone",
                    "card_kind": "operational_truth",
                    "title_ar": "راجع سلال بلا رقم تواصل",
                    "decision_ar": "راجع سلال بلا رقم تواصل",
                    "why_ar": "3 سلال",
                    "evidence_summary": "3",
                    "decision_confidence": "high",
                    "has_decision": True,
                    "required_merchant_action": "راجع",
                    "view_details_href": "#carts?tab=nophone",
                }
            ],
        ):
            out = enrich_projection_with_fde_v1(
                {"zone_a": [], "zone_b": [], "zone_labels": {}}, "store"
            )
        self.assertTrue(out.get("gate_2a_decision_workspace_completion"))
        self.assertTrue(out.get("decisions_only"))
        self.assertFalse((out.get("zone_c") or {}).get("visible"))
        self.assertEqual(out.get("mission_question"), "ماذا يجب أن أقرر الآن، ولماذا؟")
        self.assertEqual(len(out.get("zone_b") or []), 1)
        self.assertTrue((out["zone_b"][0]).get("constitution_v1"))


class Gate2AUiContractTests(unittest.TestCase):
    def test_grid_has_no_status_chrome(self) -> None:
        grid = (ROOT / "static" / "cart_workspace_grid_v1.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("CartFlow يعمل", grid)
        self.assertNotIn("النتائج", grid)
        self.assertNotIn("آخر الإنجازات", grid)
        self.assertIn("mission_question", grid)
        self.assertIn("decisions-only", grid)

    def test_card_has_constitution_fields(self) -> None:
        card = (ROOT / "static" / "cart_workspace_decision_card_v1.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("القرار", card)
        self.assertIn("لماذا", card)
        self.assertIn("الأدلة", card)
        self.assertIn("الثقة", card)
        self.assertIn("الإجراء الموصى به", card)
        self.assertIn("لا توجد أدلة كافية لإصدار قرار.", card)


if __name__ == "__main__":
    unittest.main()
