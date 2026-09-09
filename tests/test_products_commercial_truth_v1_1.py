# -*- coding: utf-8 -*-
"""Products V1.1 — commercial readability. No new ranker. Query delta must not rise."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from services.live_reality_lab_v1.catalog_v2 import NAMED_PRODUCTS
from services.live_reality_lab_v1.contract_v1 import (
    LAB_STORE_SLUG,
    MISSING_NAME_PRODUCT_ID,
)
from services.products_commercial_truth_v1.compose_v1 import (
    compose_products_commercial_truth_v1,
)
from services.products_commercial_truth_v1.contract_v1 import (
    EXPOSURE_LAB_SYNTHETIC,
    EXPOSURE_NONE_RECORDED,
    EXPOSURE_NOT_STORED,
    EXPOSURE_UNAVAILABLE_AR,
    FORBIDDEN_CAUSAL_AR,
    PRESENTATION_DEGRADED,
    PRESENTATION_NEUTRAL,
    PRESENTATION_STRONG,
    QUERY_COUNT_LAB,
    QUERY_COUNT_NORMAL,
    READ_MODEL_OWNER,
)

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _r17_observed_preloaded() -> dict:
    """R17-shaped facts matching founder-observed stored truth. Not a fixture page."""
    catalog = []
    carts = {}
    visits = {}
    hesitation = {
        "nf-oud-royal": {"price": 5},
        "nf-amber-night": {"shipping": 4},
        "nf-musk-tahara": {"shipping": 4},
        "nf-hair-serum": {"thinking": 3},
    }
    for pid, name, price, slots in NAMED_PRODUCTS:
        catalog.append(
            {
                "product_id": pid,
                "name": name,
                "price": price,
                "currency": "SAR",
                "missing_name": False,
            }
        )
        carts[pid] = {
            "cart_count": int(slots),
            "cart_value": float(price) * int(slots),
        }
        visits[pid] = 0
    visits["nf-oud-royal"] = 5
    visits["nf-amber-night"] = 4
    visits["nf-musk-tahara"] = 4
    visits["nf-hair-serum"] = 3
    catalog.append(
        {
            "product_id": MISSING_NAME_PRODUCT_ID,
            "name": "",
            "price": 39.0,
            "currency": "SAR",
            "missing_name": True,
        }
    )
    carts[MISSING_NAME_PRODUCT_ID] = {"cart_count": 1, "cart_value": 39.0}
    return {
        "catalog": catalog,
        "carts": carts,
        "purchases": {},
        "hesitation": hesitation,
        "visits": visits,
        "query_count": QUERY_COUNT_LAB,
    }


def _pkg(slug=LAB_STORE_SLUG, **kwargs):
    return compose_products_commercial_truth_v1(
        store_slug=slug, preloaded=_r17_observed_preloaded(), **kwargs
    )


def _by_id(pkg):
    return {p["product_id"]: p for p in pkg["products"]}


class ProductsV11ReadabilityTests(unittest.TestCase):
    def test_debt_pack_records_closure(self) -> None:
        debt = _read(
            "docs/architecture/products_read_model_query_fanout_v1/README.md"
        )
        base = _read(
            "docs/architecture/products_read_model_query_fanout_v1/PHASE0_BASELINE.md"
        )
        self.assertIn("PRODUCTS_READ_MODEL_QUERY_FANOUT_V1", debt)
        self.assertIn("CLOSED", debt)
        self.assertIn("normal = **+1**", debt)
        self.assertIn("lab = **+1**", debt)
        self.assertIn("7096de1564c008ac83da6216c70aba22f328071a", base)
        self.assertIn("+4", base)
        self.assertIn("+5", base)

    def test_query_delta_does_not_increase(self) -> None:
        self.assertLessEqual(QUERY_COUNT_NORMAL, 1)
        self.assertLessEqual(QUERY_COUNT_LAB, 2)
        compose = _read("services/products_commercial_truth_v1/compose_v1.py")
        self.assertIn("QUERY_COUNT_NORMAL", compose)
        self.assertIn("QUERY_COUNT_LAB", compose)
        self.assertNotIn("QUERY_COUNT_NORMAL = 5", compose)
        self.assertNotIn("QUERY_COUNT_LAB = 6", compose)

    def test_no_repeated_needs_attention_on_paint(self) -> None:
        from services.products_commercial_truth_v1.compose_v1 import (  # noqa: PLC0415
            compose_products_commercial_truth_v1,
        )

        js = _read("static/merchant_ui_v2_products.js")
        self.assertNotIn("يحتاج انتباه", js)
        self.assertNotIn("attention_label_ar", js)
        pkg = _pkg()
        for g in pkg["groups"]:
            self.assertNotEqual(g.get("label_ar"), "يحتاج انتباه")

    def test_no_frontend_ranker_or_causal_invention(self) -> None:
        js = _read("static/merchant_ui_v2_products.js")
        self.assertIn('data-cf2-frontend-ranking="0"', js)
        self.assertNotIn(".sort(", js)
        self.assertNotIn("priority score", js)
        self.assertNotIn("urgency", js)
        for phrase in FORBIDDEN_CAUSAL_AR:
            self.assertNotIn(phrase, js)
        compose = _read("services/products_commercial_truth_v1/compose_v1.py")
        self.assertNotIn("compose_commercial_opportunity_layer", compose)
        self.assertNotIn("compose_mission_catalog", compose)

    def test_r17_card_hierarchy_and_signals(self) -> None:
        pkg = _pkg()
        self.assertEqual(pkg["read_model_owner"], READ_MODEL_OWNER)
        self.assertEqual(pkg["frontend_ranking"], 0)
        self.assertEqual(pkg["n_plus_one"], 0)
        rows = _by_id(pkg)
        oud = rows["nf-oud-royal"]
        amber = rows["nf-amber-night"]
        gift = rows["nf-gift-set"]
        missing = rows[MISSING_NAME_PRODUCT_ID]
        self.assertEqual(oud["cart_count"], 5)
        self.assertEqual(oud["cart_value"], 945.0)
        self.assertEqual(oud["purchases"], 0)
        self.assertTrue(oud["purchase_known"])
        self.assertEqual(oud["hesitation_reason_counts"].get("price"), 5)
        self.assertIn("السعر تكرر في 5", oud["signal_ar"])
        self.assertEqual(oud["presentation_kind"], PRESENTATION_STRONG)
        self.assertEqual(amber["cart_count"], 4)
        self.assertEqual(amber["cart_value"], 596.0)
        self.assertEqual(amber["hesitation_reason_counts"].get("shipping"), 4)
        self.assertIn("الشحن تكرر في 4", amber["signal_ar"])
        self.assertEqual(gift["cart_count"], 4)
        self.assertEqual(gift["cart_value"], 996.0)
        self.assertEqual(gift["purchases"], 0)
        self.assertIn("دون مشتريات مسجّلة", gift["signal_ar"])
        self.assertEqual(gift["presentation_kind"], PRESENTATION_NEUTRAL)
        self.assertIn(gift["exposure"]["state"], (EXPOSURE_NONE_RECORDED, EXPOSURE_NOT_STORED))
        self.assertIsNone(gift["exposure"]["count"])
        self.assertEqual(gift["exposure"]["value_ar"], EXPOSURE_UNAVAILABLE_AR)
        self.assertEqual(missing["presentation_kind"], PRESENTATION_DEGRADED)
        self.assertEqual(missing["product_name"], "منتج بدون اسم في الكتالوج")
        self.assertEqual(oud["exposure"]["state"], EXPOSURE_LAB_SYNTHETIC)
        self.assertEqual(oud["exposure"]["count"], 5)
        self.assertEqual(oud["exposure"]["note_ar"], "ليست زيارات متجر حقيقية.")
        painted = json.dumps(pkg, ensure_ascii=False)
        for phrase in FORBIDDEN_CAUSAL_AR:
            self.assertNotIn(phrase, painted)
        self.assertEqual(pkg["unique_visitor_claim"], 0)

    def test_normal_merchant_exposure_not_zero(self) -> None:
        pkg = compose_products_commercial_truth_v1(
            store_slug="acme_store", preloaded=_r17_observed_preloaded()
        )
        self.assertEqual(pkg["query_delta"], 0)
        for row in pkg["products"]:
            self.assertEqual(row["exposure"]["state"], EXPOSURE_NOT_STORED)
            self.assertIsNone(row["exposure"]["count"])
            self.assertEqual(row["exposure"]["value_ar"], EXPOSURE_UNAVAILABLE_AR)

    def test_home_workspace_carts_untouched_by_products_js(self) -> None:
        home = _read("static/merchant_ui_v2_home.js")
        ws = _read("static/merchant_ui_v2_workspace.js")
        carts = _read("static/merchant_ui_v2_carts.js")
        self.assertNotIn("/api/dashboard/products", home)
        self.assertNotIn("/api/dashboard/products", ws)
        self.assertNotIn("/api/dashboard/products", carts)
        self.assertNotIn("أبرز إشارة", home)
        self.assertNotIn("أبرز إشارة", ws)


if __name__ == "__main__":
    unittest.main()
