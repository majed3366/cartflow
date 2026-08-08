# -*- coding: utf-8 -*-
"""Gate 2B — Decision Composition Engine V1."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_generic_product_banned(self) -> None:
        from services.decision_composition_engine_v1.contract_v1 import (
            contains_generic_product_language,
            validate_publish_contract,
            new_candidate,
        )

        self.assertTrue(contains_generic_product_language("راجع هذا المنتج"))
        cand = new_candidate(
            decision_id="x",
            store_slug="s",
            decision_type="verified_existing_finding",
            decision_subject_type="product",
            decision_subject_id="",
            title="هذا المنتج",
            merchant_decision="هذا المنتج",
            why="x",
            why_now="x",
            evidence_summary="x",
            ignore_consequence="x",
            recommended_action="x",
            first_step="x",
            expected_outcome="x",
            confidence="high",
            priority=10,
            source_truth_types=["t"],
        )
        ok, reason = validate_publish_contract(cand)
        self.assertFalse(ok)
        self.assertEqual(reason, "subject_unidentified")


class RecoverabilityTests(unittest.TestCase):
    def test_43_no_phone_composes_business_meaning(self) -> None:
        from services.decision_composition_engine_v1.compose_recoverability_v1 import (
            compose_recoverability_gap_v1,
        )

        cand = compose_recoverability_gap_v1(
            {
                "store_slug": "demo",
                "available": True,
                "no_phone_total": 43,
                "waiting_total": 43,
                "engaged_total": 0,
            }
        )
        assert cand is not None
        self.assertFalse(cand.get("suppressed"))
        # Gate 2F — merchant briefing language (never "N carts without phone").
        self.assertIn("إتمام الشراء", cand["merchant_decision"])
        self.assertNotIn("راجع سلال بلا رقم", cand["merchant_decision"])
        self.assertNotIn("43", cand["merchant_decision"])
        self.assertIn("فرص", cand["why"])
        self.assertNotIn("عدّاد", cand["evidence_summary"])
        self.assertTrue(cand["why_now"])
        self.assertTrue(cand["ignore_consequence"])
        self.assertTrue(cand["first_step"])
        self.assertEqual(cand["confidence"], "high")
        self.assertGreaterEqual(cand["priority"], 55)

    def test_zero_no_phone_suppressed_normal(self) -> None:
        from services.decision_composition_engine_v1.compose_recoverability_v1 import (
            compose_recoverability_gap_v1,
        )

        cand = compose_recoverability_gap_v1(
            {"store_slug": "s", "available": True, "no_phone_total": 0}
        )
        assert cand is not None
        self.assertTrue(cand["suppressed"])
        self.assertEqual(cand["suppression_reason"], "normal_state_no_merchant_action")


class WaitingTests(unittest.TestCase):
    def test_automation_wait_suppressed(self) -> None:
        from services.decision_composition_engine_v1.compose_waiting_v1 import (
            compose_waiting_recovery_v1,
        )

        cand = compose_waiting_recovery_v1(
            {
                "store_slug": "s",
                "available": True,
                "waiting_total": 3,
                "no_phone_total": 3,
                "engaged_total": 0,
            }
        )
        assert cand is not None
        self.assertTrue(cand["suppressed"])
        self.assertEqual(cand["suppression_reason"], "normal_state_no_merchant_action")

    def test_engaged_requires_merchant(self) -> None:
        from services.decision_composition_engine_v1.compose_waiting_v1 import (
            compose_waiting_recovery_v1,
        )

        cand = compose_waiting_recovery_v1(
            {
                "store_slug": "s",
                "available": True,
                "waiting_total": 8,
                "no_phone_total": 0,
                "engaged_total": 2,
            }
        )
        assert cand is not None
        self.assertFalse(cand.get("suppressed"))
        self.assertIn("تدخل", cand["merchant_decision"] + cand["why"])


class FindingTests(unittest.TestCase):
    def test_product_unidentified_suppressed(self) -> None:
        from services.decision_composition_engine_v1.compose_finding_v1 import (
            compose_from_finding_contract_v1,
        )

        cand = compose_from_finding_contract_v1(
            {
                "finding_id": "f1",
                "finding_type": "high_interest_low_purchase_product_v1",
                "title": "هذا المنتج",
                "merchant_decision_v1": {
                    "has_decision": True,
                    "status": "DECISION",
                    "decision": "راجع هذا المنتج",
                    "why": "اهتمام مرتفع",
                    "evidence_summary": "n=10",
                    "required_merchant_action": "حسّن الصفحة",
                    "expected_business_impact": "رفع التحويل",
                    "decision_confidence": "high",
                },
            },
            store_slug="s",
        )
        assert cand is not None
        self.assertTrue(cand["suppressed"])
        self.assertEqual(cand["suppression_reason"], "subject_unidentified")

    def test_named_product_publishes(self) -> None:
        from services.decision_composition_engine_v1.compose_finding_v1 import (
            compose_from_finding_contract_v1,
        )
        from services.decision_composition_engine_v1.suppress_v1 import apply_contract_gate

        cand = compose_from_finding_contract_v1(
            {
                "finding_id": "f2",
                "finding_type": "high_interest_low_purchase_product_v1",
                "product_id": "sku-9",
                "product_name_ar": "عطر الورد",
                "title": "اهتمام مرتفع",
                "merchant_decision_v1": {
                    "has_decision": True,
                    "status": "DECISION",
                    "decision": "راجع صفحة عطر الورد",
                    "why": "اهتمام مرتفع وتحويل منخفض",
                    "evidence_summary": "views=40 purchases=1",
                    "required_merchant_action": "حسّن صفحة المنتج",
                    "expected_business_impact": "رفع التحويل",
                    "decision_confidence": "high",
                },
            },
            store_slug="s",
        )
        assert cand is not None
        self.assertFalse(cand.get("suppressed"))
        gated = apply_contract_gate(cand)
        self.assertTrue(gated["published"])
        self.assertNotIn("هذا المنتج", gated["merchant_decision"])

    def test_insufficient_fde_suppressed_with_reason(self) -> None:
        from services.decision_composition_engine_v1.compose_finding_v1 import (
            compose_from_finding_contract_v1,
        )

        cand = compose_from_finding_contract_v1(
            {
                "finding_id": "f3",
                "finding_type": "dominant_hesitation_reason_v1",
                "merchant_decision_v1": {
                    "has_decision": False,
                    "status": "NO_DECISION",
                    "missing_evidence": "n<3",
                },
            },
            store_slug="s",
        )
        assert cand is not None
        self.assertTrue(cand["suppressed"])
        self.assertTrue(cand["suppression_reason"])


class PipelineTests(unittest.TestCase):
    def test_compose_pipeline_priority_and_registry(self) -> None:
        from services.decision_composition_engine_v1.compose_v1 import compose_decisions_v1

        with patch(
            "services.decision_composition_engine_v1.compose_v1.load_store_counter_inputs_v1",
            return_value={
                "store_slug": "s",
                "available": True,
                "no_phone_total": 43,
                "waiting_total": 50,
                "engaged_total": 2,
                "active_total": 60,
            },
        ), patch(
            "services.decision_composition_engine_v1.compose_v1.load_bound_finding_inputs_v1",
            return_value=[],
        ):
            pkg = compose_decisions_v1("s")
        self.assertTrue(pkg["ok"])
        self.assertGreaterEqual(pkg["counts"]["published"], 1)
        ids = [d["decision_id"] for d in pkg["decisions"]]
        self.assertIn("dce:recoverability_gap", ids)
        # Highest priority first
        pris = [d["priority"] for d in pkg["decisions"]]
        self.assertEqual(pris, sorted(pris, reverse=True))
        # No silent suppression — registry records normals etc.
        self.assertIsInstance(pkg["suppression_registry"], list)

    def test_no_valid_decisions(self) -> None:
        from services.decision_composition_engine_v1.compose_v1 import compose_decisions_v1

        with patch(
            "services.decision_composition_engine_v1.compose_v1.load_store_counter_inputs_v1",
            return_value={
                "store_slug": "s",
                "available": True,
                "no_phone_total": 0,
                "waiting_total": 0,
                "engaged_total": 0,
            },
        ), patch(
            "services.decision_composition_engine_v1.compose_v1.load_bound_finding_inputs_v1",
            return_value=[],
        ):
            pkg = compose_decisions_v1("s")
        self.assertTrue(pkg["no_decision_supported"])
        self.assertEqual(pkg["counts"]["published"], 0)
        # Gate 2D: healthy domains produce no candidates (no fake suppressed decisions).
        self.assertEqual(pkg["counts"]["candidates_total"], 0)
        self.assertTrue(pkg.get("gate_2d_business_domains"))
        healthy = [
            x
            for x in (pkg.get("category_landscape") or [])
            if x.get("no_action_required")
        ]
        self.assertGreaterEqual(len(healthy), 1)

    def test_teaser_parity(self) -> None:
        from services.decision_composition_engine_v1.teaser_v1 import (
            count_composed_decisions_for_teaser_v1,
        )
        from services.decision_composition_engine_v1.compose_v1 import compose_decisions_v1

        with patch(
            "services.decision_composition_engine_v1.compose_v1.load_store_counter_inputs_v1",
            return_value={
                "store_slug": "s",
                "available": True,
                "no_phone_total": 10,
                "waiting_total": 10,
                "engaged_total": 0,
            },
        ), patch(
            "services.decision_composition_engine_v1.compose_v1.load_bound_finding_inputs_v1",
            return_value=[],
        ):
            pkg = compose_decisions_v1("s")
            teaser = count_composed_decisions_for_teaser_v1("s")
        self.assertEqual(teaser["count"], len(pkg["decisions"]))
        if pkg["decisions"]:
            self.assertEqual(
                teaser["top_title_ar"], pkg["decisions"][0]["merchant_decision"]
            )

    def test_enrich_uses_dce(self) -> None:
        from services.cart_workspace.business_findings_enrichment_v1 import (
            enrich_projection_with_fde_v1,
        )

        fake_pkg = {
            "ok": True,
            "composition_version": "decision_composition_engine_v1",
            "decisions": [
                {
                    "decision_id": "dce:recoverability_gap",
                    "merchant_decision": "راجع تجربة إتمام الشراء ومتابعة العملاء.",
                    "title": "x",
                    "why": "why",
                    "why_now": "now",
                    "evidence_summary": "ev",
                    "ignore_consequence": "ig",
                    "recommended_action": "act",
                    "first_step": "step",
                    "expected_outcome": "out",
                    "confidence": "high",
                    "priority": 80,
                    "priority_band": "needs_action_now",
                    "published": True,
                    "source_truth_types": ["merchant_store_cart_counts"],
                    "composition_version": "decision_composition_engine_v1",
                    "view_details_href": "#carts?tab=nophone",
                }
            ],
            "needs_action_now": [{}],
            "monitor": [],
            "suppression_registry": [],
            "counts": {
                "published": 1,
                "suppressed": 0,
                "needs_action_now": 1,
                "monitor": 0,
                "candidates_total": 2,
            },
            "no_decision_supported": False,
        }
        with patch(
            "services.decision_composition_engine_v1.flag_v1.decision_composition_engine_v1_enabled",
            return_value=True,
        ), patch(
            "services.decision_composition_engine_v1.compose_v1.compose_decisions_v1",
            return_value=fake_pkg,
        ):
            out = enrich_projection_with_fde_v1(
                {"zone_a": [], "zone_b": [], "zone_labels": {}}, "s"
            )
        self.assertTrue(out.get("gate_2b_decision_composition_engine"))
        self.assertEqual(len(out["zone_b"]), 1)
        self.assertEqual(out["zone_b"][0]["card_kind"], "composed_decision")
        self.assertIn("إتمام الشراء", out["zone_b"][0]["decision_ar"])


class UiParityTests(unittest.TestCase):
    def test_card_has_reasoning_face(self) -> None:
        js = (ROOT / "static" / "cart_workspace_decision_card_v1.js").read_text(
            encoding="utf-8"
        )
        for label in (
            "الملاحظة",
            "ما يعنيه ذلك",
            "القرار الآن",
            "خطوتك",
            "الأولوية",
            "cx-decision",
            "cx-beat--evidence",
        ):
            self.assertIn(label, js)

    def test_grid_primary_next(self) -> None:
        grid = (ROOT / "static" / "cart_workspace_grid_v1.js").read_text(
            encoding="utf-8"
        )
        card = (ROOT / "static" / "cart_workspace_decision_card_v1.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("cx-ws", grid)
        self.assertIn("cx-ws__primary", grid)
        self.assertIn("is_primary_decision", grid)
        self.assertIn("لا يوجد قرار يحتاج انتباهك الآن", card)


class PriorityTests(unittest.TestCase):
    def test_priority_not_raw_count(self) -> None:
        from services.decision_composition_engine_v1.priority_v1 import (
            calculate_priority_v1,
        )

        low = calculate_priority_v1(
            {
                "decision_type": "waiting_recovery_work",
                "confidence": "low",
                "first_step": "x",
                "why_now": "",
            },
            affected_count=100,
            automation_can_resolve=True,
        )
        high = calculate_priority_v1(
            {
                "decision_type": "recoverability_gap",
                "confidence": "high",
                "first_step": "x",
                "why_now": "الآن",
            },
            affected_count=5,
            automation_can_resolve=False,
        )
        # Recoverability with strong evidence can beat large automated wait.
        self.assertGreater(high[0], low[0])


if __name__ == "__main__":
    unittest.main()
