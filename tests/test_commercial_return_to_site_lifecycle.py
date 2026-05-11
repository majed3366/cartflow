# -*- coding: utf-8 -*-
"""Commercial vs passive return-to-site — سلوك ‎/api/cart-event‎ ووحدات التصنيف."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import main
from extensions import db
from models import AbandonedCart
from services.behavioral_recovery.state_store import behavioral_dict_for_abandoned_cart
from services.behavioral_recovery.user_return import (
    payload_indicates_active_commercial_reengagement,
    payload_indicates_passive_return_visit,
)
from tests.test_recovery_isolation import (
    _post_recovery_reason_for_session,
    _reset_recovery_memory,
)


class CommercialReturnClassifierTests(unittest.TestCase):
    def test_passive_explicit_payload(self) -> None:
        p = {"passive_return_visit": True, "return_visit_kind": "passive_return_visit"}
        self.assertTrue(payload_indicates_passive_return_visit(p))
        self.assertFalse(payload_indicates_active_commercial_reengagement(p))

    def test_active_explicit_payload(self) -> None:
        p = {"active_commercial_reengagement": True}
        self.assertTrue(payload_indicates_active_commercial_reengagement(p))
        self.assertFalse(payload_indicates_passive_return_visit(p))

    def test_legacy_tracker_product_is_passive_only(self) -> None:
        p = {
            "event_type": "user_returned_to_site",
            "user_returned_to_site": True,
            "recovery_return_context": "product",
        }
        self.assertTrue(payload_indicates_passive_return_visit(p))
        self.assertFalse(payload_indicates_active_commercial_reengagement(p))


class CommercialReturnApiScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(main.app)

    def test_scenario_a_passive_visit_records_no_suppression(self) -> None:
        sid = "cf-scen-a-passive"
        cid = "cf-cart-scen-a"
        _post_recovery_reason_for_session(self.client, "demo", sid)
        abandon = {
            "event": "cart_abandoned",
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "cart": [{"name": "T", "price": 10.0}],
            "phone": "9665111222333",
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=abandon).status_code)
        key = main._recovery_key_from_payload({"store": "demo", "session_id": sid, "cart_id": cid})
        main._test_set_recovery_flow_armed_at(
            key, datetime.now(timezone.utc) - timedelta(seconds=120)
        )
        passive = {
            "return_visit_kind": "passive_return_visit",
            "passive_return_visit": True,
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "recovery_return_context": "page",
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=passive).status_code)
        self.assertFalse(main._is_user_returned(key), msg="passive visit must not arm suppression")
        row = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == sid, AbandonedCart.zid_cart_id == cid)
            .first()
        )
        self.assertIsNotNone(row)
        bh = behavioral_dict_for_abandoned_cart(row)
        self.assertGreaterEqual(int(bh.get("passive_return_visit_count") or 0), 1)
        self.assertNotEqual(bh.get("user_returned_to_site"), True)

    def test_scenario_b_cart_sync_add_tracks_commercial_return_when_qualified(self) -> None:
        sid = "cf-scen-b-add"
        cid = "cf-cart-scen-b"
        _post_recovery_reason_for_session(self.client, "demo", sid)
        abandon = {
            "event": "cart_abandoned",
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "cart": [{"name": "T", "price": 10.0}],
            "phone": "9665111222444",
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=abandon).status_code)
        key = main._recovery_key_from_payload({"store": "demo", "session_id": sid, "cart_id": cid})
        main._test_set_recovery_flow_armed_at(
            key, datetime.now(timezone.utc) - timedelta(seconds=120)
        )
        sync = {
            "event": "cart_state_sync",
            "reason": "add",
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "cart_total": 25.0,
            "items_count": 1,
            "cart": [{"name": "T", "price": 25.0, "quantity": 1}],
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=sync).status_code)
        self.assertTrue(main._is_user_returned(key))
        row = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == sid, AbandonedCart.zid_cart_id == cid)
            .first()
        )
        self.assertIsNotNone(row)
        bh = behavioral_dict_for_abandoned_cart(row)
        self.assertTrue(bh.get("user_returned_to_site") is True)

    def test_scenario_c_checkout_context_payload_suppresses_when_qualified(self) -> None:
        sid = "cf-scen-c-checkout"
        cid = "cf-cart-scen-c"
        _post_recovery_reason_for_session(self.client, "demo", sid)
        abandon = {
            "event": "cart_abandoned",
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "cart": [{"name": "T", "price": 10.0}],
            "phone": "9665111222555",
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=abandon).status_code)
        key = main._recovery_key_from_payload({"store": "demo", "session_id": sid, "cart_id": cid})
        main._test_set_recovery_flow_armed_at(
            key, datetime.now(timezone.utc) - timedelta(seconds=120)
        )
        active = {
            "event_type": "user_returned_to_site",
            "user_returned_to_site": True,
            "active_commercial_reengagement": True,
            "return_visit_kind": "active_commercial_reengagement",
            "returned_checkout_page": True,
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "recovery_return_context": "checkout",
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=active).status_code)
        self.assertTrue(main._is_user_returned(key))
