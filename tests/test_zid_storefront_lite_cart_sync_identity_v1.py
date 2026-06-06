# -*- coding: utf-8 -*-
"""Zid permalink → canonical merchant store during lite cart_state_sync add."""
from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
import main
from models import AbandonedCart, Store
from schema_store_identity import ensure_store_identity_schema
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    ALIAS_KIND_ZID_PERMALINK,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


class ZidStorefrontLiteCartSyncIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(main.app)
        db.create_all()
        ensure_store_identity_schema(db)
        self.canonical_slug = f"cartflow-{uuid.uuid4().hex[:6]}"
        self.zid_permalink = f"z{uuid.uuid4().hex[:6]}"
        self.store = Store(
            zid_store_id=self.canonical_slug,
            vip_cart_threshold=1000,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(self.store)
        db.session.commit()
        sid = int(self.store.id)
        register_store_identity_alias(
            store_id=sid,
            alias_kind=ALIAS_KIND_CARTFLOW_ZID,
            alias_value=self.canonical_slug,
            platform="cartflow",
        )
        register_store_identity_alias(
            store_id=sid,
            alias_kind=ALIAS_KIND_ZID_PERMALINK,
            alias_value=self.zid_permalink,
            platform="zid",
        )
        db.session.commit()

    def test_lite_add_resolves_permalink_to_canonical_store_row(self) -> None:
        session_id = f"s_zid_{uuid.uuid4().hex[:8]}"
        cart_id = f"c_zid_{uuid.uuid4().hex[:10]}"
        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "add",
                "store": self.zid_permalink,
                "session_id": session_id,
                "cart_id": cart_id,
                "cart_total": 250.0,
                "items_count": 1,
                "cart": [{"name": "item", "qty": 1, "price": 250}],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body.get("cart_state_sync"))
        self.assertEqual(body.get("vip_cart_threshold"), 1000)

        ac = (
            db.session.query(AbandonedCart)
            .filter_by(zid_cart_id=cart_id)
            .first()
        )
        self.assertIsNotNone(ac)
        assert ac is not None
        self.assertEqual(int(ac.store_id or 0), int(self.store.id))
        self.assertEqual(str(ac.status or ""), "abandoned")
        self.assertAlmostEqual(float(ac.cart_value or 0.0), 250.0)

    def test_public_config_exposes_canonical_store_slug_for_permalink(self) -> None:
        r = self.client.get(
            "/api/cartflow/public-config",
            params={"store_slug": self.zid_permalink},
        )
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("request_store_slug"), self.zid_permalink)
        self.assertEqual(body.get("canonical_store_slug"), self.canonical_slug)


if __name__ == "__main__":
    unittest.main()
