# -*- coding: utf-8 -*-
"""Demo Commerce Lab V1 — Lab Reset P1."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from extensions import db
from models import (
    AbandonedCart,
    CartRecoveryReason,
    PurchaseTruthRecord,
    RecoverySchedule,
    RecoveryTruthTimelineEvent,
    Store,
)
from services.demo_lab_reset_v1 import (
    LAB_CART_ID,
    LAB_CUSTOMER_PHONE,
    LAB_RECOVERY_KEY,
    LAB_SESSION_ID,
    LAB_STORE_SLUG,
    lab_reset_v1,
    verify_lab_baseline,
)
from services.demo_sandbox_catalog import merchant_catalog_json_string


def _ensure_demo_store(*, catalog: str = "") -> Store:
    st = db.session.query(Store).filter(Store.zid_store_id == LAB_STORE_SLUG).first()
    if st is None:
        st = Store(zid_store_id=LAB_STORE_SLUG)
        db.session.add(st)
        db.session.flush()
    if catalog:
        st.cf_product_catalog_json = catalog
    db.session.commit()
    return st


def _seed_dirty_lab_state(*, phone: str, catalog: str) -> None:
    st = _ensure_demo_store(catalog=catalog)
    now = datetime.now(timezone.utc)
    # Replace any prior Lab rows so re-seed is deterministic
    db.session.query(CartRecoveryReason).filter(
        CartRecoveryReason.store_slug == LAB_STORE_SLUG,
        CartRecoveryReason.session_id == LAB_SESSION_ID,
    ).delete(synchronize_session=False)
    db.session.query(RecoverySchedule).filter(
        RecoverySchedule.store_slug == LAB_STORE_SLUG,
        RecoverySchedule.recovery_key == LAB_RECOVERY_KEY,
    ).delete(synchronize_session=False)
    db.session.query(RecoveryTruthTimelineEvent).filter(
        RecoveryTruthTimelineEvent.store_slug == LAB_STORE_SLUG,
        RecoveryTruthTimelineEvent.recovery_key == LAB_RECOVERY_KEY,
    ).delete(synchronize_session=False)
    db.session.add(
        CartRecoveryReason(
            store_slug=LAB_STORE_SLUG,
            session_id=LAB_SESSION_ID,
            reason="price_high",
            customer_phone=phone[:100],
            source="widget",
            created_at=now,
            updated_at=now,
        )
    )
    # Unique zid_cart_id per seed to avoid unique collisions across re-seeds
    cart_id = LAB_CART_ID
    existing_ac = (
        db.session.query(AbandonedCart)
        .filter(AbandonedCart.zid_cart_id == cart_id)
        .first()
    )
    if existing_ac is None:
        db.session.add(
            AbandonedCart(
                store_id=int(st.id),
                zid_cart_id=cart_id,
                recovery_session_id=LAB_SESSION_ID,
                customer_phone=phone[:100],
                cart_value=449.0,
                status="abandoned",
                first_seen_at=now,
                last_seen_at=now,
            )
        )
    else:
        existing_ac.store_id = int(st.id)
        existing_ac.recovery_session_id = LAB_SESSION_ID
        existing_ac.customer_phone = phone[:100]
        existing_ac.cart_value = 449.0
        existing_ac.status = "abandoned"

    db.session.add(
        RecoverySchedule(
            recovery_key=LAB_RECOVERY_KEY,
            store_slug=LAB_STORE_SLUG,
            session_id=LAB_SESSION_ID,
            cart_id=LAB_CART_ID,
            customer_phone=phone[:100],
            scheduled_at=now,
            due_at=now + timedelta(seconds=30),
            effective_delay_seconds=30.0,
            delay_source="lab_test",
            status="scheduled",
            step=1,
        )
    )
    db.session.add(
        RecoveryTruthTimelineEvent(
            recovery_key=LAB_RECOVERY_KEY,
            store_slug=LAB_STORE_SLUG,
            session_id=LAB_SESSION_ID,
            cart_id=LAB_CART_ID,
            status="scheduled",
            source="lab_test",
            created_at=now,
        )
    )
    existing_p = (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == LAB_RECOVERY_KEY)
        .first()
    )
    if existing_p is None:
        db.session.add(
            PurchaseTruthRecord(
                recovery_key=LAB_RECOVERY_KEY,
                store_slug=LAB_STORE_SLUG,
                session_id=LAB_SESSION_ID,
                cart_id=LAB_CART_ID,
                purchase_detected=True,
                purchase_time=now,
                purchase_source="lab_test",
                customer_phone=phone[:100],
            )
        )
    else:
        existing_p.purchase_detected = True
        existing_p.customer_phone = phone[:100]

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


class LabResetGateTests(unittest.TestCase):
    def test_rejects_non_demo_store(self) -> None:
        out = lab_reset_v1(store_slug="acme-store")
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "lab_reset_rejected")
        self.assertEqual(out.get("reject_reason"), "store_slug_must_be_demo")

    def test_rejects_demo2(self) -> None:
        out = lab_reset_v1(store_slug="demo2")
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("reject_reason"), "store_slug_must_be_demo")

    def test_rejects_merchant_activation(self) -> None:
        out = lab_reset_v1(store_slug="demo", merchant_activation=True)
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("reject_reason"), "merchant_activation_forbidden")


class LabResetIdempotentTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        self.client = TestClient(app)
        db.create_all()
        self.phone = LAB_CUSTOMER_PHONE
        self.catalog = merchant_catalog_json_string()
        _ensure_demo_store(catalog=self.catalog)

    def tearDown(self) -> None:
        db.session.rollback()
        # Clean lab rows only
        lab_reset_v1(store_slug=LAB_STORE_SLUG, cf_test_phone=self.phone)
        db.session.query(PurchaseTruthRecord).filter(
            PurchaseTruthRecord.store_slug == "merchant-x"
        ).delete(synchronize_session=False)
        db.session.commit()

    def test_reset_clears_lab_runtime_preserves_catalog_and_merchants(self) -> None:
        _seed_dirty_lab_state(phone=self.phone, catalog=self.catalog)
        st_before = (
            db.session.query(Store)
            .filter(Store.zid_store_id == LAB_STORE_SLUG)
            .first()
        )
        assert st_before is not None
        catalog_before = st_before.cf_product_catalog_json

        out = lab_reset_v1(store_slug=LAB_STORE_SLUG, cf_test_phone=self.phone)
        self.assertTrue(out.get("ok"), out)
        self.assertTrue((out.get("baseline") or {}).get("clean"))
        self.assertEqual(out["identity"]["session_id"], LAB_SESSION_ID)
        self.assertEqual(out["identity"]["cart_id"], LAB_CART_ID)
        self.assertEqual(out["identity"]["recovery_key"], LAB_RECOVERY_KEY)

        st_after = (
            db.session.query(Store)
            .filter(Store.zid_store_id == LAB_STORE_SLUG)
            .first()
        )
        assert st_after is not None
        self.assertEqual(st_after.cf_product_catalog_json, catalog_before)

        kept = (
            db.session.query(PurchaseTruthRecord)
            .filter(PurchaseTruthRecord.recovery_key == "merchant-x:keep-me")
            .first()
        )
        self.assertIsNotNone(kept)

        baseline = verify_lab_baseline(
            store_slug=LAB_STORE_SLUG, cf_test_phone=self.phone
        )
        self.assertTrue(baseline.get("clean"))

    def test_reset_twice_identical_fingerprint(self) -> None:
        _seed_dirty_lab_state(phone=self.phone, catalog=self.catalog)
        first = lab_reset_v1(store_slug=LAB_STORE_SLUG, cf_test_phone=self.phone)
        self.assertTrue(first.get("ok"), first)
        # Re-dirty then reset again — second clean pass must match baseline identity
        _seed_dirty_lab_state(phone=self.phone, catalog=self.catalog)
        second = lab_reset_v1(store_slug=LAB_STORE_SLUG, cf_test_phone=self.phone)
        self.assertTrue(second.get("ok"), second)

        # Idempotent empty pass
        third = lab_reset_v1(store_slug=LAB_STORE_SLUG, cf_test_phone=self.phone)
        self.assertTrue(third.get("ok"), third)

        self.assertEqual(first["identity"], second["identity"])
        self.assertEqual(second["identity"], third["identity"])
        self.assertEqual(first["fingerprint"]["lab_phone"], second["fingerprint"]["lab_phone"])
        self.assertEqual(second["fingerprint"]["baseline_counts"], third["fingerprint"]["baseline_counts"])
        self.assertTrue(second["fingerprint"]["clean"])
        self.assertTrue(third["fingerprint"]["clean"])
        self.assertEqual(second["fingerprint"]["clean"], third["fingerprint"]["clean"])
        self.assertEqual(
            second["fingerprint"]["baseline_counts"],
            third["fingerprint"]["baseline_counts"],
        )


if __name__ == "__main__":
    unittest.main()
