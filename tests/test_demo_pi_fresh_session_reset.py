# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import unittest

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import CartRecoveryReason
from tests.test_recovery_isolation import _reset_recovery_memory


class TestDemoPiFreshSessionReset(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        _reset_recovery_memory()
        db.create_all()

    def tearDown(self) -> None:
        db.session.rollback()
        db.session.query(CartRecoveryReason).filter(
            CartRecoveryReason.store_slug == "demo",
            CartRecoveryReason.session_id.like("s_%"),
        ).delete(synchronize_session=False)
        db.session.commit()

    def test_fresh_query_creates_new_ids_and_price_high_reason(self) -> None:
        phone = "966546518011"
        r = self.client.get(f"/demo/store?cf_test_phone={phone}&fresh=1")
        self.assertEqual(200, r.status_code)
        t = r.text

        sid_match = re.search(r'var sid = "([^"]+)"', t)
        cid_match = re.search(r'var cid = "([^"]+)"', t)
        self.assertIsNotNone(sid_match)
        self.assertIsNotNone(cid_match)
        sid = str(sid_match.group(1))
        cid = str(cid_match.group(1))
        self.assertTrue(sid.startswith("s_"))
        self.assertTrue(cid.startswith("cf_cart_"))
        self.assertIn("reason_tag=price_high", t)
        self.assertIn("/dashboard/normal-carts/operations?nr_session=", t)
        self.assertIn(sid, t)
        self.assertIn(cid, t)

        row = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == "demo",
                CartRecoveryReason.session_id == sid,
            )
            .first()
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual("price_high", (row.reason or "").strip().lower())
        self.assertEqual(phone, (row.customer_phone or "").strip())
