# -*- coding: utf-8 -*-
"""Merchant Understanding Repair V1 — cross-surface publication contract."""
from __future__ import annotations

import unittest

from services.decision_composition_engine_v1.dedupe_v1 import (
    SUPPRESS_DUPLICATE_ACTION,
    dedupe_published_by_action_v1,
)
from services.decision_composition_engine_v1.merchant_publication_v1 import (
    COMM_CONTACT_CONSTRAINT_AR,
    compose_merchant_publication_v1,
)
from services.decision_composition_engine_v1.store_executive_understanding_v1 import (
    _executive_decision_title_v1,
)
from services.home_executive_summary_v1.compose_v1 import build_home_executive_summary_v1


class DistinctDecisionTitlesTests(unittest.TestCase):
    def test_recovery_and_operations_titles_differ(self) -> None:
        recovery = _executive_decision_title_v1(
            {
                "business_domain": "recovery",
                "decision_type": "recoverability_gap",
                "root_cause_key": "recovery:missing_contact",
                "title": "مسار الاسترجاع فيه فرص",
            }
        )
        operations = _executive_decision_title_v1(
            {
                "business_domain": "operations",
                "decision_type": "waiting_recovery_work",
                "root_cause_key": "recovery:waiting_intervention",
                "title": "مسار الاسترجاع فيه حالات تحتاج تدخلاً",
            }
        )
        self.assertNotEqual(recovery, operations)
        self.assertIn("رقم العميل", recovery)
        self.assertIn("تدخلك", operations)


class ActionDedupeTests(unittest.TestCase):
    def test_identical_actions_collapse(self) -> None:
        survivors, registry = dedupe_published_by_action_v1(
            [
                {
                    "decision_id": "d1",
                    "merchant_decision": "راجع تجربة إتمام الشراء ومتابعة العملاء.",
                    "priority_band": "needs_action_now",
                    "priority": 90,
                },
                {
                    "decision_id": "d2",
                    "merchant_decision": "راجع تجربة إتمام الشراء ومتابعة العملاء.",
                    "priority_band": "needs_action_now",
                    "priority": 80,
                },
            ]
        )
        self.assertEqual(len(survivors), 1)
        self.assertEqual(survivors[0]["decision_id"], "d1")
        self.assertTrue(
            any(r.get("suppression_reason") == SUPPRESS_DUPLICATE_ACTION for r in registry)
        )


class PublicationContractTests(unittest.TestCase):
    def test_store_condition_not_calm_when_priority_exists(self) -> None:
        pub = compose_merchant_publication_v1(
            {
                "ok": True,
                "composition_version": "t",
                "portfolio": [
                    {
                        "decision_id": "d-rec",
                        "merchant_decision": "راجع آلية جمع رقم العميل قبل مغادرة المتجر.",
                        "priority_band": "needs_action_now",
                        "business_domain": "recovery",
                        "decision_type": "recoverability_gap",
                        "root_cause_key": "recovery:missing_contact",
                        "priority": 88,
                    }
                ],
                "business_domains_v1": {
                    "signals": {"available": True, "no_phone_total": 12, "waiting_total": 5},
                    "domains": {"recovery": {"has_attention": True}},
                },
                "store_executive_understanding_v1": {
                    "home_teasers": {
                        "store_health_ar": "لا توجد مشكلات تجارية حرجة ظاهرة.",
                        "communication_ar": "تواصل العملاء يسير بشكل طبيعي.",
                    }
                },
                "suppression_registry": [],
            },
            situations_pkg={
                "ok": True,
                "published_situations": [
                    {
                        "situation_id": "cs:interest_without_purchase|x:demo",
                        "situation_kind": "interest_without_purchase",
                        "title_ar": "اهتمام دون شراء",
                        "executive_summary_ar": "اهتمام دون شراء",
                        "priority": 70,
                        "admitted": True,
                        "subject": {"name_ar": "Raven"},
                    }
                ],
            },
            identity_pkg={"simulation_run_id": "srs_test_repair"},
        )
        self.assertTrue(pub["ok"])
        # Executive Control: product situation leads over generic recovery loop.
        self.assertEqual(
            pub["primary_situation_id"],
            "cs:interest_without_purchase|x:demo",
        )
        self.assertIn("مسار شراء Raven", pub["primary_action"])
        self.assertTrue(pub["store_condition"]["needs_attention"])
        self.assertNotEqual(
            pub["store_condition"]["summary_ar"],
            "لا توجد مشكلات تجارية حرجة ظاهرة.",
        )
        self.assertNotIn("هادئ", pub["store_condition"]["status_ar"])
        # High missing-contact volume → urgent / constrained communication.
        self.assertEqual(
            pub["communication_condition"]["summary_ar"],
            COMM_CONTACT_CONSTRAINT_AR,
        )
        self.assertTrue(pub["communication_condition"]["normal_forbidden"])
        self.assertEqual(pub["simulation_run_id"], "srs_test_repair")
        self.assertTrue(pub["truth_version"])
        self.assertEqual(
            pub["cart_condition"]["individual_action_ar"],
            "لا يحتاج إجراءً فردياً الآن.",
        )
        self.assertEqual(
            pub["cart_operational_action"]["individual_action_ar"],
            "لا يحتاج إجراءً فردياً الآن.",
        )
        self.assertTrue(pub["systemic_business_action"]["summary_ar"])
        self.assertTrue(pub.get("gate_executive_control_v1"))

    def test_home_consumes_publication_authority(self) -> None:
        summary = {
            "store_slug": "demo",
            "merchant_publication_v1": {
                "ok": True,
                "truth_version": "merchant_publication_v1:abc",
                "simulation_run_id": "srs_home",
                "store_condition": {
                    "status_ar": "يتطلب متابعة",
                    "summary_ar": "فرص استعادة المبيعات محدودة اليوم.",
                    "needs_attention": True,
                    "calm_forbidden": True,
                },
                "highest_priority_decision_id": "d1",
                "highest_priority_situation_id": "cs:x",
                "primary_business_action": "راجع آلية جمع رقم العميل قبل مغادرة المتجر.",
                "secondary_decision_ids": ["d2"],
                "communication_condition": {
                    "status_ar": "يتطلب متابعة",
                    "summary_ar": COMM_CONTACT_CONSTRAINT_AR,
                    "constrained": True,
                    "normal_forbidden": True,
                },
                "cart_operational_action": {
                    "summary_ar": "سلال العملاء تحتاج متابعة تشغيلية.",
                    "status_ar": "يتطلب متابعة",
                    "individual_action_ar": "لا يحتاج إجراءً فردياً الآن.",
                    "empty": False,
                },
                "systemic_business_action": {
                    "summary_ar": "راجع آلية جمع رقم العميل قبل مغادرة المتجر.",
                    "workspace_href": "#workspace",
                },
                "home_product_situation": {
                    "situation_id": "cs:interest|p:demo",
                    "situation_kind": "interest_without_purchase",
                    "title_ar": "اهتمام دون شراء — منتج",
                    "statement_ar": "اهتمام واضح دون شراء.",
                    "href": "#workspace?situation_id=cs:interest|p:demo",
                },
            },
            "home_teaser_inputs_v1": {
                "schema": "home_teaser_inputs_v1",
                "health": {
                    "needs_attention": True,
                    "domain_summary_ar": "فرص استعادة المبيعات محدودة اليوم.",
                    "abandoned_carts": 5,
                    "no_phone": 12,
                    "store_connected": True,
                },
                "decisions": {
                    "count": 1,
                    "top_title_ar": "راجع آلية جمع رقم العميل قبل مغادرة المتجر.",
                    "evidence": "merchant_publication_v1",
                },
                "observations": {"count": 0, "top": None},
                "carts": {"waiting": 5, "active": 10, "no_phone": 12},
                "communication": {
                    "sent": 0,
                    "no_phone": 12,
                    "waiting": 5,
                    "domain_summary_ar": COMM_CONTACT_CONSTRAINT_AR,
                    "constrained": True,
                },
            },
        }
        hes = build_home_executive_summary_v1(summary)
        self.assertTrue(hes.get("ok") is not False)
        by_id = {
            s.get("id"): s
            for s in list(hes.get("sections") or [])
            if isinstance(s, dict)
        }
        health = by_id.get("health") or {}
        self.assertTrue(health.get("needs_attention"))
        self.assertNotEqual(health.get("status_ar"), "هادئ")
        self.assertNotIn("لا توجد مشكلات تجارية حرجة", health.get("summary_ar") or "")
        dec = by_id.get("decisions") or {}
        self.assertEqual(dec.get("count"), 1)
        self.assertEqual(
            dec.get("summary_ar"),
            "راجع آلية جمع رقم العميل قبل مغادرة المتجر.",
        )
        comm = by_id.get("communication") or {}
        self.assertEqual(comm.get("summary_ar"), COMM_CONTACT_CONSTRAINT_AR)
        self.assertNotIn("بشكل طبيعي", comm.get("summary_ar") or "")
        carts = by_id.get("carts") or {}
        self.assertEqual(
            carts.get("cart_level_action_ar"),
            "لا يحتاج إجراءً فردياً الآن.",
        )
        self.assertTrue(carts.get("systemic_business_action_ar"))
        sits = by_id.get("situations") or {}
        if sits:
            self.assertEqual(sits.get("count"), 1)


if __name__ == "__main__":
    unittest.main()
