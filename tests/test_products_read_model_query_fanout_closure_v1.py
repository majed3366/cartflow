# -*- coding: utf-8 -*-
"""
PRODUCTS_READ_MODEL_QUERY_FANOUT_V1 closure gate.

One store-scoped SQL. Products V1.2 truth unchanged. DEPLOY: NO.
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import event, text

from services.founder_production_evaluation_tenant_v1.contract_v1 import (
    FOUNDER_EVAL_STORE_SLUG,
)
from services.live_reality_lab_v1.contract_v1 import (
    LAB_STORE_SLUG,
    LAB_SYNTHETIC_VISIT_SOURCE,
    MISSING_NAME_PRODUCT_ID,
)
from services.product_data.product_signal_types_v1 import (
    FAMILY_PRODUCT_VIEW,
    SIGNAL_PRODUCT_VIEWED,
)
from services.products_commercial_truth_v1.compose_v1 import (
    compose_products_commercial_truth_v1,
)
from services.products_commercial_truth_v1.contract_v1 import (
    EXPOSURE_LAB_SYNTHETIC,
    EXPOSURE_NONE_RECORDED,
    EXPOSURE_NOT_STORED,
    MAX_PRODUCTS,
    MISSING_NAME_IDENTITY_AR,
    MISSING_NAME_TITLE_AR,
    QUERY_COUNT_LAB,
    QUERY_COUNT_NORMAL,
    READ_MODEL_OWNER,
)
from services.products_commercial_truth_v1.load_consolidated_v1 import (
    products_read_sql_v1,
)

ROOT = Path(__file__).resolve().parents[1]
NORMAL_SLUG = "acme_fanout_normal"
COLLIDE_SLUG = "acme_fanout_other"


def _interesting_sql(statement: str) -> bool:
    s = (statement or "").lower()
    return any(
        token in s
        for token in (
            "product_catalog_entries",
            "cart_line_snapshots",
            "abandoned_carts",
            "product_purchase_mappings",
            "product_hesitation_mappings",
            "product_signal_events",
        )
    )


class _SqlTrace:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.sql: list[str] = []

    def __enter__(self) -> "_SqlTrace":
        event.listen(self.engine, "before_cursor_execute", self._before)
        return self

    def __exit__(self, *args) -> None:
        event.remove(self.engine, "before_cursor_execute", self._before)

    def _before(self, conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        self.sql.append(str(statement or ""))

    @property
    def product_sql(self) -> list[str]:
        return [s for s in self.sql if _interesting_sql(s)]


def _by_id(pkg):
    return {p["product_id"]: p for p in pkg["products"]}


class ProductsReadModelQueryFanoutClosureV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fd, db_path = tempfile.mkstemp(prefix="cartflow_fanout_v1_", suffix=".db")
        os.close(fd)
        cls._db_path = db_path
        cls._prev_env = {
            key: os.environ.get(key)
            for key in (
                "DATABASE_URL",
                "CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1",
                "CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1",
                "ENV",
                "SECRET_KEY",
            )
        }
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
        os.environ["CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1"] = "1"
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "products-fanout-closure-v1"

        import sys

        sys.path.insert(0, str(ROOT))
        from extensions import db, init_database, remove_scoped_session
        import models  # noqa: F401
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
        from services.founder_production_evaluation_tenant_v1 import (
            ensure_founder_production_evaluation_tenant_v1,
        )
        from services.live_reality_lab_v1 import (
            apply_lab_scenario_v1,
            ensure_live_reality_lab_tenant_v1,
        )

        try:
            remove_scoped_session()
            db.engine.dispose()
        except Exception:
            pass
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
        ensure_founder_production_evaluation_tenant_v1()
        cls.db = db
        cls.models = models
        cls._seed_normal_and_collision_tenants()

    @classmethod
    def tearDownClass(cls) -> None:
        from extensions import db, remove_scoped_session

        try:
            remove_scoped_session()
            db.engine.dispose()
        except Exception:
            pass
        for key, val in getattr(cls, "_prev_env", {}).items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        path = getattr(cls, "_db_path", "")
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    @classmethod
    def _seed_normal_and_collision_tenants(cls) -> None:
        from models import (
            AbandonedCart,
            CartLineSnapshot,
            MerchantUser,
            ProductCatalogEntry,
            ProductHesitationMapping,
            ProductPurchaseMapping,
            ProductSignalEvent,
            Store,
        )
        from services.merchant_auth_v1 import hash_password

        now = datetime.now(timezone.utc)
        user = MerchantUser(
            email="fanout.normal@cartflow.local",
            password_hash=hash_password("Fanout-Normal-Tenant-V1!"),
            merchant_name="Fanout Normal",
        )
        cls.db.session.add(user)
        cls.db.session.flush()
        store = Store(
            zid_store_id=NORMAL_SLUG,
            merchant_user_id=int(user.id),
            widget_display_name="Fanout Normal",
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            is_active=True,
            integration_source="fanout_normal_v1",
            whatsapp_recovery_enabled=False,
        )
        cls.db.session.add(store)
        other_user = MerchantUser(
            email="fanout.other@cartflow.local",
            password_hash=hash_password("Fanout-Other-Tenant-V1!"),
            merchant_name="Fanout Other",
        )
        cls.db.session.add(other_user)
        cls.db.session.flush()
        other = Store(
            zid_store_id=COLLIDE_SLUG,
            merchant_user_id=int(other_user.id),
            widget_display_name="Fanout Other",
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            is_active=True,
            integration_source="fanout_other_v1",
            whatsapp_recovery_enabled=False,
        )
        cls.db.session.add(other)
        cls.db.session.flush()
        cls.db.session.add(
            ProductCatalogEntry(
                store_slug=NORMAL_SLUG,
                stable_identity_key="normal-soap",
                identity_tier="C",
                product_id="normal-soap",
                sku="NORMAL_SOAP",
                name="صابون عادي",
                price=25.0,
                currency="SAR",
                capture_confidence="high",
                catalog_source="fanout_test",
                first_seen_at=now,
                last_synced_at=now,
            )
        )
        cls.db.session.add(
            ProductCatalogEntry(
                store_slug=COLLIDE_SLUG,
                stable_identity_key="nf-oud-royal",
                identity_tier="C",
                product_id="nf-oud-royal",
                sku="COLLIDE_OUD",
                name="عود مستأجر آخر",
                price=10.0,
                currency="SAR",
                capture_confidence="high",
                catalog_source="fanout_test",
                first_seen_at=now,
                last_synced_at=now,
            )
        )
        cls.db.session.add(
            AbandonedCart(
                store_id=int(other.id),
                zid_cart_id="collide_cart_1",
                cart_value=9999.0,
                status="detected",
            )
        )
        cls.db.session.add(
            CartLineSnapshot(
                store_slug=COLLIDE_SLUG,
                session_id="collide-s1",
                cart_id="collide_cart_1",
                product_id="nf-oud-royal",
                name="عود مستأجر آخر",
                unit_price=10.0,
                quantity=1,
                captured_at=now,
                capture_source="fanout_test",
                capture_confidence="high",
                content_hash="collide-oud-1",
            )
        )
        cls.db.session.add(
            ProductHesitationMapping(
                store_slug=COLLIDE_SLUG,
                session_id="collide-s1",
                cart_id="collide_cart_1",
                stable_identity_key="nf-oud-royal",
                identity_tier="C",
                product_id="nf-oud-royal",
                name="عود مستأجر آخر",
                reason="shipping",
                mapping_confidence="high",
                mapping_source="fanout_test",
                captured_at=now,
                dedup_hash="collide-hes-1",
            )
        )
        cls.db.session.add(
            ProductPurchaseMapping(
                store_slug=COLLIDE_SLUG,
                session_id="collide-s1",
                cart_id="collide_cart_1",
                stable_identity_key="nf-oud-royal",
                product_id="nf-oud-royal",
                name="عود مستأجر آخر",
                quantity=9,
                unit_price=10.0,
                purchase_confidence="high",
                purchase_source="fanout_test",
                purchased_at=now,
                dedup_hash="collide-purch-1",
            )
        )
        cls.db.session.add(
            ProductSignalEvent(
                store_slug=NORMAL_SLUG,
                session_id="should-not-read",
                cart_id="",
                stable_identity_key="normal-soap",
                identity_tier="C",
                product_id="normal-soap",
                signal_family=FAMILY_PRODUCT_VIEW,
                signal_type=SIGNAL_PRODUCT_VIEWED,
                observed_at=now,
                source=LAB_SYNTHETIC_VISIT_SOURCE,
                dedup_hash="normal-must-not-count-visit",
            )
        )
        cls.db.session.commit()

    def _store(self, slug: str):
        from models import Store

        return (
            self.db.session.query(Store).filter(Store.zid_store_id == slug).first()
        )

    def test_sql_bodies_isolate_lab_exposure(self) -> None:
        normal = products_read_sql_v1(lab_tenant=False, dialect="sqlite")
        lab = products_read_sql_v1(lab_tenant=True, dialect="sqlite")
        self.assertNotIn("product_signal_events", normal.lower())
        self.assertIn("product_signal_events", lab.lower())
        self.assertIn("store_slug = :slug", normal)
        self.assertLessEqual(QUERY_COUNT_NORMAL, 1)
        self.assertLessEqual(QUERY_COUNT_LAB, 2)

    def test_lab_r17_truth_parity_and_one_statement(self) -> None:
        store = self._store(LAB_STORE_SLUG)
        self.assertIsNotNone(store)
        with _SqlTrace(self.db.engine) as traced:
            t0 = time.perf_counter()
            pkg = compose_products_commercial_truth_v1(
                store_slug=LAB_STORE_SLUG, store=store
            )
            lab_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(len(traced.product_sql), 1)
        self.assertEqual(pkg["query_delta"], QUERY_COUNT_LAB)
        self.assertEqual(pkg["n_plus_one"], 0)
        self.assertEqual(pkg["read_model_owner"], READ_MODEL_OWNER)
        self.assertEqual(pkg["frontend_ranking"], 0)
        self.assertEqual(pkg["unique_visitor_claim"], 0)
        self.assertTrue(pkg["lab_tenant"])
        self.assertEqual(pkg["counts"]["products"], 11)
        self.assertEqual(pkg["counts"]["named"], 10)
        rows = _by_id(pkg)
        oud = rows["nf-oud-royal"]
        self.assertEqual(oud["product_name"], "عود ملكي مركز")
        self.assertEqual(oud["cart_count"], 5)
        self.assertAlmostEqual(oud["cart_value"], 945.0, places=2)
        self.assertEqual(oud["purchases"], 0)
        self.assertEqual(oud["hesitation_reason_counts"].get("price"), 5)
        self.assertEqual(oud["exposure"]["state"], EXPOSURE_LAB_SYNTHETIC)
        self.assertEqual(oud["exposure"]["count"], 5)
        amber = rows["nf-amber-night"]
        self.assertEqual(amber["product_name"], "عنبر ليلي")
        self.assertEqual(amber["cart_count"], 4)
        self.assertAlmostEqual(amber["cart_value"], 596.0, places=2)
        self.assertEqual(amber["purchases"], 0)
        self.assertEqual(amber["hesitation_reason_counts"].get("shipping"), 4)
        self.assertEqual(amber["exposure"]["count"], 4)
        gift = rows["nf-gift-set"]
        self.assertEqual(gift["product_name"], "طقم العناية الفاخر")
        self.assertEqual(gift["cart_count"], 4)
        self.assertAlmostEqual(gift["cart_value"], 996.0, places=2)
        self.assertEqual(gift["purchases"], 0)
        self.assertEqual(gift["exposure"]["state"], EXPOSURE_NONE_RECORDED)
        self.assertIsNone(gift["exposure"]["count"])
        missing = rows[MISSING_NAME_PRODUCT_ID]
        self.assertEqual(missing["product_name"], MISSING_NAME_TITLE_AR)
        self.assertEqual(missing["product_identity"], MISSING_NAME_IDENTITY_AR)
        self.assertTrue(missing["missing_name"])
        type(self).lab_wall_ms = lab_ms
        type(self).lab_sql_n = len(traced.product_sql)

    def test_normal_merchant_no_lab_query_unknown_exposure(self) -> None:
        store = self._store(NORMAL_SLUG)
        with _SqlTrace(self.db.engine) as traced:
            t0 = time.perf_counter()
            pkg = compose_products_commercial_truth_v1(
                store_slug=NORMAL_SLUG, store=store
            )
            normal_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(len(traced.product_sql), 1)
        self.assertNotIn("product_signal_events", traced.product_sql[0].lower())
        self.assertEqual(pkg["query_delta"], QUERY_COUNT_NORMAL)
        self.assertFalse(pkg["lab_tenant"])
        self.assertEqual(pkg["counts"]["products"], 1)
        soap = _by_id(pkg)["normal-soap"]
        self.assertEqual(soap["product_name"], "صابون عادي")
        self.assertEqual(soap["exposure"]["state"], EXPOSURE_NOT_STORED)
        self.assertIsNone(soap["exposure"]["count"])
        self.assertNotIn("nf-oud-royal", _by_id(pkg))
        type(self).normal_wall_ms = normal_ms

    def test_founder_eval_is_not_lab_and_sees_no_lab_skus(self) -> None:
        store = self._store(FOUNDER_EVAL_STORE_SLUG)
        with _SqlTrace(self.db.engine) as traced:
            pkg = compose_products_commercial_truth_v1(
                store_slug=FOUNDER_EVAL_STORE_SLUG, store=store
            )
        self.assertEqual(len(traced.product_sql), 1)
        self.assertNotIn("product_signal_events", traced.product_sql[0].lower())
        self.assertFalse(pkg["lab_tenant"])
        ids = set(_by_id(pkg))
        self.assertNotIn("nf-oud-royal", ids)
        self.assertNotIn("nf-amber-night", ids)
        for card in pkg["products"]:
            self.assertEqual(card["exposure"]["state"], EXPOSURE_NOT_STORED)

    def test_cross_tenant_collision_does_not_leak(self) -> None:
        lab = compose_products_commercial_truth_v1(
            store_slug=LAB_STORE_SLUG, store=self._store(LAB_STORE_SLUG)
        )
        other = compose_products_commercial_truth_v1(
            store_slug=COLLIDE_SLUG, store=self._store(COLLIDE_SLUG)
        )
        oud = _by_id(lab)["nf-oud-royal"]
        self.assertEqual(oud["cart_count"], 5)
        self.assertAlmostEqual(oud["cart_value"], 945.0, places=2)
        self.assertEqual(oud["purchases"], 0)
        collide = _by_id(other)["nf-oud-royal"]
        self.assertEqual(collide["product_name"], "عود مستأجر آخر")
        self.assertEqual(collide["cart_count"], 1)
        self.assertAlmostEqual(collide["cart_value"], 9999.0, places=2)
        self.assertEqual(collide["purchases"], 1)
        self.assertEqual(collide["revenue"], 90.0)

    def test_empty_store_one_statement(self) -> None:
        with _SqlTrace(self.db.engine) as traced:
            pkg = compose_products_commercial_truth_v1(store_slug="empty_fanout_store")
        self.assertEqual(len(traced.product_sql), 1)
        self.assertEqual(pkg["counts"]["products"], 0)
        self.assertEqual(pkg["n_plus_one"], 0)

    def test_failure_shapes_stay_bounded(self) -> None:
        from models import (
            AbandonedCart,
            CartLineSnapshot,
            ProductCatalogEntry,
            ProductHesitationMapping,
            ProductPurchaseMapping,
        )

        now = datetime.now(timezone.utc)
        slug = "fanout_failure_shapes"
        self.db.session.add(
            ProductCatalogEntry(
                store_slug=slug,
                stable_identity_key="only-catalog",
                identity_tier="C",
                product_id="only-catalog",
                name="فقط كتالوج",
                price=12.0,
                currency="SAR",
                capture_confidence="high",
                catalog_source="fanout_test",
                first_seen_at=now,
                last_synced_at=now,
            )
        )
        self.db.session.add(
            ProductCatalogEntry(
                store_slug=slug,
                stable_identity_key="cart-no-purchase",
                identity_tier="C",
                product_id="cart-no-purchase",
                name="سلة بلا شراء",
                price=40.0,
                currency="SAR",
                capture_confidence="high",
                catalog_source="fanout_test",
                first_seen_at=now,
                last_synced_at=now,
            )
        )
        self.db.session.add(
            AbandonedCart(
                zid_cart_id="fail_cart_a",
                cart_value=40.0,
                status="detected",
            )
        )
        self.db.session.add(
            CartLineSnapshot(
                store_slug=slug,
                session_id="fail-s1",
                cart_id="fail_cart_a",
                product_id="cart-no-purchase",
                captured_at=now,
                capture_source="fanout_test",
                capture_confidence="high",
                content_hash="fail-cart-a",
            )
        )
        self.db.session.add(
            CartLineSnapshot(
                store_slug=slug,
                session_id="fail-s1b",
                cart_id="fail_cart_a",
                product_id="cart-no-purchase",
                captured_at=now,
                capture_source="fanout_test",
                capture_confidence="high",
                content_hash="fail-cart-a-dup-line",
            )
        )
        self.db.session.add(
            ProductCatalogEntry(
                store_slug=slug,
                stable_identity_key="purchase-no-hes",
                identity_tier="C",
                product_id="purchase-no-hes",
                name="شراء بلا تردد",
                price=8.0,
                currency="SAR",
                capture_confidence="high",
                catalog_source="fanout_test",
                first_seen_at=now,
                last_synced_at=now,
            )
        )
        self.db.session.add(
            ProductPurchaseMapping(
                store_slug=slug,
                session_id="fail-s2",
                cart_id="fail_buy_1",
                stable_identity_key="purchase-no-hes",
                product_id="purchase-no-hes",
                quantity=2,
                unit_price=8.0,
                purchase_confidence="high",
                purchase_source="fanout_test",
                purchased_at=now,
                dedup_hash="fail-purch-1",
            )
        )
        self.db.session.add(
            ProductPurchaseMapping(
                store_slug=slug,
                session_id="fail-s2b",
                cart_id="fail_buy_1",
                stable_identity_key="purchase-no-hes",
                product_id="purchase-no-hes",
                quantity=2,
                unit_price=8.0,
                purchase_confidence="high",
                purchase_source="fanout_test",
                purchased_at=now,
                dedup_hash="fail-purch-1-dup-risk",
            )
        )
        self.db.session.add(
            ProductCatalogEntry(
                store_slug=slug,
                stable_identity_key="hes-no-purchase",
                identity_tier="C",
                product_id="hes-no-purchase",
                name="تردد بلا شراء",
                price=15.0,
                currency="SAR",
                capture_confidence="high",
                catalog_source="fanout_test",
                first_seen_at=now,
                last_synced_at=now,
            )
        )
        self.db.session.add(
            ProductHesitationMapping(
                store_slug=slug,
                session_id="fail-s3",
                cart_id="fail_h1",
                stable_identity_key="hes-no-purchase",
                identity_tier="C",
                product_id="hes-no-purchase",
                reason="price",
                mapping_confidence="high",
                mapping_source="fanout_test",
                captured_at=now,
                dedup_hash="fail-hes-price",
            )
        )
        self.db.session.add(
            ProductHesitationMapping(
                store_slug=slug,
                session_id="fail-s4",
                cart_id="fail_h2",
                stable_identity_key="hes-no-purchase",
                identity_tier="C",
                product_id="hes-no-purchase",
                reason="shipping",
                mapping_confidence="high",
                mapping_source="fanout_test",
                captured_at=now,
                dedup_hash="fail-hes-ship",
            )
        )
        self.db.session.add(
            ProductCatalogEntry(
                store_slug=slug,
                stable_identity_key="blank-name",
                identity_tier="C",
                product_id="blank-name",
                name="",
                price=3.0,
                currency="SAR",
                capture_confidence="high",
                catalog_source="fanout_test",
                first_seen_at=now,
                last_synced_at=now,
            )
        )
        self.db.session.commit()
        with _SqlTrace(self.db.engine) as traced:
            pkg = compose_products_commercial_truth_v1(store_slug=slug)
        self.assertEqual(len(traced.product_sql), 1)
        rows = _by_id(pkg)
        self.assertEqual(rows["only-catalog"]["cart_count"], 0)
        self.assertEqual(rows["only-catalog"]["purchases"], 0)
        cart_only = rows["cart-no-purchase"]
        self.assertEqual(cart_only["cart_count"], 1)
        self.assertAlmostEqual(cart_only["cart_value"], 40.0, places=2)
        self.assertEqual(cart_only["purchases"], 0)
        bought = rows["purchase-no-hes"]
        self.assertEqual(bought["purchases"], 2)
        self.assertAlmostEqual(bought["revenue"], 32.0, places=2)
        self.assertEqual(bought["hesitation_reason_counts"], {})
        hes = rows["hes-no-purchase"]
        self.assertEqual(hes["purchases"], 0)
        self.assertEqual(hes["hesitation_reason_counts"].get("price"), 1)
        self.assertEqual(hes["hesitation_reason_counts"].get("shipping"), 1)
        blank = rows["blank-name"]
        self.assertEqual(blank["product_name"], MISSING_NAME_TITLE_AR)
        self.assertTrue(blank["missing_name"])

    def test_scale_remains_one_statement_and_capped(self) -> None:
        from models import (
            AbandonedCart,
            CartLineSnapshot,
            ProductCatalogEntry,
            ProductHesitationMapping,
            ProductPurchaseMapping,
        )

        now = datetime.now(timezone.utc)
        measurements: dict[int, dict[str, float]] = {}
        for n in (11, 100, 500, 1000):
            slug = f"fanout_scale_{n}"
            rows = []
            for i in range(n):
                pid = f"scale-{n}-{i:04d}"
                rows.append(
                    ProductCatalogEntry(
                        store_slug=slug,
                        stable_identity_key=pid,
                        identity_tier="C",
                        product_id=pid,
                        name=f"منتج {i}",
                        price=10.0 + i,
                        currency="SAR",
                        capture_confidence="high",
                        catalog_source="fanout_scale",
                        first_seen_at=now,
                        last_synced_at=now,
                    )
                )
            self.db.session.add_all(rows)
            hot = [f"scale-{n}-{i:04d}" for i in range(min(20, n))]
            for i, pid in enumerate(hot):
                for k in range(8):
                    cid = f"{slug}_c_{i}_{k}"
                    self.db.session.add(
                        AbandonedCart(
                            zid_cart_id=cid,
                            cart_value=float(11 + k),
                            status="detected",
                        )
                    )
                    self.db.session.add(
                        CartLineSnapshot(
                            store_slug=slug,
                            session_id=f"{slug}-s-{i}-{k}",
                            cart_id=cid,
                            product_id=pid,
                            captured_at=now,
                            capture_source="fanout_scale",
                            capture_confidence="high",
                            content_hash=f"{slug}-h-{i}-{k}",
                        )
                    )
                    self.db.session.add(
                        ProductPurchaseMapping(
                            store_slug=slug,
                            session_id=f"{slug}-p-{i}-{k}",
                            cart_id=cid,
                            stable_identity_key=pid,
                            product_id=pid,
                            quantity=1,
                            unit_price=float(11 + k),
                            purchase_confidence="high",
                            purchase_source="fanout_scale",
                            purchased_at=now,
                            dedup_hash=f"{slug}-p-{i}-{k}",
                        )
                    )
                    self.db.session.add(
                        ProductHesitationMapping(
                            store_slug=slug,
                            session_id=f"{slug}-hs-{i}-{k}",
                            cart_id=cid,
                            stable_identity_key=pid,
                            identity_tier="C",
                            product_id=pid,
                            reason="price" if k % 2 == 0 else "shipping",
                            mapping_confidence="high",
                            mapping_source="fanout_scale",
                            captured_at=now,
                            dedup_hash=f"{slug}-hs-{i}-{k}",
                        )
                    )
            self.db.session.commit()
            with _SqlTrace(self.db.engine) as traced:
                t0 = time.perf_counter()
                pkg = compose_products_commercial_truth_v1(store_slug=slug)
                ms = (time.perf_counter() - t0) * 1000.0
            self.assertEqual(len(traced.product_sql), 1, msg=f"n={n} n+1 risk")
            self.assertEqual(pkg["n_plus_one"], 0)
            self.assertLessEqual(pkg["counts"]["products"], MAX_PRODUCTS)
            self.assertEqual(pkg["counts"]["products"], min(n, MAX_PRODUCTS))
            plan_rows = self.db.session.execute(
                text("EXPLAIN QUERY PLAN " + products_read_sql_v1(lab_tenant=False)),
                {
                    "slug": slug,
                    "store_id": 0,
                    "max_products": MAX_PRODUCTS,
                    "max_cart_pairs": 400,
                    "lab_source": "",
                    "lab_signal": "",
                },
            ).fetchall()
            plan = " ".join(str(r) for r in plan_rows).lower()
            self.assertNotIn("nested loop", plan)
            measurements[n] = {
                "wall_ms": round(ms, 3),
                "sql": 1,
                "result_rows": pkg["counts"]["products"],
            }
        type(self).scale_measurements = measurements
        self.assertLess(
            measurements[1000]["wall_ms"],
            max(250.0, measurements[11]["wall_ms"] * 80),
        )


if __name__ == "__main__":
    unittest.main()
