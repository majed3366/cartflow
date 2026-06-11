# -*- coding: utf-8 -*-
"""Storefront Cart Bridge Recovery v1 — contract, Zid adapter, core wiring, server safety."""
from __future__ import annotations

import json
import pathlib
import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
import main
from models import AbandonedCart, Store
from services.storefront_cart_bridge_diagnostics_v1 import (
    build_storefront_cart_bridge_truth_report,
    storefront_cart_bridge_state_from_beacon,
)
from tests.test_recovery_isolation import _reset_recovery_memory

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RUNTIME = _ROOT / "static" / "cartflow_widget_runtime"
_CONTRACT = _RUNTIME / "cartflow_storefront_cart_bridge_contract.js"
_ADAPTERS = _RUNTIME / "cartflow_storefront_cart_adapters.js"
_CORE = _RUNTIME / "cartflow_storefront_cart_bridge_core.js"
_BRIDGE = _RUNTIME / "cartflow_cart_event_bridge.js"
_SOURCES = _RUNTIME / "cartflow_cart_sources.js"
_FLOWS = _RUNTIME / "cartflow_widget_flows.js"
_CONFIG = _RUNTIME / "cartflow_widget_config.js"
_RUNTIME_LOADER = _RUNTIME / "cartflow_widget_loader.js"
_WIDGET_LOADER = _ROOT / "static" / "widget_loader.js"


class StorefrontCartBridgeJsWiringTests(unittest.TestCase):
    def test_contract_required_fields_and_validation(self) -> None:
        text = _CONTRACT.read_text(encoding="utf-8")
        for field in (
            "platform",
            "store_slug",
            "canonical_store_slug",
            "session_id",
            "cart_id",
            "cart_token",
            "cart_value",
            "currency",
            "item_count",
            "items",
            "source",
            "observed_at",
        ):
            self.assertIn(field, text)
        self.assertIn("missing_store_slug", text)
        self.assertIn("missing_session_id", text)
        self.assertIn("missing_cart_value", text)
        self.assertIn("empty_item_count", text)
        self.assertIn("dedupeKey", text)
        self.assertIn("cf_storefront_cart_bridge", text)

    def test_adapter_interface_and_zid_sources(self) -> None:
        text = _ADAPTERS.read_text(encoding="utf-8")
        for fn in ("canHandle", "detect", "readCart", "normalize", "sourceName"):
            self.assertIn(fn, text)
        self.assertIn("/api/v1/cart", text)
        self.assertIn("window_cart_fallback", text)
        self.assertIn("stubAdapter", text)
        self.assertIn('stubAdapter("salla")', text)
        self.assertIn('stubAdapter("shopify")', text)

    def test_core_proof_logs_and_no_direct_adapter_post(self) -> None:
        text = _CORE.read_text(encoding="utf-8")
        for tag in (
            "[CF CART BRIDGE ADAPTER]",
            "[CF CART BRIDGE READ]",
            "[CF CART BRIDGE NORMALIZED]",
            "[CF CART BRIDGE POST]",
            "[CF CART BRIDGE SKIP]",
            "[CF CART BRIDGE ERROR]",
        ):
            self.assertIn(tag, text)
        self.assertIn("ensureCartTruthBeforeReason", text)
        self.assertIn("/api/cart-event", text)
        self.assertNotIn("adapter.post", text)

    def test_event_bridge_delegates_to_storefront_core(self) -> None:
        text = _BRIDGE.read_text(encoding="utf-8")
        self.assertIn("StorefrontCartBridge.persistFromTrigger", text)
        self.assertIn("cartflowSyncCartState", text)

    def test_sources_invoke_storefront_bridge(self) -> None:
        text = _SOURCES.read_text(encoding="utf-8")
        self.assertIn("StorefrontCartBridge.readAndPersist", text)

    def test_flows_ensure_cart_before_reason(self) -> None:
        text = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("ensureCartTruthBeforeReason", text)
        self.assertIn("cf_reason_orphan_risk", text)
        self.assertIn("cf_cart_bridge_diagnostic", text)

    def test_config_beacon_includes_storefront_bridge(self) -> None:
        text = _CONFIG.read_text(encoding="utf-8")
        self.assertIn("storefront_cart_bridge", text)
        self.assertIn("StorefrontCartBridge", text)

    def test_loader_registers_bridge_modules(self) -> None:
        text = _RUNTIME_LOADER.read_text(encoding="utf-8")
        self.assertIn("cartflow_storefront_cart_bridge_contract.js", text)
        self.assertIn("cartflow_storefront_cart_adapters.js", text)
        self.assertIn("cartflow_storefront_cart_bridge_core.js", text)

    def test_widget_loader_runtime_version(self) -> None:
        text = _WIDGET_LOADER.read_text(encoding="utf-8")
        self.assertIn("v2-widget-trigger-arbitration-shadow-v1", text)


class StorefrontCartBridgeDiagnosticsTests(unittest.TestCase):
    def test_beacon_state_defaults(self) -> None:
        state = storefront_cart_bridge_state_from_beacon({})
        self.assertFalse(state["cart_persisted"])
        self.assertIsNone(state["adapter"])

    def test_truth_report_operator_questions(self) -> None:
        beacon = {
            "runtime_truth": {
                "storefront_cart_bridge": {
                    "adapter": "zid",
                    "read_source": "zid_api_v1_cart",
                    "last_post_ok": True,
                    "cart_persisted": True,
                }
            }
        }
        report = build_storefront_cart_bridge_truth_report(
            store_slug="demo",
            session_id="s1",
            beacon=beacon,
        )
        self.assertTrue(report["ok"])
        self.assertEqual(len(report["operator_questions"]), 8)
        self.assertEqual(report["storefront_cart_bridge"]["adapter"], "zid")


class StorefrontCartBridgeServerTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(main.app)
        db.create_all()
        main._ensure_store_widget_schema()
        self.slug = f"scb_{uuid.uuid4().hex[:8]}"
        self.store = Store(
            zid_store_id=self.slug,
            vip_cart_threshold=1000,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(self.store)
        db.session.commit()

    def _normalized_payload(
        self,
        *,
        session_id: str,
        cart_id: str,
        cart_total: float,
        items_count: int = 1,
        reason: str = "add",
    ) -> dict:
        return {
            "event": "cart_state_sync",
            "reason": reason,
            "store": self.slug,
            "session_id": session_id,
            "cart_id": cart_id,
            "cart_total": cart_total,
            "items_count": items_count,
            "cart": [{"name": "Sony A7", "qty": 1, "price": cart_total}],
            "cf_storefront_cart_bridge": {
                "platform": "zid",
                "canonical_store_slug": self.slug,
                "cart_token": "3121837:token",
                "source": "zid_api_v1_cart",
                "observed_at": 1717000000000,
                "currency": "SAR",
            },
        }

    def test_normalized_payload_creates_abandoned_cart(self) -> None:
        sid = f"s_scb_{uuid.uuid4().hex[:8]}"
        cid = f"c_scb_{uuid.uuid4().hex[:10]}"
        r = self.client.post(
            "/api/cart-event",
            json=self._normalized_payload(
                session_id=sid, cart_id=cid, cart_total=10000.0
            ),
        )
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body.get("cart_state_sync"))
        ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        self.assertIsNotNone(ac)
        assert ac is not None
        self.assertAlmostEqual(float(ac.cart_value or 0.0), 10000.0)
        self.assertTrue(bool(ac.vip_mode))
        raw = json.loads(ac.raw_payload or "{}")
        self.assertEqual(raw.get("cf_storefront_cart_bridge", {}).get("platform"), "zid")

    def test_empty_cart_bridge_contract_skips_on_client(self) -> None:
        text = _CONTRACT.read_text(encoding="utf-8")
        self.assertIn("empty_cart_value", text)
        self.assertIn("empty_item_count", text)
        core = _CORE.read_text(encoding="utf-8")
        self.assertIn("cart_read_empty", core)
        self.assertIn("dedupe_unchanged", core)

    def test_empty_cart_server_legacy_creates_cleared_not_abandoned(self) -> None:
        """Server legacy path unchanged: empty sync upserts cleared row (not VIP/abandoned)."""
        sid = f"s_empty_{uuid.uuid4().hex[:8]}"
        cid = f"c_empty_{uuid.uuid4().hex[:10]}"
        r = self.client.post(
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
        self.assertEqual(r.status_code, 200, r.text)
        ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        self.assertIsNotNone(ac)
        assert ac is not None
        self.assertEqual(str(ac.status or ""), "cleared")
        self.assertFalse(bool(ac.vip_mode))

    def test_duplicate_identical_payload_single_row(self) -> None:
        sid = f"s_dup_{uuid.uuid4().hex[:8]}"
        cid = f"c_dup_{uuid.uuid4().hex[:10]}"
        body = self._normalized_payload(
            session_id=sid, cart_id=cid, cart_total=250.0
        )
        r1 = self.client.post("/api/cart-event", json=body)
        r2 = self.client.post("/api/cart-event", json=body)
        self.assertEqual(r1.status_code, 200, r1.text)
        self.assertEqual(r2.status_code, 200, r2.text)
        rows = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).all()
        self.assertEqual(len(rows), 1)

    def test_legacy_window_cart_payload_still_works(self) -> None:
        sid = f"s_legacy_{uuid.uuid4().hex[:8]}"
        cid = f"c_legacy_{uuid.uuid4().hex[:10]}"
        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "add",
                "store": self.slug,
                "session_id": sid,
                "cart_id": cid,
                "cart_total": 150.0,
                "items_count": 1,
                "cart": [{"name": "item", "qty": 1, "price": 150}],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json().get("cart_state_sync"))
        ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        self.assertIsNotNone(ac)

    def test_dev_truth_endpoint(self) -> None:
        sid = f"s_dev_{uuid.uuid4().hex[:8]}"
        cid = f"c_dev_{uuid.uuid4().hex[:10]}"
        self.client.post(
            "/api/cart-event",
            json=self._normalized_payload(
                session_id=sid, cart_id=cid, cart_total=500.0
            ),
        )
        r = self.client.get(
            "/dev/storefront-cart-bridge-truth",
            params={"store_slug": self.slug, "cart_id": cid},
        )
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("abandoned_cart", {}).get("exists"))


if __name__ == "__main__":
    unittest.main()
