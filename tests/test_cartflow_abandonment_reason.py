# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid
import unittest

from main import app
from extensions import db
from models import CartRecoveryLog, CartRecoveryReason, Store
from schema_widget import ensure_store_widget_schema


class TestCartflowAbandonmentReason(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        self.client = TestClient(app)

    def test_post_reason_price(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-test-1",
                "reason": "price",
                "sub_category": "price_discount_request",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue((r.json() or {}).get("ok"))

    def test_post_reason_price_requires_sub(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={"store_slug": "demo", "session_id": "s-no-sub", "reason": "price"},
        )
        self.assertEqual(400, r.status_code, r.text)
        self.assertFalse((r.json() or {}).get("ok"))

    def test_post_reason_sub_rejected_for_non_price(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-extra",
                "reason": "warranty",
                "sub_category": "price_discount_request",
            },
        )
        self.assertEqual(400, r.status_code, r.text)
        self.assertFalse((r.json() or {}).get("ok"))

    def test_post_reason_other_requires_text(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-test-2",
                "reason": "other",
            },
        )
        self.assertEqual(400, r.status_code)
        self.assertFalse((r.json() or {}).get("ok"))

    def test_post_reason_other_accepts_phone_only(self) -> None:
        ensure_store_widget_schema(db)
        sid = "s-phone-only-" + uuid.uuid4().hex[:8]
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": sid,
                "reason": "other",
                "customer_phone": "966512345678",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue((r.json() or {}).get("ok"))
        crr = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == "demo",
                CartRecoveryReason.session_id == sid,
            )
            .first()
        )
        self.assertIsNotNone(crr)
        self.assertEqual("966512345678", (crr.customer_phone or "").strip())

    def test_post_reason_other_invalid_phone(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-inv-ph",
                "reason": "other",
                "customer_phone": "12345",
            },
        )
        self.assertEqual(400, r.status_code)
        self.assertFalse((r.json() or {}).get("ok"))

    def test_customer_phone_rejected_when_not_other(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-wa-phone",
                "reason": "warranty",
                "customer_phone": "966512345678",
            },
        )
        self.assertEqual(400, r.status_code)
        self.assertEqual(
            "customer_phone_not_applicable",
            (r.json() or {}).get("error"),
        )

    def test_ready_step1(self) -> None:
        ensure_store_widget_schema(db)
        sid = "rs1-" + uuid.uuid4().hex
        r0 = self.client.get(
            "/api/cartflow/ready",
            params={"store_slug": "rstore", "session_id": sid},
        )
        self.assertEqual(200, r0.status_code)
        self.assertFalse((r0.json() or {}).get("after_step1"))
        log = CartRecoveryLog(
            store_slug="rstore",
            session_id=sid,
            message="m",
            status="mock_sent",
            step=1,
        )
        db.session.add(log)
        db.session.commit()
        r1 = self.client.get(
            "/api/cartflow/ready",
            params={"store_slug": "rstore", "session_id": sid},
        )
        self.assertEqual(200, r1.status_code)
        self.assertTrue((r1.json() or {}).get("after_step1"))

    def test_cart_recovery_reason_upsert(self) -> None:
        ensure_store_widget_schema(db)
        sid = "crr-upsert-1"
        r1 = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": sid,
                "reason": "price",
                "sub_category": "price_budget_issue",
            },
        )
        self.assertEqual(200, r1.status_code, r1.text)
        self.assertTrue((r1.json() or {}).get("ok"))
        r2 = self.client.post(
            "/api/cartflow/reason",
            json={"store_slug": "demo", "session_id": sid, "reason": "warranty"},
        )
        self.assertEqual(200, r2.status_code, r2.text)
        self.assertTrue((r2.json() or {}).get("ok"))
        crr = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == "demo",
                CartRecoveryReason.session_id == sid,
            )
            .first()
        )
        self.assertIsNotNone(crr)
        self.assertEqual("warranty", crr.reason)
        self.assertIsNone(crr.sub_category)

    def test_public_config_whatsapp(self) -> None:
        ensure_store_widget_schema(db)
        row = db.session.query(Store).order_by(Store.id.desc()).first()
        if row is not None:
            row.whatsapp_support_url = "https://wa.me/966500000000"
            db.session.commit()
        r = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": "demo"}
        )
        self.assertEqual(200, r.status_code)
        j = r.json() or {}
        self.assertTrue(j.get("ok"))


if __name__ == "__main__":
    unittest.main()
