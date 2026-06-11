# -*- coding: utf-8 -*-
"""Storefront Cart Bridge Timing Fix v1 — cache, retry, in-flight wiring."""
from __future__ import annotations

import json
import pathlib
import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
import main
from models import AbandonedCart, Store
from tests.test_recovery_isolation import _reset_recovery_memory

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RUNTIME = _ROOT / "static" / "cartflow_widget_runtime"
_ADAPTERS = _RUNTIME / "cartflow_storefront_cart_adapters.js"
_CORE = _RUNTIME / "cartflow_storefront_cart_bridge_core.js"
_FLOWS = _RUNTIME / "cartflow_widget_flows.js"
_SOURCES = _RUNTIME / "cartflow_cart_sources.js"
_WIDGET_LOADER = _ROOT / "static" / "widget_loader.js"
_JOURNEY = _ROOT / "scripts" / "_cart_journey_truth_trace_v1_out" / "journey_trace.json"


class StorefrontCartBridgeTimingJsTests(unittest.TestCase):
    def test_cache_empty_does_not_overwrite_populated(self) -> None:
        text = _ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("ignore_empty_overwrite", text)
        self.assertIn("[CF CART BRIDGE CACHE KEEP]", text)
        self.assertIn("[CF CART BRIDGE CACHE UPDATE]", text)
        self.assertIn("zidBodyIsPopulated", text)
        self.assertIn("zidBodyIsEmpty", text)

    def test_fetch_falls_back_to_populated_cache(self) -> None:
        text = _ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("zid_api_v1_cart_cached", text)
        self.assertIn("recheck", text)

    def test_retry_logs_and_delays(self) -> None:
        text = _CORE.read_text(encoding="utf-8")
        for tag in (
            "[CF CART BRIDGE RETRY SCHEDULED]",
            "[CF CART BRIDGE RETRY FIRED]",
            "[CF CART BRIDGE RETRY STOP]",
        ):
            self.assertIn(tag, text)
        self.assertIn("500", text)
        self.assertIn("1200", text)
        self.assertIn("2500", text)
        self.assertIn("scheduleEmptyRetries", text)

    def test_inflight_defer_for_priority_triggers(self) -> None:
        text = _CORE.read_text(encoding="utf-8")
        self.assertIn("readAndPersist_defer_after_inflight", text)
        self.assertIn("isPriorityAddTrigger", text)
        self.assertIn("allowFreshAfterInFlight", text)
        self.assertIn("zid_network_hook_post_items", text)

    def test_post_partial_cache_path(self) -> None:
        text = _ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("cacheCartItemResponse", text)
        self.assertIn("cart_items_quantity", text)

    def test_reason_guard_uses_retry_path(self) -> None:
        text = _CORE.read_text(encoding="utf-8")
        self.assertIn("ensure_before_reason", text)
        text_flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("ensureCartTruthBeforeReason", text_flows)
        self.assertIn("cf_reason_orphan_risk", text_flows)

    def test_sources_pass_fresh_after_inflight(self) -> None:
        text = _SOURCES.read_text(encoding="utf-8")
        self.assertIn("allowFreshAfterInFlight", text)

    def test_window_cart_fallback_preserved(self) -> None:
        text = _ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("readGlobalFallback", text)
        self.assertIn("window_cart_fallback", text)

    def test_runtime_version_bumped(self) -> None:
        text = _WIDGET_LOADER.read_text(encoding="utf-8")
        self.assertIn("v2-storefront-cart-bridge-timing-v1", text)


class StorefrontCartBridgeTimingSimulationTests(unittest.TestCase):
    """Python mirror of JS normalization for captured Zid payloads."""

    @staticmethod
    def _num(v):  # noqa: ANN001
        if isinstance(v, (int, float)):
            return float(v)
        if v is None or v == "":
            return None
        try:
            import re

            return float(re.sub(r"[^0-9.\-]", "", str(v)))
        except ValueError:
            return None

    def _metrics(self, body: dict) -> dict:
        products = body.get("products") if isinstance(body.get("products"), list) else []
        item_count = self._num(body.get("products_count"))
        if item_count is None:
            item_count = len(products)
        cart_value = self._num(body.get("total_value"))
        if cart_value is None:
            cart_value = self._num(body.get("products_subtotal"))
        return {
            "item_count": int(item_count or 0),
            "cart_value": float(cart_value or 0),
        }

    def _cache_item_partial(self, body: dict) -> dict:
        item = body.get("item") or {}
        return {
            "products": [item],
            "products_count": self._num(body.get("cart_items_quantity")) or 1,
            "total_value": self._num(item.get("price")),
            "products_subtotal": self._num(item.get("price")),
        }

    def test_journey_post_partial_normalizes(self) -> None:
        data = json.loads(_JOURNEY.read_text(encoding="utf-8"))
        post_body = None
        for row in data["zid_network_sample"]:
            if "/cart/items" in row["url"] and row.get("status") == 201:
                post_body = row["body_sample"]
                break
        self.assertIsNotNone(post_body)
        partial = self._cache_item_partial(post_body)
        m = self._metrics(partial)
        self.assertEqual(m["item_count"], 1)
        self.assertAlmostEqual(m["cart_value"], 10000.0)

    def test_empty_get_does_not_block_populated_get(self) -> None:
        data = json.loads(_JOURNEY.read_text(encoding="utf-8"))
        empty_m = None
        full_m = None
        for row in data["zid_network_sample"]:
            if row.get("url", "").endswith("/api/v1/cart") and row.get("body_sample"):
                m = self._metrics(row["body_sample"])
                if m["cart_value"] <= 0:
                    empty_m = m
                elif m["cart_value"] >= 10000:
                    full_m = m
        self.assertIsNotNone(empty_m)
        self.assertIsNotNone(full_m)
        self.assertEqual(empty_m["item_count"], 0)
        self.assertEqual(full_m["item_count"], 1)


class StorefrontCartBridgeTimingServerTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(main.app)
        db.create_all()
        main._ensure_store_widget_schema()
        self.slug = f"scb_timing_{uuid.uuid4().hex[:8]}"
        self.store = Store(
            zid_store_id=self.slug,
            vip_cart_threshold=1000,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(self.store)
        db.session.commit()

    def test_duplicate_protection_unchanged(self) -> None:
        sid = f"s_dup_{uuid.uuid4().hex[:8]}"
        cid = f"c_dup_{uuid.uuid4().hex[:10]}"
        body = {
            "event": "cart_state_sync",
            "reason": "add",
            "store": self.slug,
            "session_id": sid,
            "cart_id": cid,
            "cart_total": 250.0,
            "items_count": 1,
            "cart": [{"name": "item", "qty": 1, "price": 250}],
        }
        r1 = self.client.post("/api/cart-event", json=body)
        r2 = self.client.post("/api/cart-event", json=body)
        self.assertEqual(r1.status_code, 200, r1.text)
        self.assertEqual(r2.status_code, 200, r2.text)
        rows = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).all()
        self.assertEqual(len(rows), 1)

    def test_vip_cart_still_classifies(self) -> None:
        sid = f"s_vip_{uuid.uuid4().hex[:8]}"
        cid = f"c_vip_{uuid.uuid4().hex[:10]}"
        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "add",
                "store": self.slug,
                "session_id": sid,
                "cart_id": cid,
                "cart_total": 10000.0,
                "items_count": 1,
                "cart": [{"name": "Sony A7", "qty": 1, "price": 10000}],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        self.assertIsNotNone(ac)
        assert ac is not None
        self.assertTrue(bool(ac.vip_mode))

    def test_empty_legacy_sync_still_cleared_not_abandoned(self) -> None:
        sid = f"s_clr_{uuid.uuid4().hex[:8]}"
        cid = f"c_clr_{uuid.uuid4().hex[:10]}"
        self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "add",
                "store": self.slug,
                "session_id": sid,
                "cart_id": cid,
                "cart_total": 0,
                "items_count": 0,
                "cart": [],
            },
        )
        ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        self.assertIsNotNone(ac)
        assert ac is not None
        self.assertEqual(str(ac.status or ""), "cleared")
        self.assertFalse(bool(ac.vip_mode))


if __name__ == "__main__":
    unittest.main()
