# -*- coding: utf-8 -*-
"""Business Theme Engine V1 — many facts → one canonical theme."""
from __future__ import annotations

import unittest

from services.business_themes_v1.compose_v1 import compose_business_themes_v1
from services.business_themes_v1.contract_v1 import (
    THEME_PRODUCT_CONVERSION,
    THEME_SHIPPING_FRICTION,
    validate_business_theme_v1,
)
from services.business_themes_v1.route_v1 import (
    route_business_themes_v1,
    workspace_cards_from_business_themes_v1,
)


def _fact(
    *,
    fact_id: str,
    fact_type: str,
    meaning: str,
    product: str = "",
    caps: list[str] | None = None,
    score: int = 80,
) -> dict:
    subject = (
        {"kind": "product", "id": product.lower(), "name_ar": product}
        if product
        else {"kind": "store", "id": "store", "name_ar": "المتجر"}
    )
    return {
        "fact_id": fact_id,
        "fact_type": fact_type,
        "subject": subject,
        "business_meaning_ar": meaning,
        "evidence": {
            "capability_ids": list(caps or []),
            "evidence_ref_count": 1,
        },
        "confidence": {"level": "high", "ar": "مرتفع", "score": score},
        "freshness": {"status": "current"},
        "impact_category": fact_type,
        "recommendation": None,
    }


class ManyFactsOneThemeTests(unittest.TestCase):
    def test_many_conversion_facts_collapse_to_one_theme(self) -> None:
        facts = [
            _fact(
                fact_id="f1",
                fact_type="conversion",
                meaning="اهتمام مرتفع وتحويل ضعيف",
                product="Raven — حزام جلد للساعة",
                caps=["high_interest_low_conversion"],
            ),
            _fact(
                fact_id="f2",
                fact_type="conversion",
                meaning="زيارات متكررة دون شراء",
                product="Raven — حزام جلد للساعة",
                caps=["high_interest_low_conversion"],
            ),
            _fact(
                fact_id="f3",
                fact_type="conversion",
                meaning="إضافة للسلة دون إتمام",
                product="Horizon — سماعة",
                caps=["high_interest_low_conversion"],
            ),
            _fact(
                fact_id="f4",
                fact_type="product_demand",
                meaning="الشحن يضعف الإتمام",
                product="TrueSound — سماعة لاسلكية",
                caps=["shipping_stronger_than_price"],
            ),
            _fact(
                fact_id="f5",
                fact_type="product_demand",
                meaning="تكلفة الشحن ظاهرة قبل الشراء",
                product="TrueSound — سماعة لاسلكية",
                caps=["shipping_stronger_than_price"],
            ),
        ]
        pkg = compose_business_themes_v1(
            {"ok": True, "facts": facts, "store_slug": "demo"},
            store_slug="demo",
        )
        self.assertTrue(pkg["ok"])
        self.assertEqual(pkg["counts"]["facts_in"], 5)
        published = list(pkg["published_themes"] or [])
        types = [t.get("theme_type") for t in published]
        self.assertEqual(len(types), len(set(types)), "no duplicated theme types")
        self.assertIn(THEME_PRODUCT_CONVERSION, types)
        self.assertIn(THEME_SHIPPING_FRICTION, types)
        conv = next(t for t in published if t["theme_type"] == THEME_PRODUCT_CONVERSION)
        ship = next(t for t in published if t["theme_type"] == THEME_SHIPPING_FRICTION)
        self.assertEqual(len(conv["supporting_fact_ids"]), 3)
        self.assertEqual(len(ship["supporting_fact_ids"]), 2)
        self.assertGreaterEqual(float(pkg["counts"]["collapsed_ratio"]), 2.0)
        self.assertIsNone(pkg.get("recommendation"))
        for t in published:
            self.assertEqual(validate_business_theme_v1(t), [])
            self.assertIsNone(t.get("recommendation"))
            self.assertTrue(t.get("admitted"))
            self.assertEqual(t.get("primary_owner"), "decision_workspace")

    def test_flag_off_returns_empty(self) -> None:
        pkg = compose_business_themes_v1(
            {
                "facts": [
                    _fact(
                        fact_id="f1",
                        fact_type="conversion",
                        meaning="x",
                        product="A",
                        caps=["high_interest_low_conversion"],
                    )
                ]
            },
            environ={"CARTFLOW_BUSINESS_THEMES_V1": "0"},
        )
        self.assertFalse(pkg["ok"])
        self.assertEqual(pkg["themes"], [])


class RoutingTests(unittest.TestCase):
    def test_home_teaser_and_workspace_one_card_per_theme(self) -> None:
        facts = [
            _fact(
                fact_id="c1",
                fact_type="conversion",
                meaning="تحويل ضعيف",
                product="Raven",
                caps=["high_interest_low_conversion"],
            ),
            _fact(
                fact_id="c2",
                fact_type="conversion",
                meaning="اهتمام بلا شراء",
                product="Raven",
                caps=["high_interest_low_conversion"],
            ),
            _fact(
                fact_id="s1",
                fact_type="product_demand",
                meaning="الشحن يضعف",
                product="TrueSound",
                caps=["shipping_stronger_than_price"],
            ),
        ]
        pkg = compose_business_themes_v1(
            {"facts": facts, "store_slug": "demo"}, store_slug="demo"
        )
        routed = route_business_themes_v1(pkg)
        self.assertIsNotNone(routed["home_teaser"]["top"])
        self.assertEqual(routed["home_teaser"]["top"]["source"], "business_themes_v1")
        cards = workspace_cards_from_business_themes_v1(pkg)
        self.assertEqual(len(cards), len(pkg["published_themes"]))
        self.assertTrue(all(c.get("gate_business_themes") for c in cards))
        self.assertTrue(all(c.get("recommended_action") == "" for c in cards))


class HomeIntegrationTests(unittest.TestCase):
    def test_hes_uses_theme_executive_summary(self) -> None:
        from services.home_executive_summary_v1.compose_v1 import (
            build_home_executive_summary_v1,
        )

        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "health": {"domain_summary_ar": "نشاط المتجر مستقر."},
                    "decisions": {"count": 0, "top_title_ar": ""},
                    "observations": {
                        "count": 2,
                        "top": {
                            "product_name_ar": "Raven — حزام جلد للساعة",
                            "statement_ar": (
                                "تحويل Raven — حزام جلد للساعة ضعيف رغم اهتمام واضح "
                                "— هذه أولوية تجارية اليوم."
                            ),
                            "title_ar": "تحويل المنتجات",
                            "theme_type": "product_conversion",
                            "source": "business_themes_v1",
                        },
                        "evidence": "business_themes",
                    },
                    "carts": {"waiting": 0, "domain_summary_ar": "تقدّم سلال العملاء مستقر."},
                    "communication": {
                        "domain_summary_ar": "تواصل العملاء يسير بشكل طبيعي."
                    },
                }
            }
        )
        obs = next(s for s in hes["sections"] if s["id"] == "observations")
        self.assertEqual(obs["title_ar"], "مواضيع المتجر")
        self.assertEqual(obs.get("built_from"), "business_themes_v1")
        self.assertIn("أولوية تجارية", obs["summary_ar"])
        self.assertNotIn("waiting_total", obs["summary_ar"])


class AllowlistTests(unittest.TestCase):
    def test_dev_route_allowlisted(self) -> None:
        from main import _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT

        self.assertIn("/dev/business-themes", _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT)


if __name__ == "__main__":
    unittest.main()
