# -*- coding: utf-8 -*-
"""Products V1 — commercial product truth surface. No second ranker."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from services.live_reality_lab_v1.catalog_v2 import NAMED_PRODUCTS
from services.live_reality_lab_v1.contract_v1 import (
    LAB_STORE_SLUG,
    LAB_VISIT_TRUTH_CLASS,
    MISSING_NAME_PRODUCT_ID,
)
from services.product_data.product_read_model_contract_v1 import (
    PRODUCT_READ_MODEL_SCHEMA,
    VISIT_FIELD_CLASS_LAB_ONLY,
    VISIT_FIELD_NAME,
)
from services.products_commercial_truth_v1.compose_v1 import (
    compose_products_commercial_truth_v1,
)
from services.products_commercial_truth_v1.contract_v1 import (
    ATTENTION_INSUFFICIENT,
    ATTENTION_NEEDS,
    ATTENTION_OWNER,
    ATTENTION_STABLE,
    EXPOSURE_LAB_SYNTHETIC,
    EXPOSURE_NONE_RECORDED,
    EXPOSURE_NOT_STORED,
    FORBIDDEN_CAUSAL_AR,
    MISSING_NAME_IDENTITY_AR,
    MISSING_NAME_TITLE_AR,
    QUERY_COUNT_LAB,
    QUERY_COUNT_NORMAL,
    READ_MODEL_OWNER,
)

ROOT = Path(__file__).resolve().parents[1]
NORMAL_SLUG = "acme_store"
FOUNDER_SLUG = "cf_founder_evaluation"
FORBIDDEN_MISSING_TITLE = "اسم المنتج غير متوفر"


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _r17_preloaded(*, with_purchase: bool = False) -> dict:
    catalog = []
    carts: dict[str, dict] = {}
    hesitation: dict[str, dict] = {}
    visits: dict[str, int] = {}
    purchases: dict[str, dict] = {}
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
        visits[pid] = 2
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
    hesitation["nf-oud-royal"] = {"shipping": 5}
    hesitation["nf-musk-tahara"] = {"shipping": 4}
    hesitation["nf-rose-damascus"] = {"shipping": 3, "price": 1}
    hesitation["nf-amber-night"] = {"price": 4}
    hesitation["nf-hair-serum"] = {"thinking": 3}
    if with_purchase:
        purchases["nf-gift-set"] = {
            "purchase_count": 2,
            "revenue": 498.0,
            "known": True,
        }
    return {
        "catalog": catalog,
        "carts": carts,
        "purchases": purchases,
        "hesitation": hesitation,
        "visits": visits,
        "query_count": QUERY_COUNT_LAB,
    }


def _lab_pkg(**kwargs):
    return compose_products_commercial_truth_v1(
        store_slug=LAB_STORE_SLUG,
        preloaded=_r17_preloaded(**kwargs),
    )


def _by_id(pkg: dict) -> dict:
    return {p["product_id"]: p for p in pkg["products"]}


class ProductsCommercialTruthV1StaticTests(unittest.TestCase):
    def test_stub_removed_and_owned_surface(self) -> None:
        html = _read("templates/merchant_app_v2.html")
        self.assertNotIn("قسم المنتجات غير متاح", html)
        self.assertIn('id="cf2-products-root"', html)
        self.assertIn("merchant_ui_v2_products.js", html)
        self.assertIn("merchant_ui_v2_products.css", html)
        self.assertIn("أي المنتجات تستحق انتباهي", html)
        app = _read("static/merchant_ui_v2_app.js")
        self.assertIn('section === "products"', app)
        self.assertIn("CartFlowUiV2Products.loadAndPaint", app)
        self.assertIn("products: false", app)
        self.assertEqual(app.count("CartFlowUiV2Products.loadAndPaint"), 1)
        main = _read("main.py")
        self.assertIn("products_commercial_truth_v1_router", main)

    def test_no_frontend_fixtures_or_ranker(self) -> None:
        js = _read("static/merchant_ui_v2_products.js")
        self.assertIn('data-cf2-frontend-ranking="0"', js)
        self.assertIn('data-cf2-frontend-fixtures="0"', js)
        self.assertIn("products-commercial-truth-v1", js)
        self.assertNotIn("عنبر ليلي", js)
        self.assertNotIn("nf-oud-royal", js)
        self.assertNotIn("nf-amber-night", js)
        self.assertNotIn(FORBIDDEN_MISSING_TITLE, js)
        self.assertNotIn("unique_visitor", js)
        self.assertNotIn("AI priority", js)
        self.assertNotIn(".sort(", js)
        self.assertNotIn("weight", js)
        for phrase in FORBIDDEN_CAUSAL_AR:
            self.assertNotIn(phrase, js)

    def test_no_summary_tax_or_side_systems(self) -> None:
        compose = _read("services/products_commercial_truth_v1/compose_v1.py")
        js = _read("static/merchant_ui_v2_products.js")
        home = _read("static/merchant_ui_v2_home.js")
        ws = _read("static/merchant_ui_v2_workspace.js")
        carts = _read("static/merchant_ui_v2_carts.js")
        self.assertNotIn("compose_commercial_opportunity_layer", compose)
        self.assertNotIn("compose_mission_catalog", compose)
        self.assertNotIn("compose_mission_portfolio", compose)
        self.assertNotIn("/api/dashboard/summary", js)
        self.assertNotIn("/api/dashboard/products", home)
        self.assertNotIn("/api/dashboard/products", ws)
        self.assertNotIn("/api/dashboard/products", carts)
        self.assertNotIn("openai", compose.lower())
        self.assertNotIn("anthropic", compose.lower())
        self.assertNotIn("CREATE TABLE", compose.upper())

    def test_paint_uses_server_fields_only(self) -> None:
        js = _read("static/merchant_ui_v2_products.js")
        self.assertIn("p.product_name", js)
        self.assertIn("p.cart_count", js)
        self.assertIn("p.purchases", js)
        self.assertIn("p.purchase_known", js)
        self.assertIn("p.exposure", js)
        self.assertIn("pkg.products", js)


class ProductsCommercialTruthV1ComposeTests(unittest.TestCase):
    def test_named_authoritative_and_missing_name_fallback(self) -> None:
        pkg = _lab_pkg()
        rows = _by_id(pkg)
        self.assertEqual(pkg["read_model_owner"], READ_MODEL_OWNER)
        self.assertEqual(pkg["read_model_schema"], PRODUCT_READ_MODEL_SCHEMA)
        self.assertEqual(pkg["counts"]["products"], 11)
        self.assertEqual(pkg["counts"]["named"], 10)
        self.assertEqual(pkg["frontend_ranking"], 0)
        self.assertEqual(pkg["frontend_fixtures"], 0)
        self.assertEqual(pkg["n_plus_one"], 0)
        amber = rows["nf-amber-night"]
        self.assertEqual(amber["product_name"], "عنبر ليلي")
        self.assertTrue(amber["name_is_merchant_title"])
        self.assertEqual(amber["price"], 149.0)
        self.assertEqual(amber["cart_count"], 4)
        self.assertEqual(amber["purchases"], 0)
        self.assertTrue(amber["purchase_known"])
        missing = rows[MISSING_NAME_PRODUCT_ID]
        self.assertEqual(missing["product_name"], MISSING_NAME_TITLE_AR)
        self.assertEqual(missing["product_identity"], MISSING_NAME_IDENTITY_AR)
        self.assertFalse(missing["name_is_merchant_title"])
        self.assertNotEqual(missing["product_name"], FORBIDDEN_MISSING_TITLE)
        self.assertNotIn(FORBIDDEN_MISSING_TITLE, json.dumps(pkg, ensure_ascii=False))

    def test_r17_stories_a_through_f(self) -> None:
        pkg = _lab_pkg(with_purchase=True)
        rows = _by_id(pkg)
        amber = rows["nf-amber-night"]
        gift = rows["nf-gift-set"]
        oud = rows["nf-oud-royal"]
        missing = rows[MISSING_NAME_PRODUCT_ID]
        # A named + carts + 0 purchases
        self.assertGreater(amber["cart_count"], 0)
        self.assertEqual(amber["purchases"], 0)
        self.assertEqual(amber["commercial_attention_state"], ATTENTION_NEEDS)
        # B purchase/revenue truth
        self.assertEqual(gift["purchases"], 2)
        self.assertEqual(gift["revenue"], 498.0)
        self.assertEqual(gift["commercial_attention_state"], ATTENTION_STABLE)
        # C product-scoped hesitation
        self.assertEqual(oud["hesitation_reason_counts"].get("shipping"), 5)
        self.assertIn("هذا المنتج", oud["hesitation_ar"])
        # D lab-synthetic exposure
        self.assertEqual(amber["exposure"]["state"], EXPOSURE_LAB_SYNTHETIC)
        self.assertEqual(amber["exposure"]["count"], 2)
        self.assertEqual(amber["exposure"]["truth_class"], VISIT_FIELD_CLASS_LAB_ONLY)
        self.assertEqual(amber["exposure"][VISIT_FIELD_NAME], 2)
        # E unavailable exposure on missing-name (0 events → not a fabricated merchant 0)
        self.assertEqual(missing["exposure"]["state"], EXPOSURE_NONE_RECORDED)
        self.assertIsNone(missing["exposure"]["count"])
        # F missing-name fixture
        self.assertEqual(missing["commercial_attention_state"], ATTENTION_INSUFFICIENT)
        self.assertEqual(pkg["unique_visitor_claim"], 0)
        self.assertFalse(pkg["real_merchant_visit_ingestion"])
        self.assertEqual(pkg["visit_field_label"], LAB_VISIT_TRUTH_CLASS)

    def test_zero_purchase_is_known_not_unknown(self) -> None:
        pkg = _lab_pkg()
        amber = _by_id(pkg)["nf-amber-night"]
        self.assertTrue(amber["purchase_known"])
        self.assertEqual(amber["purchases"], 0)
        self.assertEqual(amber["revenue"], 0.0)
        self.assertIsNone(amber["revenue_ar"])

    def test_normal_merchant_visits_are_not_stored(self) -> None:
        blob = _r17_preloaded()
        pkg = compose_products_commercial_truth_v1(
            store_slug=NORMAL_SLUG, preloaded=blob
        )
        self.assertFalse(pkg["lab_tenant"])
        self.assertEqual(pkg["query_delta"], 0)
        self.assertEqual(pkg["visit_field_label"], "NOT_STORED")
        for row in pkg["products"]:
            self.assertEqual(row["exposure"]["state"], EXPOSURE_NOT_STORED)
            self.assertIsNone(row["exposure"]["count"])
            self.assertNotIn(VISIT_FIELD_NAME, row["exposure"])
            self.assertNotEqual(row["exposure"]["count"], 0)
        painted = json.dumps(pkg, ensure_ascii=False)
        self.assertNotIn("0 زيارة", painted)
        self.assertNotIn("unique visitor", painted.lower())

    def test_store_level_hesitation_is_not_product_causation(self) -> None:
        pkg = _lab_pkg()
        painted = json.dumps(pkg, ensure_ascii=False)
        self.assertFalse(pkg["product_scoped_shipping_claim_allowed"])
        self.assertEqual(pkg["store_context"]["attribution_boundary"], "store")
        self.assertIn("دون افتراض سبب تجاري غير مثبت", pkg["store_context"]["body_ar"])
        for row in pkg["products"]:
            self.assertFalse(row["product_scoped_shipping_claim"])
        for phrase in FORBIDDEN_CAUSAL_AR:
            self.assertNotIn(phrase, painted)
        self.assertNotIn("12 customers abandoned this product", painted)
        self.assertNotIn("المنتج لا يبيع بسبب الشحن", painted)

    def test_attention_is_presentation_not_mission_ranker(self) -> None:
        pkg = _lab_pkg(with_purchase=True)
        self.assertEqual(pkg["attention_owner"], ATTENTION_OWNER)
        self.assertEqual(pkg["commercial_status_owner"], "catalog_cdc_portfolio")
        self.assertEqual(pkg["frontend_ranking"], 0)
        primary = pkg["primary"]
        self.assertEqual(primary["commercial_attention_state"], ATTENTION_NEEDS)
        ids = [p["product_id"] for p in pkg["products"]]
        self.assertIn("nf-gift-set", ids)
        gift_idx = ids.index("nf-gift-set")
        needs = [
            p
            for p in pkg["products"]
            if p["commercial_attention_state"] == ATTENTION_NEEDS
        ]
        self.assertGreater(len(needs), 0)
        self.assertLess(ids.index(needs[0]["product_id"]), gift_idx)

    def test_tenant_preloaded_isolation(self) -> None:
        lab = _lab_pkg()
        other = compose_products_commercial_truth_v1(
            store_slug=FOUNDER_SLUG,
            preloaded={"catalog": [], "carts": {}, "purchases": {}, "hesitation": {}},
        )
        self.assertEqual(lab["store_slug"], LAB_STORE_SLUG)
        self.assertEqual(other["store_slug"], FOUNDER_SLUG)
        self.assertEqual(other["counts"]["products"], 0)
        self.assertNotEqual(lab["counts"]["products"], 0)

    def test_unauthorized_products_route(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)
        r = client.get("/api/dashboard/products", follow_redirects=False)
        self.assertIn(r.status_code, (401, 302, 303))


class ProductsCommercialTruthV1LabDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fd, db_path = tempfile.mkstemp(prefix="cartflow_prd_v1_", suffix=".db")
        os.close(fd)
        cls._db_path = db_path
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
        os.environ["CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1"] = "1"
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "products-commercial-truth-v1"

        import sys

        sys.path.insert(0, str(ROOT))
        from extensions import db, init_database, remove_scoped_session
        import models  # noqa: F401

        try:
            remove_scoped_session()
            db.engine.dispose()
        except Exception:
            pass
        from schema_cart_line_snapshots_v1 import ensure_cart_line_snapshots_schema
        from schema_commercial_decision_commitment_v1 import (
            ensure_commercial_decision_commitment_schema,
            reset_commercial_decision_commitment_schema_guard_for_tests,
        )
        from schema_product_catalog_v1 import ensure_product_catalog_schema
        from schema_product_hesitation_mapping_v1 import (
            ensure_product_hesitation_mapping_schema,
        )
        from schema_product_purchase_mapping_v1 import (
            ensure_product_purchase_mapping_schema,
        )
        from schema_product_signal_events_v1 import ensure_product_signal_events_schema
        from services.live_reality_lab_v1 import (
            apply_lab_scenario_v1,
            ensure_live_reality_lab_tenant_v1,
        )

        init_database()
        db.create_all()
        reset_commercial_decision_commitment_schema_guard_for_tests()
        ensure_commercial_decision_commitment_schema(db)
        ensure_product_catalog_schema(db)
        ensure_cart_line_snapshots_schema(db)
        ensure_product_signal_events_schema(db)
        ensure_product_hesitation_mapping_schema(db)
        ensure_product_purchase_mapping_schema(db)
        ensure_live_reality_lab_tenant_v1()
        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R17_shipping_hesitation",
        )
        cls.db = db
        cls.models = models

    @classmethod
    def tearDownClass(cls) -> None:
        path = getattr(cls, "_db_path", "")
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    def test_db_compose_matches_stored_r17_truth(self) -> None:
        from models import (
            AbandonedCart,
            CartLineSnapshot,
            ProductCatalogEntry,
            ProductHesitationMapping,
            ProductPurchaseMapping,
            ProductSignalEvent,
            Store,
        )
        from services.live_reality_lab_v1.contract_v1 import LAB_SYNTHETIC_VISIT_SOURCE
        from services.product_data.product_signal_types_v1 import SIGNAL_PRODUCT_VIEWED

        store = (
            self.db.session.query(Store)
            .filter(Store.zid_store_id == LAB_STORE_SLUG)
            .first()
        )
        self.assertIsNotNone(store)
        pkg = compose_products_commercial_truth_v1(
            store_slug=LAB_STORE_SLUG, store=store
        )
        self.assertEqual(pkg["query_delta"], QUERY_COUNT_LAB)
        self.assertEqual(pkg["n_plus_one"], 0)
        self.assertTrue(pkg["lab_tenant"])
        rows = _by_id(pkg)
        catalog_n = (
            self.db.session.query(ProductCatalogEntry)
            .filter(ProductCatalogEntry.store_slug == LAB_STORE_SLUG)
            .count()
        )
        self.assertEqual(pkg["counts"]["products"], catalog_n)
        self.assertEqual(pkg["counts"]["named"], 10)
        amber = rows["nf-amber-night"]
        self.assertEqual(amber["product_name"], "عنبر ليلي")
        snap_carts = {
            r[0]
            for r in self.db.session.query(CartLineSnapshot.cart_id)
            .filter(
                CartLineSnapshot.store_slug == LAB_STORE_SLUG,
                CartLineSnapshot.product_id == "nf-amber-night",
            )
            .all()
        }
        self.assertEqual(amber["cart_count"], len(snap_carts))
        stored_value = 0.0
        for cid in snap_carts:
            cart = (
                self.db.session.query(AbandonedCart)
                .filter(
                    AbandonedCart.store_id == store.id,
                    AbandonedCart.zid_cart_id == cid,
                )
                .first()
            )
            if cart is not None:
                stored_value += float(cart.cart_value or 0)
        self.assertAlmostEqual(amber["cart_value"], stored_value, places=2)
        purch_n = (
            self.db.session.query(ProductPurchaseMapping)
            .filter(
                ProductPurchaseMapping.store_slug == LAB_STORE_SLUG,
                ProductPurchaseMapping.product_id == "nf-amber-night",
            )
            .count()
        )
        self.assertEqual(purch_n, 0)
        self.assertEqual(amber["purchases"], 0)
        self.assertTrue(amber["purchase_known"])
        hes_n = (
            self.db.session.query(ProductHesitationMapping)
            .filter(
                ProductHesitationMapping.store_slug == LAB_STORE_SLUG,
                ProductHesitationMapping.product_id == "nf-oud-royal",
            )
            .count()
        )
        self.assertGreater(hes_n, 0)
        self.assertGreater(
            sum(_by_id(pkg)["nf-oud-royal"]["hesitation_reason_counts"].values()), 0
        )
        visit_n = (
            self.db.session.query(ProductSignalEvent)
            .filter(
                ProductSignalEvent.store_slug == LAB_STORE_SLUG,
                ProductSignalEvent.source == LAB_SYNTHETIC_VISIT_SOURCE,
                ProductSignalEvent.signal_type == SIGNAL_PRODUCT_VIEWED,
            )
            .count()
        )
        self.assertGreater(visit_n, 0)
        labelled = [
            p
            for p in pkg["products"]
            if p["exposure"]["state"] == EXPOSURE_LAB_SYNTHETIC
        ]
        self.assertGreater(len(labelled), 0)
        self.assertEqual(labelled[0]["exposure"]["truth_class"], VISIT_FIELD_CLASS_LAB_ONLY)
        missing = rows[MISSING_NAME_PRODUCT_ID]
        self.assertEqual(missing["product_name"], MISSING_NAME_TITLE_AR)
        if missing["exposure"]["state"] == EXPOSURE_NONE_RECORDED:
            self.assertIsNone(missing["exposure"]["count"])

    def test_normal_slug_does_not_see_lab_rows(self) -> None:
        pkg = compose_products_commercial_truth_v1(store_slug=NORMAL_SLUG)
        self.assertEqual(pkg["counts"]["products"], 0)
        self.assertFalse(pkg["lab_tenant"])
        self.assertEqual(pkg["query_delta"], QUERY_COUNT_NORMAL)
        self.assertEqual(pkg["visit_field_label"], "NOT_STORED")


if __name__ == "__main__":
    unittest.main()
