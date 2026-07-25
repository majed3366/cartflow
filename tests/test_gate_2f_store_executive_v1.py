# -*- coding: utf-8 -*-
"""Gate 2F — Store Executive Thinking."""
from __future__ import annotations

import unittest

from services.decision_composition_engine_v1.store_executive_understanding_v1 import (
    compose_store_executive_understanding_v1,
    is_system_centric_executive_text_v1,
    sanitize_executive_text_v1,
)


def _counters(*, no_phone=0, waiting=0, engaged=0, active=2):
    return {
        "available": True,
        "store_slug": "demo",
        "no_phone_total": no_phone,
        "waiting_total": waiting,
        "engaged_total": engaged,
        "active_total": active,
    }


class SystemCentricFilterTests(unittest.TestCase):
    def test_rejects_counter_and_module_language(self) -> None:
        self.assertTrue(is_system_centric_executive_text_v1("43 سلة بلا رقم تواصل"))
        self.assertTrue(is_system_centric_executive_text_v1("Scheduler state ready"))
        self.assertTrue(is_system_centric_executive_text_v1("محرك الاسترجاع متوقف"))
        self.assertFalse(
            is_system_centric_executive_text_v1("فرص استعادة المبيعات محدودة اليوم.")
        )

    def test_sanitize_falls_back(self) -> None:
        out = sanitize_executive_text_v1(
            "waiting_total=12", fallback="نشاط المتجر مستقر."
        )
        self.assertEqual(out, "نشاط المتجر مستقر.")


class StoreExecutiveBriefingTests(unittest.TestCase):
    def test_morning_briefing_business_first(self) -> None:
        from services.decision_composition_engine_v1.business_domains_v1 import (
            normalize_business_domains_v1,
        )

        domains = normalize_business_domains_v1(
            _counters(no_phone=4, waiting=4), [], store_slug="demo"
        )
        exec_pkg = compose_store_executive_understanding_v1(
            domains,
            decisions=[
                {
                    "business_domain": "recovery",
                    "merchant_decision": "راجع مسار الاسترجاع.",
                }
            ],
        )
        self.assertTrue(exec_pkg["gate_2f_store_executive"])
        health = exec_pkg["home_teasers"]["store_health_ar"]
        self.assertIn("فرص", health)
        self.assertNotIn("انخفض", health)  # avoid recovery-engine tone
        self.assertNotIn("بلا رقم", health)
        title = exec_pkg["home_teasers"]["decisions_top_title_ar"]
        self.assertIn("إتمام الشراء", title)
        self.assertNotIn("43", title)
        briefing = exec_pkg["briefing"]
        for key in (
            "store_healthy",
            "revenue_signal_ar",
            "products_attention_ar",
            "top_decision_ar",
            "recovery_healthy_ar",
            "communication_healthy_ar",
        ):
            self.assertIn(key, briefing)

    def test_pipeline_stamps_gate_2f_and_rewrites_title(self) -> None:
        from services.decision_composition_engine_v1.compose_v1 import compose_decisions_v1

        pkg = compose_decisions_v1(
            "demo",
            counters=_counters(no_phone=5, waiting=5),
            findings=[],
            use_cache=False,
        )
        self.assertTrue(pkg.get("gate_2f_store_executive"))
        self.assertTrue(
            (pkg.get("store_executive_understanding_v1") or {}).get(
                "gate_2f_store_executive"
            )
        )
        top = pkg["portfolio"][0]
        self.assertEqual(
            top["merchant_decision"],
            "راجع تجربة إتمام الشراء ومتابعة العملاء.",
        )
        home = (pkg.get("business_domains_v1") or {}).get("home_teasers") or {}
        self.assertIn("فرص", home.get("store_health_ar") or "")
        self.assertNotEqual(
            home.get("store_health_ar"), top["merchant_decision"]
        )

    def test_home_feels_like_store_not_cartflow(self) -> None:
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
                        "abandoned_carts": 3,
                        "no_phone": 3,
                    },
                    "decisions": {
                        "count": 1,
                        "top_title_ar": "راجع تجربة إتمام الشراء ومتابعة العملاء.",
                        "evidence": "store_executive_understanding",
                    },
                    "observations": {"count": 0},
                    "carts": {
                        "waiting": 3,
                        "domain_summary_ar": "3 سلة قيد المتابعة مع العملاء.",
                    },
                    "communication": {
                        "waiting": 3,
                        "no_phone": 2,
                        "domain_summary_ar": "تواصل العملاء يحتاج انتباهاً — المتابعة مقيدة لبعض الحالات.",
                    },
                }
            }
        )
        by_id = {s["id"]: s for s in hes["sections"]}
        blob = " ".join(s["summary_ar"] for s in hes["sections"])
        self.assertNotIn("CartFlow", blob)
        self.assertNotIn("scheduler", blob.lower())
        self.assertNotIn("عدّاد", blob)
        self.assertIn("فرص", by_id["health"]["summary_ar"])
        self.assertIn("إتمام الشراء", by_id["decisions"]["summary_ar"])
        self.assertIn("أدلة كافية", by_id["observations"]["summary_ar"])
        self.assertTrue(hes["governance"].get("store_executive_thinking"))


if __name__ == "__main__":
    unittest.main()
