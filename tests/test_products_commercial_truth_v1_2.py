# -*- coding: utf-8 -*-
"""Products V1.2 — presentation density only. Compose/order/debt unchanged."""
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
    EXPOSURE_NOT_STORED,
    EXPOSURE_UNAVAILABLE_AR,
    FORBIDDEN_CAUSAL_AR,
    QUERY_COUNT_LAB,
    QUERY_COUNT_NORMAL,
    READ_MODEL_OWNER,
)

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _r17_observed_preloaded() -> dict:
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


def _pkg(slug=LAB_STORE_SLUG):
    return compose_products_commercial_truth_v1(
        store_slug=slug, preloaded=_r17_observed_preloaded()
    )


def _by_id(pkg):
    return {p["product_id"]: p for p in pkg["products"]}


class ProductsV12PresentationTests(unittest.TestCase):
    def test_backend_contract_and_order_unchanged(self) -> None:
        compose = _read("services/products_commercial_truth_v1/compose_v1.py")
        contract = _read("services/products_commercial_truth_v1/contract_v1.py")
        self.assertIn("أسباب تردد مسجّلة لهذا المنتج", compose)
        self.assertIn("QUERY_COUNT_NORMAL", compose)
        self.assertLessEqual(QUERY_COUNT_NORMAL, 1)
        self.assertLessEqual(QUERY_COUNT_LAB, 2)
        self.assertIn("products_commercial_truth_v1_1", contract)
        lab = _pkg()
        ids = [p["product_id"] for p in lab["products"]]
        again = _pkg()
        self.assertEqual(ids, [p["product_id"] for p in again["products"]])
        self.assertEqual(lab["read_model_owner"], READ_MODEL_OWNER)
        self.assertEqual(lab["frontend_ranking"], 0)
        self.assertEqual(lab["n_plus_one"], 0)
        self.assertEqual(lab["unique_visitor_claim"], 0)

    def test_debt_is_closed(self) -> None:
        debt = _read(
            "docs/architecture/products_read_model_query_fanout_v1/README.md"
        )
        self.assertIn("PRODUCTS_READ_MODEL_QUERY_FANOUT_V1", debt)
        self.assertIn("CLOSED", debt)
        self.assertIn("normal = **+1**", debt)
        self.assertIn("lab = **+1**", debt)

    def test_frontend_is_presentation_only(self) -> None:
        js = _read("static/merchant_ui_v2_products.js")
        self.assertIn('data-cf2-prd-v="1.2"', js)
        self.assertIn('data-cf2-frontend-ranking="0"', js)
        self.assertIn("data-cf2-product-truth-strength", js)
        self.assertIn("أسباب تردد لهذا المنتج", js)
        self.assertIn("أسباب تردد مسجّلة لهذا المنتج", js)
        self.assertNotIn(".sort(", js)
        self.assertNotIn("weight", js)
        self.assertNotIn("يحتاج انتباه", js)
        self.assertNotIn("top product", js)
        self.assertNotIn("priority product", js)
        self.assertNotIn("best opportunity", js)
        self.assertNotIn("unique_visitor", js)
        for phrase in FORBIDDEN_CAUSAL_AR:
            self.assertNotIn(phrase, js)

    def test_paint_shortens_signal_and_compacts_exposure(self) -> None:
        js = _read("static/merchant_ui_v2_products.js")
        self.assertIn("cf2-prd__metric-n", js)
        self.assertIn("cf2-prd__cta", js)
        self.assertIn("ctx.href", js)
        pkg = _pkg()
        rows = _by_id(pkg)
        oud = rows["nf-oud-royal"]
        gift = rows["nf-gift-set"]
        missing = rows[MISSING_NAME_PRODUCT_ID]
        self.assertIn("السعر تكرر في 5 أسباب تردد مسجّلة لهذا المنتج", oud["signal_ar"])
        self.assertEqual(oud["exposure"]["state"], EXPOSURE_LAB_SYNTHETIC)
        self.assertEqual(oud["exposure"]["count"], 5)
        self.assertEqual(gift["purchases"], 0)
        self.assertTrue(gift["purchase_known"])
        self.assertIsNone(gift["exposure"]["count"])
        self.assertEqual(missing["product_name"], "منتج بدون اسم في الكتالوج")
        self.assertEqual(missing["product_identity"], "هوية الكتالوج غير مكتملة")

    def test_normal_merchant_visits_remain_unknown(self) -> None:
        pkg = compose_products_commercial_truth_v1(
            store_slug="acme_store", preloaded=_r17_observed_preloaded()
        )
        self.assertEqual(pkg["unique_visitor_claim"], 0)
        for row in pkg["products"]:
            self.assertEqual(row["exposure"]["state"], EXPOSURE_NOT_STORED)
            self.assertIsNone(row["exposure"]["count"])
            self.assertEqual(row["exposure"]["value_ar"], EXPOSURE_UNAVAILABLE_AR)
        painted = json.dumps(pkg, ensure_ascii=False)
        self.assertNotIn("0 زيارة", painted)
        for phrase in FORBIDDEN_CAUSAL_AR:
            self.assertNotIn(phrase, painted)

    def test_home_workspace_carts_untouched(self) -> None:
        home = _read("static/merchant_ui_v2_home.js")
        ws = _read("static/merchant_ui_v2_workspace.js")
        carts = _read("static/merchant_ui_v2_carts.js")
        self.assertNotIn("/api/dashboard/products", home)
        self.assertNotIn("/api/dashboard/products", ws)
        self.assertNotIn("/api/dashboard/products", carts)
        self.assertNotIn("data-cf2-product-truth-strength", home)
        self.assertNotIn("data-cf2-product-truth-strength", ws)
        compose = _read("services/products_commercial_truth_v1/compose_v1.py")
        self.assertNotIn("compose_commercial_opportunity_layer", compose)
        self.assertNotIn("compose_mission_catalog", compose)


if __name__ == "__main__":
    unittest.main()
