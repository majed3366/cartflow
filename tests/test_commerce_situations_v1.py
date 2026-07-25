# -*- coding: utf-8 -*-
"""Commerce Situation Engine V1 — entity-bound many facts → one situation."""
from __future__ import annotations

import unittest

from services.commerce_situations_v1.compose_v1 import compose_commerce_situations_v1
from services.commerce_situations_v1.consume_v1 import surface_projection_v1
from services.commerce_situations_v1.contract_v1 import (
    KIND_INTEREST_WITHOUT_PURCHASE,
    KIND_SHIPPING_FRICTION,
    validate_commerce_situation_v1,
)
from services.commerce_situations_v1.route_v1 import (
    route_commerce_situations_v1,
    workspace_cards_from_commerce_situations_v1,
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
        {"kind": "product", "id": product.lower().replace(" ", "-"), "name_ar": product}
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
            "observation_ids": [f"obs-{fact_id}"],
            "evidence_ref_count": 1,
        },
        "confidence": {"level": "high", "ar": "مرتفع", "score": score},
        "freshness": {"status": "current"},
        "impact_category": fact_type,
        "recommendation": None,
    }


class EntityBoundCollapseTests(unittest.TestCase):
    def test_many_facts_one_situation_per_entity_kind(self) -> None:
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
                meaning="العملاء يعودون دون شراء",
                product="Raven — حزام جلد للساعة",
                caps=["repeated_return_without_purchase"],
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
        pkg = compose_commerce_situations_v1(
            {"ok": True, "facts": facts, "store_slug": "demo"},
            store_slug="demo",
        )
        self.assertTrue(pkg["ok"])
        self.assertEqual(pkg["counts"]["facts_in"], 5)
        published = list(pkg["published_situations"] or [])
        kinds = [s.get("situation_kind") for s in published]
        self.assertIn(KIND_INTEREST_WITHOUT_PURCHASE, kinds)
        self.assertIn(KIND_SHIPPING_FRICTION, kinds)
        # Anti-Theme: two product interest situations, not one type bucket.
        interest = [
            s for s in published if s["situation_kind"] == KIND_INTEREST_WITHOUT_PURCHASE
        ]
        self.assertEqual(len(interest), 2)
        raven = next(
            s for s in interest if "Raven" in str((s.get("subject") or {}).get("name_ar"))
        )
        self.assertEqual(len(raven["supporting_fact_ids"]), 2)
        ship = next(
            s for s in published if s["situation_kind"] == KIND_SHIPPING_FRICTION
        )
        self.assertEqual(len(ship["supporting_fact_ids"]), 2)
        self.assertGreaterEqual(float(pkg["counts"]["collapsed_ratio"]), 1.5)
        self.assertIsNone(pkg.get("recommendation"))
        for s in published:
            self.assertEqual(validate_commerce_situation_v1(s), [])
            self.assertTrue(s.get("admitted"))
            self.assertFalse(s.get("product_intelligence"))

    def test_no_type_only_collapse_across_products(self) -> None:
        facts = [
            _fact(
                fact_id="a",
                fact_type="conversion",
                meaning="تحويل ضعيف",
                product="Alpha",
                caps=["high_interest_low_conversion"],
            ),
            _fact(
                fact_id="b",
                fact_type="conversion",
                meaning="تحويل ضعيف",
                product="Beta",
                caps=["high_interest_low_conversion"],
            ),
        ]
        pkg = compose_commerce_situations_v1(
            {"facts": facts, "store_slug": "demo"}, store_slug="demo"
        )
        interest = [
            s
            for s in pkg["published_situations"]
            if s["situation_kind"] == KIND_INTEREST_WITHOUT_PURCHASE
        ]
        self.assertEqual(len(interest), 2)
        ids = {(s.get("subject") or {}).get("id") for s in interest}
        self.assertEqual(len(ids), 2)

    def test_flag_off_returns_empty(self) -> None:
        pkg = compose_commerce_situations_v1(
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
            environ={"CARTFLOW_COMMERCE_SITUATIONS_V1": "0"},
        )
        self.assertFalse(pkg["ok"])
        self.assertEqual(pkg["situations"], [])


class RoutingAndConsumerTests(unittest.TestCase):
    def test_home_workspace_same_situation_ids(self) -> None:
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
                meaning="يعودون دون شراء",
                product="Raven",
                caps=["repeated_return_without_purchase"],
            ),
        ]
        pkg = compose_commerce_situations_v1(
            {"facts": facts, "store_slug": "demo"}, store_slug="demo"
        )
        routed = route_commerce_situations_v1(pkg)
        self.assertIsNotNone(routed["home_teaser"]["top"])
        self.assertEqual(
            routed["home_teaser"]["top"]["source"], "commerce_situations_v1"
        )
        cards = workspace_cards_from_commerce_situations_v1(pkg)
        self.assertEqual(len(cards), 1)
        self.assertTrue(all(c.get("gate_commerce_situations") for c in cards))
        self.assertEqual(cards[0]["supporting_fact_count"], 2)
        home_ids = set(surface_projection_v1(pkg, "home")["situation_ids"])
        ws_ids = set(surface_projection_v1(pkg, "decision_workspace")["situation_ids"])
        prod_ids = set(surface_projection_v1(pkg, "products")["situation_ids"])
        carts_ids = set(surface_projection_v1(pkg, "carts")["situation_ids"])
        self.assertEqual(home_ids, ws_ids)
        self.assertEqual(home_ids, prod_ids)
        self.assertEqual(home_ids, carts_ids)
        self.assertFalse(
            any(i.get("reinterpretation") for i in surface_projection_v1(pkg, "carts")["items"])
        )


class HomeIntegrationTests(unittest.TestCase):
    def test_hes_portfolio_lists_distinct_situations(self) -> None:
        from services.home_executive_summary_v1.compose_v1 import (
            build_home_executive_summary_v1,
        )

        items = [
            {
                "situation_id": "cs:interest_without_purchase|raven:demo",
                "situation_kind": "interest_without_purchase",
                "title_ar": "اهتمام دون شراء — Raven",
                "statement_ar": "Raven يجذب الاهتمام دون شراء.",
                "product_name_ar": "Raven",
                "href": "#workspace?situation_id=cs:interest_without_purchase|raven:demo",
                "source": "commerce_situations_v1",
            },
            {
                "situation_id": "cs:shipping_friction|truesound:demo",
                "situation_kind": "shipping_friction",
                "title_ar": "احتكاك الشحن — TrueSound",
                "statement_ar": "الشحن يضعف إتمام شراء TrueSound.",
                "product_name_ar": "TrueSound",
                "href": "#workspace?situation_id=cs:shipping_friction|truesound:demo",
                "source": "commerce_situations_v1",
            },
            {
                "situation_id": "cs:communication_coverage|store:demo",
                "situation_kind": "communication_coverage",
                "title_ar": "تغطية التواصل",
                "statement_ar": "تواصل العملاء يسير بشكل طبيعي.",
                "href": "#workspace?situation_id=cs:communication_coverage|store:demo",
                "source": "commerce_situations_v1",
            },
        ]
        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "health": {"domain_summary_ar": "نشاط المتجر مستقر."},
                    "decisions": {"count": 0, "top_title_ar": ""},
                    "observations": {
                        "count": 3,
                        "top": {
                            "source": "commerce_situations_v1",
                            "situations": items,
                            "situation_id": items[0]["situation_id"],
                            "statement_ar": items[0]["statement_ar"],
                            "title_ar": items[0]["title_ar"],
                        },
                        "evidence": "commerce_situations",
                    },
                    "carts": {"waiting": 0, "domain_summary_ar": "تقدّم سلال العملاء مستقر."},
                    "communication": {
                        "domain_summary_ar": "تواصل العملاء يسير بشكل طبيعي."
                    },
                }
            }
        )
        section_ids = [s["id"] for s in hes["sections"]]
        self.assertIn("situations", section_ids)
        self.assertNotIn("decisions", section_ids)
        self.assertNotIn("observations", section_ids)
        portfolio = next(s for s in hes["sections"] if s["id"] == "situations")
        self.assertEqual(portfolio.get("built_from"), "commerce_situations_v1")
        self.assertEqual(len(portfolio.get("items") or []), 3)
        self.assertEqual(
            portfolio["items"][0]["situation_id"],
            "cs:interest_without_purchase|raven:demo",
        )
        ids = {i["situation_id"] for i in portfolio["items"]}
        self.assertEqual(len(ids), 3)


class AllowlistTests(unittest.TestCase):
    def test_dev_route_allowlisted(self) -> None:
        from main import _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT

        self.assertIn(
            "/dev/commerce-situations", _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT
        )


if __name__ == "__main__":
    unittest.main()
