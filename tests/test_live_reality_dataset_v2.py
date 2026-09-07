# -*- coding: utf-8 -*-
"""Live Reality Dataset V2 — reconstruction tests on production lineage."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

V2_SCENARIOS = (
    "R13_sent_recovery_no_completion",
    "R14_sent_recovery_later_purchased",
    "R15_zero_visits",
    "R16_visits_no_carts",
    "R17_shipping_hesitation",
    "R18_delivery_duration_hesitation",
    "R19_cart_interest_weak_purchase",
    "R20_product_confidence",
    "R21_price_hesitation",
    "R22_healthy_product",
    "R23_unresolved_recovery",
    "R24_resolved_recovery",
)


class LiveRealityDatasetV2StaticTests(unittest.TestCase):
    def test_catalog_has_ten_named_products_and_one_fixture(self) -> None:
        from services.live_reality_lab_v1.catalog_v2 import (
            NAMED_PRODUCTS,
            cart_product_sequence,
            named_product_count,
        )
        from services.live_reality_lab_v1.contract_v1 import MISSING_NAME_PRODUCT_ID

        self.assertEqual(named_product_count(), 10)
        self.assertEqual(len(cart_product_sequence()), 38)
        self.assertEqual(cart_product_sequence().count(MISSING_NAME_PRODUCT_ID), 1)
        for _pid, name, price, _slots in NAMED_PRODUCTS:
            self.assertTrue(name.strip())
            self.assertNotIn("منتج X", name)
            self.assertGreater(float(price), 0)

    def test_dashboard_does_not_auto_seed(self) -> None:
        pages = (ROOT / "routes" / "merchant_pages.py").read_text(encoding="utf-8")
        self.assertNotIn("apply_lab_scenario", pages)
        self.assertNotIn("seed_dataset_v2", pages)
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        # Router is registered; apply is not invoked from dashboard handlers.
        self.assertIn("live_reality_lab_v1_router", main)
        self.assertNotIn("apply_lab_scenario_v1(", main)
        for name in (
            "merchant_dashboard_lazy.js",
            "merchant_intelligence_carts_v1.js",
        ):
            path = ROOT / "static" / name
            if path.exists():
                blob = path.read_text(encoding="utf-8")
                self.assertNotIn("seed_dataset_v2", blob)
                self.assertNotIn("/api/live-reality-lab/v1/apply", blob)

    def test_no_lab_ranker_or_scheduler_in_v2_seed(self) -> None:
        seed = (ROOT / "services" / "live_reality_lab_v1" / "seed_v2.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("lab_ranker", seed)
        self.assertNotIn("recovery_db_due_scanner", seed)
        self.assertNotIn("openai", seed.lower())
        self.assertNotIn("anthropic", seed.lower())

    def test_query_param_is_assertion_only(self) -> None:
        routes = (ROOT / "routes" / "live_reality_lab_v1.py").read_text(encoding="utf-8")
        self.assertIn("assertion-only", routes)
        self.assertIn("live_reality_lab_tenant_mismatch", routes)

    def test_json_boolean_contract_helpers(self) -> None:
        from json_response import j

        payload = j({"ok": True, "ready": False})
        body = json.loads(payload.body.decode("utf-8"))
        self.assertIs(body["ok"], True)
        self.assertIs(body["ready"], False)
        self.assertNotIsInstance(body["ok"], str)

    def test_four_distinct_decision_kinds_not_twelve(self) -> None:
        from services.live_reality_lab_v1.dataset_v2 import scenario_manifests_v2

        kinds: set[str] = set()
        for manifest in scenario_manifests_v2().values():
            family = manifest.get("expected_commercial_family")
            lane = manifest.get("expected_operational_lane")
            kind = str(family or lane or "")
            if kind == "product_confidence_quality":
                kind = "product_confidence"
            if kind == "wait_insufficient_evidence":
                kind = "wait"
            kinds.add(kind)
        self.assertEqual(
            kinds,
            {
                "wait",
                "shipping_friction",
                "product_confidence",
                "price_hesitation",
            },
        )
        self.assertEqual(len(kinds), 4)
        self.assertEqual(len(V2_SCENARIOS), 12)

    def test_col_ogl_home_do_not_treat_lab_visits_as_merchant_truth(self) -> None:
        paths = (
            ROOT / "services" / "commercial_opportunity_layer_v1" / "compose_v1.py",
            ROOT / "services" / "operational_guidance_v1" / "compose_v1.py",
            ROOT / "static" / "merchant_ui_v2_home.js",
            ROOT / "static" / "merchant_ui_v2_workspace.js",
            ROOT / "static" / "merchant_ui_v2_carts.js",
            ROOT / "routes" / "merchant_pages.py",
        )
        forbidden = (
            "live_reality_lab_v2_synthetic_visit",
            "LAB-SYNTHETIC PRODUCTION-SHAPED VISIT TRUTH",
            "product_viewed",
        )
        for path in paths:
            if not path.exists():
                continue
            blob = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, blob, msg=str(path))


class LiveRealityDatasetV2IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fd, db_path = tempfile.mkstemp(prefix="cartflow_pytest_lrd_v2_", suffix=".db")
        os.close(fd)
        cls._db_path = db_path
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
        os.environ["CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1"] = "1"
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "live-reality-dataset-v2"

        import sys

        sys.path.insert(0, str(ROOT))
        from extensions import db, init_database, remove_scoped_session
        import models  # noqa: F401
        try:
            remove_scoped_session()
            db.engine.dispose()
        except Exception:
            pass
        from schema_commercial_decision_commitment_v1 import (
            ensure_commercial_decision_commitment_schema,
            reset_commercial_decision_commitment_schema_guard_for_tests,
        )
        from schema_cart_line_snapshots_v1 import (
            ensure_cart_line_snapshots_schema,
        )
        from schema_product_catalog_v1 import ensure_product_catalog_schema
        from schema_product_signal_events_v1 import (
            ensure_product_signal_events_schema,
        )
        from services.live_reality_lab_v1 import ensure_live_reality_lab_tenant_v1
        from services.founder_evaluation_reality_v1.seed_v1 import (
            seed_founder_evaluation_tenants_v1,
        )
        from services.founder_production_evaluation_tenant_v1.ensure_v1 import (
            ensure_founder_production_evaluation_tenant_v1,
        )

        init_database()
        from sqlalchemy import event

        @event.listens_for(db.engine, "connect")
        def _sqlite_pragma(dbapi_conn, _rec):  # noqa: ANN001
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=30000")
            cur.close()

        db.create_all()
        reset_commercial_decision_commitment_schema_guard_for_tests()
        ensure_commercial_decision_commitment_schema(db)
        ensure_product_catalog_schema(db)
        ensure_cart_line_snapshots_schema(db)
        ensure_product_signal_events_schema(db)
        seed_founder_evaluation_tenants_v1(reset=True)
        ensure_founder_production_evaluation_tenant_v1()
        ensure_live_reality_lab_tenant_v1()
        cls.db = db

    @classmethod
    def tearDownClass(cls) -> None:
        path = getattr(cls, "_db_path", "")
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
            for suffix in ("-wal", "-shm"):
                extra = path + suffix
                if os.path.exists(extra):
                    try:
                        os.remove(extra)
                    except OSError:
                        pass

    def test_r13_through_r24_verify(self) -> None:
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            apply_lab_scenario_v1,
            verify_lab_scenario_v1,
        )

        failures = []
        for sid in V2_SCENARIOS:
            applied = apply_lab_scenario_v1(
                authenticated_store_slug=LAB_STORE_SLUG, scenario_id=sid
            )
            self.assertTrue(applied.get("ok"), msg=sid)
            self.assertIs(applied.get("ok"), True)
            verified = verify_lab_scenario_v1(
                authenticated_store_slug=LAB_STORE_SLUG, scenario_id=sid
            )
            if not verified.get("ok"):
                failures.append((sid, verified.get("checks")))
        self.assertEqual(failures, [], msg=str(failures))

    def test_r17_col_ogl_catalog_pipeline(self) -> None:
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            apply_lab_scenario_v1,
            verify_lab_scenario_v1,
        )

        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R17_shipping_hesitation",
        )
        verified = verify_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R17_shipping_hesitation",
        )
        self.assertTrue(verified.get("ok"), msg=str(verified.get("checks")))
        obs = verified.get("observed") or {}
        self.assertEqual(obs.get("catalog_primary"), "shipping_friction")
        self.assertEqual(obs.get("commercial_family"), "shipping_friction")
        self.assertEqual(obs.get("operational_lane"), "shipping_friction")
        self.assertEqual(obs.get("portfolio_active_count"), 0)

    def test_r18_same_family_delivery_reason(self) -> None:
        from models import CartRecoveryReason
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            apply_lab_scenario_v1,
            verify_lab_scenario_v1,
        )

        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R18_delivery_duration_hesitation",
        )
        verified = verify_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R18_delivery_duration_hesitation",
        )
        self.assertTrue(verified.get("ok"), msg=str(verified.get("checks")))
        self.assertEqual(
            (verified.get("observed") or {}).get("catalog_primary"),
            "shipping_friction",
        )
        delivery_n = (
            self.db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == LAB_STORE_SLUG,
                CartRecoveryReason.reason == "delivery",
            )
            .count()
        )
        self.assertGreaterEqual(delivery_n, 12)

    def test_named_products_and_missing_name_fixture(self) -> None:
        from models import AbandonedCart, ProductCatalogEntry
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            apply_lab_scenario_v1,
        )
        from services.live_reality_lab_v1.contract_v1 import MISSING_NAME_PRODUCT_ID
        from services.product_data.product_identity_authenticity_v1 import (
            unresolved_product_identity_ar,
        )

        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R17_shipping_hesitation",
        )
        names = [
            r.name
            for r in self.db.session.query(ProductCatalogEntry)
            .filter(ProductCatalogEntry.store_slug == LAB_STORE_SLUG)
            .all()
        ]
        named = [n for n in names if n]
        self.assertEqual(len(named), 10)
        missing = [
            r
            for r in self.db.session.query(ProductCatalogEntry)
            .filter(
                ProductCatalogEntry.store_slug == LAB_STORE_SLUG,
                ProductCatalogEntry.product_id == MISSING_NAME_PRODUCT_ID,
            )
            .all()
        ]
        self.assertEqual(len(missing), 1)
        self.assertFalse((missing[0].name or "").strip())
        carts = (
            self.db.session.query(AbandonedCart)
            .filter(AbandonedCart.zid_cart_id.like("lrl_v2_%"))
            .all()
        )
        self.assertEqual(len(carts), 38)
        raw_blob = " ".join(str(c.raw_payload or "") for c in carts)
        self.assertNotIn(unresolved_product_identity_ar(), raw_blob)
        self.assertIn("عود ملكي مركز", raw_blob)

    def test_recovery_and_purchase_truth(self) -> None:
        from models import CartRecoveryLog, PurchaseTruthRecord
        from services.live_reality_lab_v1 import LAB_STORE_SLUG, apply_lab_scenario_v1

        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R14_sent_recovery_later_purchased",
        )
        sent = (
            self.db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.store_slug == LAB_STORE_SLUG)
            .count()
        )
        purchased = (
            self.db.session.query(PurchaseTruthRecord)
            .filter(PurchaseTruthRecord.store_slug == LAB_STORE_SLUG)
            .count()
        )
        self.assertGreaterEqual(sent, 8)
        self.assertGreaterEqual(purchased, 8)

    def test_lab_synthetic_visits_are_labeled(self) -> None:
        from models import ProductSignalEvent
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            LAB_SYNTHETIC_VISIT_SOURCE,
            apply_lab_scenario_v1,
        )
        from services.product_data.product_signal_types_v1 import SIGNAL_PRODUCT_VIEWED

        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R16_visits_no_carts",
        )
        rows = (
            self.db.session.query(ProductSignalEvent)
            .filter(ProductSignalEvent.store_slug == LAB_STORE_SLUG)
            .all()
        )
        self.assertGreaterEqual(len(rows), 24)
        for row in rows:
            if row.signal_type == SIGNAL_PRODUCT_VIEWED:
                self.assertEqual(row.source, LAB_SYNTHETIC_VISIT_SOURCE)

    def test_r15_has_zero_visits(self) -> None:
        from models import ProductSignalEvent
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            LAB_SYNTHETIC_VISIT_SOURCE,
            apply_lab_scenario_v1,
        )

        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R15_zero_visits",
        )
        visits = (
            self.db.session.query(ProductSignalEvent)
            .filter(
                ProductSignalEvent.store_slug == LAB_STORE_SLUG,
                ProductSignalEvent.source == LAB_SYNTHETIC_VISIT_SOURCE,
            )
            .count()
        )
        self.assertEqual(visits, 0)

    def test_cross_tenant_reset_protection(self) -> None:
        from models import CartRecoveryReason
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            apply_lab_scenario_v1,
            reset_lab_tenant_data_v1,
        )

        self.db.session.add(
            CartRecoveryReason(
                store_slug="cf_founder_evaluation",
                session_id="protect-v2",
                reason="quality",
                source="founder_production_evaluation_v1",
            )
        )
        self.db.session.commit()
        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R21_price_hesitation",
        )
        reset_lab_tenant_data_v1(authenticated_store_slug=LAB_STORE_SLUG)
        foreign = (
            self.db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == "cf_founder_evaluation",
                CartRecoveryReason.session_id == "protect-v2",
            )
            .count()
        )
        self.assertEqual(foreign, 1)

    def test_foreign_tenant_denied(self) -> None:
        from services.live_reality_lab_v1 import apply_lab_scenario_v1

        with self.assertRaises(ValueError) as ctx:
            apply_lab_scenario_v1(
                authenticated_store_slug="demo",
                scenario_id="R17_shipping_hesitation",
            )
        self.assertIn("unauthorized", str(ctx.exception))

    def test_side_effects_still_blocked(self) -> None:
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            lab_blocks_external_side_effects,
        )

        self.assertTrue(lab_blocks_external_side_effects(store_slug=LAB_STORE_SLUG))

    def test_enum_copy_not_leaked_in_col(self) -> None:
        from services.live_reality_lab_v1 import LAB_STORE_SLUG, apply_lab_scenario_v1

        applied = apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R17_shipping_hesitation",
        )
        blob = json.dumps(applied.get("observed") or {}, ensure_ascii=False)
        self.assertNotIn("shipping_cost", blob)
        col = ((applied.get("observed") or {}).get("catalog_primary"))
        self.assertEqual(col, "shipping_friction")

    def test_v1_r2_still_passes(self) -> None:
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            SCENARIO_R2,
            apply_lab_scenario_v1,
            verify_lab_scenario_v1,
        )

        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R2
        )
        verified = verify_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R2
        )
        self.assertTrue(verified.get("ok"), msg=str(verified.get("checks")))

    def test_deny_unauthenticated_and_foreign_tenants(self) -> None:
        from services.live_reality_lab_v1 import (
            apply_lab_scenario_v1,
            reset_lab_tenant_data_v1,
        )

        for slug in ("", "demo", "cf_founder_evaluation", "normal-merchant", "spoofed"):
            with self.assertRaises(ValueError) as ctx:
                apply_lab_scenario_v1(
                    authenticated_store_slug=slug,
                    scenario_id="R17_shipping_hesitation",
                )
            self.assertIn("unauthorized", str(ctx.exception))
            with self.assertRaises(ValueError):
                reset_lab_tenant_data_v1(authenticated_store_slug=slug)

    def test_production_pipeline_surfaces_on_apply(self) -> None:
        from services.live_reality_lab_v1 import LAB_STORE_SLUG, apply_lab_scenario_v1

        applied = apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R17_shipping_hesitation",
        )
        self.assertTrue(applied.get("ok"))
        obs = applied.get("observed") or {}
        self.assertEqual(obs.get("catalog_primary"), "shipping_friction")
        self.assertEqual(obs.get("operational_lane"), "shipping_friction")
        self.assertEqual(obs.get("portfolio_active_count"), 0)
        self.assertIsInstance(applied.get("snapshot_rebuild"), dict)

    def test_queuepool_and_scheduler_untouched(self) -> None:
        apply_src = (ROOT / "services" / "live_reality_lab_v1" / "apply_v1.py").read_text(
            encoding="utf-8"
        )
        seed_src = (ROOT / "services" / "live_reality_lab_v1" / "seed_v2.py").read_text(
            encoding="utf-8"
        )
        ext = (ROOT / "extensions.py").read_text(encoding="utf-8")
        for blob in (apply_src, seed_src):
            self.assertNotIn("pool_size", blob)
            self.assertNotIn("recovery_db_due_scanner", blob)
        self.assertIn('["poolclass"]=NullPool', ext.replace(" ", ""))

    def test_lab_synthetic_visits_do_not_leak_to_other_tenants(self) -> None:
        from models import ProductSignalEvent
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            LAB_SYNTHETIC_VISIT_SOURCE,
            apply_lab_scenario_v1,
        )
        from services.product_data.product_signal_types_v1 import SIGNAL_PRODUCT_VIEWED

        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG,
            scenario_id="R16_visits_no_carts",
        )
        lab_visits = (
            self.db.session.query(ProductSignalEvent)
            .filter(
                ProductSignalEvent.store_slug == LAB_STORE_SLUG,
                ProductSignalEvent.source == LAB_SYNTHETIC_VISIT_SOURCE,
                ProductSignalEvent.signal_type == SIGNAL_PRODUCT_VIEWED,
            )
            .count()
        )
        self.assertGreaterEqual(lab_visits, 24)
        leaked = (
            self.db.session.query(ProductSignalEvent)
            .filter(
                ProductSignalEvent.store_slug != LAB_STORE_SLUG,
                ProductSignalEvent.source == LAB_SYNTHETIC_VISIT_SOURCE,
            )
            .count()
        )
        self.assertEqual(leaked, 0)
        for foreign in ("demo", "cf_founder_evaluation", "normal-merchant"):
            n = (
                self.db.session.query(ProductSignalEvent)
                .filter(
                    ProductSignalEvent.store_slug == foreign,
                    ProductSignalEvent.signal_type == SIGNAL_PRODUCT_VIEWED,
                )
                .count()
            )
            self.assertEqual(n, 0, msg=foreign)


if __name__ == "__main__":
    unittest.main()
