# -*- coding: utf-8 -*-
"""Executive Editorial Brief Composition V1 — Principle 7 publication policy."""
from __future__ import annotations

import unittest

from services.home_executive_summary_v1.compose_v1 import build_home_executive_summary_v1
from services.home_executive_summary_v1.editorial_exclusivity_v1 import (
    SIT_PURCHASE_COMPLETION,
    SIT_RECOVERY,
    apply_editorial_exclusivity_v1,
    classify_commercial_situation_v1,
)


class ClassifyTests(unittest.TestCase):
    def test_carts_locked_to_ops(self) -> None:
        self.assertEqual(
            classify_commercial_situation_v1(
                "carts", "سلال العملاء تحتاج متابعة نشطة."
            ),
            "cart_operations",
        )

    def test_purchase_completion_family(self) -> None:
        self.assertEqual(
            classify_commercial_situation_v1(
                "decisions", "راجع تجربة إتمام الشراء ومتابعة العملاء."
            ),
            SIT_PURCHASE_COMPLETION,
        )
        self.assertEqual(
            classify_commercial_situation_v1(
                "observations",
                "تحويل Raven — حزام جلد للساعة ضعيف رغم اهتمام واضح.",
                product_name_ar="Raven — حزام جلد للساعة",
            ),
            SIT_PURCHASE_COMPLETION,
        )


class ExclusivityTests(unittest.TestCase):
    def test_product_observation_beats_generic_decision(self) -> None:
        sections = apply_editorial_exclusivity_v1(
            [
                {
                    "id": "health",
                    "title_ar": "حالة المتجر",
                    "summary_ar": "فرص استعادة المبيعات محدودة اليوم.",
                    "empty": False,
                },
                {
                    "id": "decisions",
                    "title_ar": "قرارات اليوم",
                    "summary_ar": "راجع تجربة إتمام الشراء ومتابعة العملاء.",
                    "empty": False,
                    "count": 2,
                },
                {
                    "id": "observations",
                    "title_ar": "ملاحظات المنتجات",
                    "summary_ar": (
                        "تحويل Raven — حزام جلد للساعة ضعيف رغم اهتمام واضح "
                        "— هذه أولوية تجارية اليوم."
                    ),
                    "empty": False,
                    "count": 1,
                },
                {
                    "id": "carts",
                    "title_ar": "السلال",
                    "summary_ar": "سلال العملاء تحتاج متابعة نشطة.",
                    "empty": False,
                    "count": 0,
                },
                {
                    "id": "communication",
                    "title_ar": "التواصل",
                    "summary_ar": "تواصل العملاء يسير بشكل طبيعي.",
                    "empty": True,
                    "count": 0,
                },
            ]
        )
        by = {s["id"]: s for s in sections}
        self.assertEqual(by["health"]["editorial_exclusivity"], "published")
        self.assertEqual(by["health"]["commercial_situation"], SIT_RECOVERY)
        self.assertEqual(by["observations"]["editorial_exclusivity"], "published")
        self.assertEqual(
            by["observations"]["commercial_situation"], SIT_PURCHASE_COMPLETION
        )
        self.assertEqual(
            by["decisions"]["editorial_exclusivity"], "suppressed_duplicate_situation"
        )
        self.assertTrue(by["decisions"].get("empty"))
        self.assertNotEqual(
            by["health"]["summary_ar"], by["observations"]["summary_ar"]
        )
        published = [
            s["summary_ar"]
            for s in sections
            if s.get("editorial_exclusivity") == "published"
        ]
        # No two published cards share purchase_completion wording path.
        self.assertEqual(len(published), len(set(published)))


class HomeBriefTests(unittest.TestCase):
    def test_living_store_shaped_home_not_repetitive(self) -> None:
        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "health": {
                        "domain_summary_ar": "فرص استعادة المبيعات محدودة اليوم.",
                        "needs_attention": True,
                    },
                    "decisions": {
                        "count": 2,
                        "top_title_ar": "راجع تجربة إتمام الشراء ومتابعة العملاء.",
                    },
                    "observations": {
                        "count": 4,
                        "top": {
                            "product_name_ar": "Raven — حزام جلد للساعة",
                            "statement_ar": (
                                "Raven — حزام جلد للساعة يحظى باهتمام واضح، "
                                "لكن التحويل إلى شراء لا يزال ضعيفاً."
                            ),
                            "source": "business_facts_v1",
                        },
                        "evidence": "business_facts",
                    },
                    "carts": {
                        "waiting": 0,
                        "domain_summary_ar": "سلال العملاء تحتاج متابعة نشطة.",
                    },
                    "communication": {
                        "domain_summary_ar": "تواصل العملاء يسير بشكل طبيعي."
                    },
                }
            }
        )
        self.assertTrue((hes.get("governance") or {}).get("executive_editorial_exclusivity"))
        audit = hes.get("editorial_brief") or {}
        self.assertFalse(audit.get("duplicate_situations"))
        by = {s["id"]: s for s in hes["sections"]}
        self.assertEqual(by["observations"]["title_ar"], "ملاحظات المنتجات")
        # Same commercial situation must not appear on decisions + observations.
        if by["observations"].get("editorial_exclusivity") == "published":
            self.assertNotEqual(
                by["decisions"].get("editorial_exclusivity"), "published"
            )
        published_sits = [
            s.get("commercial_situation")
            for s in hes["sections"]
            if s.get("editorial_exclusivity") == "published"
            and s.get("commercial_situation")
        ]
        self.assertEqual(len(published_sits), len(set(published_sits)))


if __name__ == "__main__":
    unittest.main()
