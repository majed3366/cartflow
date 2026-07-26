# -*- coding: utf-8 -*-
"""Gate 2X — Merchant Understanding V1."""
from __future__ import annotations

import unittest

from services.decision_composition_engine_v1.merchant_understanding_v1 import (
    PREFERRED_CARTS_NEED_ATTENTION_AR,
    PREFERRED_DECISION_CHECKOUT_AR,
    PREFERRED_DECISION_RECOVERY_CONTACT_AR,
    PREFERRED_HEALTH_LIMITED_AR,
    PREFERRED_NO_CRITICAL_AR,
    compose_merchant_understanding_v1,
    evaluate_merchant_understanding_v1,
    publish_executive_statement_v1,
    rewrite_for_merchant_understanding_v1,
    violates_merchant_understanding_language_v1,
)


class LanguageConstitutionTests(unittest.TestCase):
    def test_rejects_queue_and_validation_language(self) -> None:
        self.assertTrue(violates_merchant_understanding_language_v1("86 سلة قيد المتابعة مع العملاء."))
        self.assertTrue(violates_merchant_understanding_language_v1("queue size elevated"))
        self.assertTrue(violates_merchant_understanding_language_v1("validation failed"))
        self.assertTrue(violates_merchant_understanding_language_v1("scheduler ready"))
        self.assertFalse(
            violates_merchant_understanding_language_v1(PREFERRED_HEALTH_LIMITED_AR)
        )

    def test_rewrite_queue_count_to_understanding(self) -> None:
        out = rewrite_for_merchant_understanding_v1(
            "86 سلة قيد المتابعة مع العملاء.",
            surface="carts",
            fallback=PREFERRED_CARTS_NEED_ATTENTION_AR,
        )
        self.assertEqual(out, PREFERRED_CARTS_NEED_ATTENTION_AR)
        self.assertFalse(out[0].isdigit())


class FourQuestionsTests(unittest.TestCase):
    def test_preferred_health_publishes(self) -> None:
        v = evaluate_merchant_understanding_v1(
            PREFERRED_HEALTH_LIMITED_AR, surface="health"
        )
        self.assertTrue(v["publish"])
        self.assertTrue(v["helps_understand_business"])
        self.assertTrue(v["about_store_not_cartflow"])

    def test_cartflow_internals_suppressed(self) -> None:
        pub = publish_executive_statement_v1(
            "Scheduler state ready — waiting_total=12",
            surface="health",
            fallback=PREFERRED_NO_CRITICAL_AR,
        )
        self.assertTrue(pub["suppressed"] or pub["text_ar"] == PREFERRED_NO_CRITICAL_AR)
        self.assertNotIn("scheduler", pub["text_ar"].lower())
        self.assertNotIn("waiting_total", pub["text_ar"])


class MerchantUnderstandingComposeTests(unittest.TestCase):
    def test_care_about_not_cartflow_process(self) -> None:
        mu = compose_merchant_understanding_v1(
            {
                "store_facts_ar": {
                    "health": "فرص استعادة المبيعات محدودة اليوم.",
                    "carts": "43 سلة قيد المتابعة مع العملاء.",
                    "communication": "تواصل العملاء يسير بشكل طبيعي.",
                }
            },
            decisions=[
                {
                    "decision_id": "d1",
                    "business_domain": "recovery",
                    "merchant_decision": "راجع مسار الاسترجاع.",
                }
            ],
            home_teasers={
                "store_health_ar": "فرص استعادة المبيعات محدودة اليوم.",
                "carts_ar": "43 سلة قيد المتابعة مع العملاء.",
                "communication_ar": "تواصل العملاء يسير بشكل طبيعي.",
            },
        )
        self.assertTrue(mu["gate_2x_merchant_understanding"])
        self.assertEqual(
            mu["home_teasers"]["carts_ar"], PREFERRED_CARTS_NEED_ATTENTION_AR
        )
        self.assertEqual(
            mu["decisions"][0]["merchant_decision"],
            PREFERRED_DECISION_RECOVERY_CONTACT_AR,
        )
        self.assertEqual(
            mu["guiding_principle"], "merchant_understands_store_not_cartflow"
        )


class PipelineStampTests(unittest.TestCase):
    def test_compose_stamps_gate_2x(self) -> None:
        from services.decision_composition_engine_v1.compose_v1 import compose_decisions_v1

        pkg = compose_decisions_v1(
            "demo",
            counters={
                "available": True,
                "store_slug": "demo",
                "no_phone_total": 4,
                "waiting_total": 4,
                "engaged_total": 0,
                "active_total": 4,
            },
            findings=[],
            use_cache=False,
        )
        self.assertTrue(pkg.get("gate_2x_merchant_understanding"))
        self.assertTrue(
            (pkg.get("merchant_understanding_v1") or {}).get(
                "gate_2x_merchant_understanding"
            )
        )
        carts = ((pkg.get("business_domains_v1") or {}).get("home_teasers") or {}).get(
            "carts_ar"
        ) or ""
        # Executive Control allows count-led cart condition ("N سلة تحتاج…");
        # still forbid internal queue field names.
        self.assertNotIn("waiting_total", carts)
        self.assertTrue(
            ("سلة" in carts) or ("سلال" in carts) or ("مستقر" in carts),
            carts,
        )
        top = (pkg.get("portfolio") or [{}])[0]
        self.assertTrue(top.get("gate_2x_merchant_understanding"))
        decision = top.get("merchant_decision") or ""
        self.assertTrue(
            ("رقم العميل" in decision)
            or ("تدخلك" in decision)
            or ("إتمام الشراء" in decision),
            decision,
        )
        self.assertTrue(pkg.get("gate_merchant_understanding_repair_v1"))
        pub = pkg.get("merchant_publication_v1") or {}
        self.assertTrue(pub.get("ok"))
        # Exactly one primary executive action; may be product-led over portfolio[0].
        self.assertTrue(pub.get("primary_action") or pub.get("primary_business_action"))
        if pub.get("highest_priority_decision_id") and not pub.get("primary_situation_id"):
            self.assertEqual(pub.get("highest_priority_decision_id"), top.get("decision_id"))


class HomeFeelsLikeStoreTests(unittest.TestCase):
    def test_home_carts_not_queue_report(self) -> None:
        from services.home_executive_summary_v1.compose_v1 import (
            build_home_executive_summary_v1,
        )

        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "health": {
                        "domain_summary_ar": "فرص استعادة المبيعات محدودة اليوم.",
                        "needs_attention": True,
                    },
                    "decisions": {
                        "count": 1,
                        "top_title_ar": "راجع تجربة إتمام الشراء ومتابعة العملاء.",
                    },
                    "observations": {"count": 0, "top": None},
                    "carts": {
                        "waiting": 86,
                        "active": 86,
                        "no_phone": 0,
                        "domain_summary_ar": "86 سلة قيد المتابعة مع العملاء.",
                    },
                    "communication": {
                        "domain_summary_ar": "تواصل العملاء يسير بشكل طبيعي.",
                    },
                }
            }
        )
        self.assertTrue((hes.get("governance") or {}).get("merchant_understanding"))
        carts = next(s for s in hes["sections"] if s["id"] == "carts")
        self.assertEqual(carts["summary_ar"], PREFERRED_CARTS_NEED_ATTENTION_AR)
        self.assertFalse(str(carts["summary_ar"])[:1].isdigit())
        blob = " ".join(s.get("summary_ar") or "" for s in hes["sections"])
        self.assertNotIn("scheduler", blob.lower())
        self.assertNotIn("validation", blob.lower())


if __name__ == "__main__":
    unittest.main()
