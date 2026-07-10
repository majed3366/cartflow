# -*- coding: utf-8 -*-
"""Demo Commerce Lab V1 — Scenario 1 runner tests (P2)."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import PurchaseTruthRecord, Store
from services.demo_lab_reset_v1 import (
    LAB_CUSTOMER_PHONE,
    LAB_RECOVERY_KEY,
    LAB_STORE_SLUG,
    lab_reset_v1,
)
from services.demo_lab_scenario1_v1 import (
    LAB_PRODUCT_PRICE,
    SCENARIO_ID,
    run_lab_scenario1_duplicate_purchase_probe,
    run_lab_scenario1_v1,
    validate_lab_scenario1_scope,
)
from services.demo_sandbox_catalog import merchant_catalog_json_string
from tests.test_recovery_isolation import _reset_recovery_memory


class LabScenario1GateTests(unittest.TestCase):
    def test_rejects_non_demo_store(self) -> None:
        out = run_lab_scenario1_v1(store_slug="acme-store")
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "lab_scenario1_rejected")
        self.assertEqual(out.get("reject_reason"), "store_slug_must_be_demo")

    def test_rejects_demo2(self) -> None:
        out = run_lab_scenario1_v1(store_slug="demo2")
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("reject_reason"), "store_slug_must_be_demo")

    def test_rejects_merchant_activation(self) -> None:
        out = run_lab_scenario1_v1(store_slug="demo", merchant_activation=True)
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("reject_reason"), "merchant_activation_forbidden")

    def test_validate_scope_ok_for_demo(self) -> None:
        self.assertIsNone(
            validate_lab_scenario1_scope(store_slug="demo", merchant_activation=False)
        )


class LabScenario1RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(app)
        db.create_all()
        self.phone = LAB_CUSTOMER_PHONE
        st = db.session.query(Store).filter(Store.zid_store_id == LAB_STORE_SLUG).first()
        if st is None:
            st = Store(zid_store_id=LAB_STORE_SLUG)
            db.session.add(st)
        st.cf_product_catalog_json = merchant_catalog_json_string()
        db.session.commit()

        # Foreign merchant row must survive Lab runs
        other = db.session.query(Store).filter(Store.zid_store_id == "merchant-x").first()
        if other is None:
            other = Store(zid_store_id="merchant-x")
            db.session.add(other)
            db.session.flush()
        kept = (
            db.session.query(PurchaseTruthRecord)
            .filter(PurchaseTruthRecord.recovery_key == "merchant-x:keep-me")
            .first()
        )
        if kept is None:
            now = datetime.now(timezone.utc)
            db.session.add(
                PurchaseTruthRecord(
                    recovery_key="merchant-x:keep-me",
                    store_slug="merchant-x",
                    session_id="s_keep",
                    cart_id="cf_cart_keep",
                    purchase_detected=True,
                    purchase_time=now,
                    purchase_source="prod",
                    customer_phone="966500000001",
                )
            )
        db.session.commit()

    def tearDown(self) -> None:
        db.session.rollback()
        try:
            lab_reset_v1(store_slug=LAB_STORE_SLUG, cf_test_phone=self.phone)
        except Exception:  # noqa: BLE001
            db.session.rollback()
        db.session.query(PurchaseTruthRecord).filter(
            PurchaseTruthRecord.store_slug == "merchant-x"
        ).delete(synchronize_session=False)
        db.session.commit()
        _reset_recovery_memory()

    def test_full_scenario_pass(self) -> None:
        out = run_lab_scenario1_v1(
            store_slug=LAB_STORE_SLUG,
            cf_test_phone=self.phone,
            client=self.client,
        )
        self.assertTrue(out.get("ok"), out)
        self.assertTrue(out.get("pass"), out)
        self.assertEqual(out.get("scenario_id"), SCENARIO_ID)
        self.assertEqual(out["identity"]["recovery_key"], LAB_RECOVERY_KEY)
        self.assertEqual(
            (out.get("recovered_purchase") or {}).get("amount_sar"),
            LAB_PRODUCT_PRICE,
        )
        asserts = out.get("truth_assertions") or {}
        self.assertTrue(asserts.get("ok"), asserts)
        pulse = out.get("pulse_payload") or {}
        self.assertTrue((pulse.get("sources") or {}).get("commerce_signals_used"))
        self.assertEqual(pulse.get("fork"), "leave")
        cart = out.get("cart_page_state") or {}
        self.assertTrue(cart.get("completed"))
        self.assertEqual(cart.get("cart_value"), LAB_PRODUCT_PRICE)

        kept = (
            db.session.query(PurchaseTruthRecord)
            .filter(PurchaseTruthRecord.recovery_key == "merchant-x:keep-me")
            .first()
        )
        self.assertIsNotNone(kept)

    def test_reset_then_rerun_equivalent_outcome(self) -> None:
        first = run_lab_scenario1_v1(
            store_slug=LAB_STORE_SLUG,
            cf_test_phone=self.phone,
            client=self.client,
        )
        self.assertTrue(first.get("ok"), first)
        second = run_lab_scenario1_v1(
            store_slug=LAB_STORE_SLUG,
            cf_test_phone=self.phone,
            client=self.client,
        )
        self.assertTrue(second.get("ok"), second)
        self.assertEqual(first["identity"], second["identity"])
        self.assertEqual(
            (first.get("truth_assertions") or {}).get("signal_counts"),
            (second.get("truth_assertions") or {}).get("signal_counts"),
        )
        self.assertEqual(
            (first.get("recovered_purchase") or {}).get("amount_sar"),
            (second.get("recovered_purchase") or {}).get("amount_sar"),
        )
        self.assertEqual(
            (first.get("cart_page_state") or {}).get("completed"),
            (second.get("cart_page_state") or {}).get("completed"),
        )
        self.assertTrue(
            (second.get("pulse_payload") or {}).get("sources", {}).get(
                "commerce_signals_used"
            )
        )

    def test_duplicate_purchase_protection(self) -> None:
        out = run_lab_scenario1_duplicate_purchase_probe(
            client=self.client,
            cf_test_phone=self.phone,
        )
        self.assertTrue(out.get("ok"), out)
        counts = out.get("signal_counts") or {}
        self.assertEqual(counts.get("purchase_confirmed"), 1)
        self.assertEqual(counts.get("recovery_completed"), 1)

    def test_no_cross_store_leakage(self) -> None:
        out = run_lab_scenario1_v1(
            store_slug=LAB_STORE_SLUG,
            cf_test_phone=self.phone,
            client=self.client,
        )
        self.assertTrue(out.get("ok"), out)
        cross = out.get("cross_store") or {}
        self.assertTrue(cross.get("ok"), cross)
        kept = (
            db.session.query(PurchaseTruthRecord)
            .filter(PurchaseTruthRecord.recovery_key == "merchant-x:keep-me")
            .first()
        )
        self.assertIsNotNone(kept)
        lab_row = (
            db.session.query(PurchaseTruthRecord)
            .filter(PurchaseTruthRecord.recovery_key == LAB_RECOVERY_KEY)
            .first()
        )
        self.assertIsNotNone(lab_row)
        self.assertEqual(lab_row.store_slug, LAB_STORE_SLUG)


if __name__ == "__main__":
    unittest.main()
