# -*- coding: utf-8 -*-
"""Executive Control & Merchant Surface Parity V1 — projection-level tests."""
from __future__ import annotations

import unittest

from services.decision_composition_engine_v1.merchant_publication_v1 import (
    STATUS_STABLE_WITH_OPPORTUNITY_AR,
    apply_publication_priority_to_decisions_v1,
    compose_merchant_publication_v1,
    semantic_parity_fingerprint_v1,
)
from services.home_executive_summary_v1.compose_v1 import build_home_executive_summary_v1
from services.home_executive_summary_v1.slim_transport_v1 import (
    strip_heavy_home_summary_payload_v1,
)


def _living_store_fixture() -> dict:
    return {
        "ok": True,
        "composition_version": "t",
        "portfolio": [
            {
                "decision_id": "d-rec",
                "merchant_decision": "راجع تجربة إتمام الشراء ومتابعة العملاء.",
                "priority_band": "needs_action_now",
                "business_domain": "recovery",
                "priority": 80,
            },
            {
                "decision_id": "d-ops",
                "merchant_decision": "راجع تجربة إتمام الشراء ومتابعة العملاء.",
                "priority_band": "needs_action_now",
                "business_domain": "operations",
                "priority": 75,
            },
        ],
        "business_domains_v1": {
            "signals": {
                "available": True,
                "no_phone_total": 2,
                "waiting_total": 30,
                "active_total": 40,
            },
        },
        "suppression_registry": [],
    }


def _situations_pkg() -> dict:
    return {
        "ok": True,
        "published_situations": [
            {
                "situation_id": "cs:interest_without_purchase|p:raven",
                "situation_kind": "interest_without_purchase",
                "title_ar": "اهتمام دون شراء",
                "executive_summary_ar": "اهتمام واضح دون إتمام.",
                "why_it_matters_ar": "اهتمام واضح دون إتمام.",
                "priority": 78,
                "admitted": True,
                "subject": {"name_ar": "Raven — ساعة ذكية"},
            },
            {
                "situation_id": "cs:shipping_friction|p:truesound",
                "situation_kind": "shipping_friction",
                "title_ar": "احتكاك الشحن",
                "executive_summary_ar": "الشحن يضعف الإتمام.",
                "priority": 72,
                "admitted": True,
                "subject": {"name_ar": "TrueSound — سماعة"},
            },
            {
                "situation_id": "cs:recovery_opportunity|store",
                "situation_kind": "recovery_opportunity",
                "title_ar": "فرصة استعادة",
                "executive_summary_ar": "سلال مؤهلة للاستعادة.",
                "priority": 55,
                "admitted": True,
            },
        ],
    }


class ExecutiveControlContractTests(unittest.TestCase):
    def test_exactly_one_primary_product_action(self) -> None:
        pub = compose_merchant_publication_v1(
            _living_store_fixture(),
            situations_pkg=_situations_pkg(),
            identity_pkg={"simulation_run_id": "srs_parity"},
        )
        self.assertTrue(pub["ok"])
        self.assertTrue(pub["gate_executive_control_v1"])
        self.assertEqual(
            pub["store_condition"]["status_ar"],
            STATUS_STABLE_WITH_OPPORTUNITY_AR,
        )
        self.assertIn("فرصتان", pub["store_condition"]["summary_ar"])
        self.assertNotIn(
            "لا توجد مشكلات تجارية حرجة",
            pub["store_condition"]["summary_ar"],
        )
        self.assertEqual(pub["primary_situation_id"], "cs:interest_without_purchase|p:raven")
        self.assertIn("Raven", pub["primary_subject"])
        self.assertIn("مسار شراء Raven", pub["primary_action"])
        self.assertNotIn("إتمام الشراء ومتابعة", pub["primary_action"])
        ped = pub["primary_executive_decision"]
        self.assertTrue(ped and ped.get("is_primary"))
        self.assertEqual(ped["action_ar"], pub["primary_action"])
        # Secondaries are distinct and do not repeat primary action.
        secondary = pub["supporting_secondary_situations"]
        self.assertGreaterEqual(len(secondary), 2)
        for s in secondary:
            self.assertNotEqual(s.get("situation_id"), pub["primary_situation_id"])
            self.assertNotEqual(s.get("action_ar"), pub["primary_action"])
        self.assertEqual(pub["simulation_run_id"], "srs_parity")
        self.assertTrue(pub["truth_version"])

    def test_workspace_marks_single_primary(self) -> None:
        pub = compose_merchant_publication_v1(
            _living_store_fixture(),
            situations_pkg=_situations_pkg(),
        )
        decisions = apply_publication_priority_to_decisions_v1(
            [
                {
                    "decision_id": "dce:cs:cs:interest_without_purchase|p:raven",
                    "situation_id": "cs:interest_without_purchase|p:raven",
                    "merchant_decision": "generic",
                    "priority": 78,
                },
                {
                    "decision_id": "d-rec",
                    "situation_id": "cs:recovery_opportunity|store",
                    "merchant_decision": "راجع تجربة إتمام الشراء ومتابعة العملاء.",
                    "priority": 80,
                },
            ],
            pub,
        )
        primaries = [d for d in decisions if d.get("is_primary_decision")]
        self.assertEqual(len(primaries), 1)
        self.assertEqual(primaries[0]["situation_id"], pub["primary_situation_id"])
        self.assertEqual(primaries[0]["merchant_decision"], pub["primary_action"])


class SemanticParityTests(unittest.TestCase):
    def test_fingerprint_stable_across_transport(self) -> None:
        pub = compose_merchant_publication_v1(
            _living_store_fixture(),
            situations_pkg=_situations_pkg(),
            identity_pkg={"simulation_run_id": "srs_parity"},
        )
        summary = {
            "store_slug": "demo",
            "merchant_publication_v1": pub,
            "home_teaser_inputs_v1": {
                "schema": "home_teaser_inputs_v1",
                "health": {
                    "needs_attention": True,
                    "abandoned_carts": 30,
                    "no_phone": 2,
                    "store_connected": True,
                },
                "decisions": {
                    "count": 1,
                    "top_title_ar": pub["primary_action"],
                    "evidence": "merchant_publication_v1",
                },
                "observations": {"count": 1, "top": None},
                "carts": {"waiting": 30, "active": 40, "no_phone": 2},
                "communication": {
                    "sent": 0,
                    "no_phone": 2,
                    "waiting": 30,
                    "constrained": True,
                },
            },
        }
        fp_a = semantic_parity_fingerprint_v1(pub)
        # Desktop/Mobile must consume the same stripped publication envelope.
        strip_heavy_home_summary_payload_v1(summary)
        fp_b = semantic_parity_fingerprint_v1(summary["merchant_publication_v1"])
        self.assertEqual(fp_a["store_condition_summary_ar"], fp_b["store_condition_summary_ar"])
        self.assertEqual(fp_a["primary_action"], fp_b["primary_action"])
        self.assertEqual(fp_a["primary_subject"], fp_b["primary_subject"])
        self.assertEqual(fp_a["primary_situation_id"], fp_b["primary_situation_id"])
        self.assertEqual(fp_a["communication_summary_ar"], fp_b["communication_summary_ar"])
        self.assertEqual(fp_a["cart_summary_ar"], fp_b["cart_summary_ar"])
        self.assertEqual(fp_a["secondary_titles_ar"], fp_b["secondary_titles_ar"])
        self.assertEqual(fp_a["simulation_run_id"], fp_b["simulation_run_id"])

        hes = build_home_executive_summary_v1(summary)
        by_id = {s.get("id"): s for s in list(hes.get("sections") or []) if isinstance(s, dict)}
        self.assertIn("فرصتان", (by_id.get("health") or {}).get("summary_ar") or "")
        self.assertEqual(
            (by_id.get("decisions") or {}).get("summary_ar"),
            pub["primary_action"],
        )
        self.assertTrue((by_id.get("decisions") or {}).get("dominant"))
        sits = by_id.get("situations") or {}
        if sits.get("items"):
            item = sits["items"][0]
            self.assertNotIn("situation_id", item)
            self.assertIn("Raven", item.get("title_ar") or item.get("product_name_ar") or "")


class TechnicalCopyBanTests(unittest.TestCase):
    def test_home_sections_have_no_technical_tokens(self) -> None:
        pub = compose_merchant_publication_v1(
            _living_store_fixture(),
            situations_pkg=_situations_pkg(),
            identity_pkg={"simulation_run_id": "srs_parity"},
        )
        summary = {
            "store_slug": "demo",
            "merchant_publication_v1": pub,
            "home_teaser_inputs_v1": {
                "schema": "home_teaser_inputs_v1",
                "health": {
                    "needs_attention": True,
                    "abandoned_carts": 30,
                    "no_phone": 2,
                    "store_connected": True,
                    "domain_summary_ar": pub["store_condition"]["summary_ar"],
                },
                "decisions": {
                    "count": 1,
                    "top_title_ar": pub["primary_action"],
                },
                "observations": {"count": 0, "top": None},
                "carts": {
                    "waiting": 30,
                    "active": 40,
                    "no_phone": 2,
                    "domain_summary_ar": pub["cart_condition"]["summary_ar"],
                },
                "communication": {
                    "sent": 0,
                    "no_phone": 2,
                    "waiting": 30,
                    "domain_summary_ar": pub["communication_condition"]["summary_ar"],
                    "constrained": True,
                },
            },
        }
        hes = build_home_executive_summary_v1(summary)
        # Merchant-visible fields only (not internal classification metadata).
        visible = []
        for sec in list(hes.get("sections") or []):
            if not isinstance(sec, dict):
                continue
            visible.extend(
                [
                    str(sec.get("title_ar") or ""),
                    str(sec.get("summary_ar") or ""),
                    str(sec.get("status_ar") or ""),
                    str(sec.get("cart_level_action_ar") or ""),
                    str(sec.get("systemic_business_action_ar") or ""),
                ]
            )
            for it in list(sec.get("items") or []):
                if isinstance(it, dict):
                    visible.extend(
                        [
                            str(it.get("title_ar") or ""),
                            str(it.get("statement_ar") or ""),
                            str(it.get("product_name_ar") or ""),
                        ]
                    )
        blob = "\n".join(visible)
        for banned in (
            "CONSISTENT",
            "CEO_REVIEW_SAFE",
            "store_slug",
            "simulation_run_id",
            "truth_version",
            "cs:",
            "situation_id",
            "merchant_id",
            "operations",
        ):
            self.assertNotIn(banned, blob)


if __name__ == "__main__":
    unittest.main()
