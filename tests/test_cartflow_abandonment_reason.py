# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from main import app
from extensions import db
from models import CartRecoveryLog, Store
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
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue((r.json() or {}).get("ok"))

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

    def test_ready_step1(self) -> None:
        ensure_store_widget_schema(db)
        r0 = self.client.get(
            "/api/cartflow/ready",
            params={"store_slug": "rstore", "session_id": "rs1"},
        )
        self.assertEqual(200, r0.status_code)
        self.assertFalse((r0.json() or {}).get("after_step1"))
        log = CartRecoveryLog(
            store_slug="rstore",
            session_id="rs1",
            message="m",
            status="mock_sent",
            step=1,
        )
        db.session.add(log)
        db.session.commit()
        r1 = self.client.get(
            "/api/cartflow/ready",
            params={"store_slug": "rstore", "session_id": "rs1"},
        )
        self.assertEqual(200, r1.status_code)
        self.assertTrue((r1.json() or {}).get("after_step1"))

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
