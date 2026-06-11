# -*- coding: utf-8 -*-
"""Platform-neutral Cart Event Bridge — backend state + JS wiring assertions."""
from __future__ import annotations

import json
import pathlib
import unittest
import uuid

from extensions import db
from models import Store
from services.widget_settings_runtime_truth_v1 import (
    build_cart_event_bridge_missing_alerts,
    cart_bridge_state_from_beacon,
    evaluate_widget_settings_runtime_truth,
)

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RUNTIME = _ROOT / "static" / "cartflow_widget_runtime"
_BRIDGE = _RUNTIME / "cartflow_cart_event_bridge.js"
_SOURCES = _RUNTIME / "cartflow_cart_sources.js"
_TRIGGERS = _RUNTIME / "cartflow_widget_triggers.js"
_CONFIG = _RUNTIME / "cartflow_widget_config.js"
_RUNTIME_LOADER = _RUNTIME / "cartflow_widget_loader.js"
_WIDGET_LOADER = _ROOT / "static" / "widget_loader.js"


class CartBridgeBackendStateTests(unittest.TestCase):
    def test_cart_bridge_state_defaults_without_beacon(self) -> None:
        state = cart_bridge_state_from_beacon({})
        self.assertIsNone(state["last_event_type"])
        self.assertIsNone(state["last_event_at"])
        self.assertFalse(state["hesitation_armed_from_cart_event"])

    def test_cart_bridge_state_from_beacon(self) -> None:
        beacon = {
            "runtime_truth": {
                "cart_bridge": {
                    "last_event_type": "add_to_cart",
                    "last_event_source_platform": "zid",
                    "last_detected_by": "dom_observer",
                    "last_items_count": 2,
                    "last_cart_total": 150.0,
                    "last_event_at": 1717000000000,
                    "hesitation_armed_from_cart_event": True,
                }
            }
        }
        state = cart_bridge_state_from_beacon(beacon)
        self.assertEqual(state["last_event_type"], "add_to_cart")
        self.assertEqual(state["last_event_source_platform"], "zid")
        self.assertEqual(state["last_detected_by"], "dom_observer")
        self.assertEqual(state["last_items_count"], 2)
        self.assertTrue(state["hesitation_armed_from_cart_event"])

    def test_evaluate_report_includes_cart_bridge(self) -> None:
        db.create_all()
        slug = f"bridge-eval-{uuid.uuid4().hex[:8]}"
        row = Store(zid_store_id=slug)
        row.cartflow_widget_enabled = True
        row.widget_last_beacon_json = json.dumps(
            {
                "store_slug": slug,
                "runtime_truth": {
                    "widget_enabled": True,
                    "config_loaded": True,
                    "cart_bridge": {
                        "last_event_type": "cart_detected",
                        "last_event_source_platform": "zid",
                        "last_event_at": 1717000000000,
                    },
                },
            },
            ensure_ascii=False,
        )
        db.session.add(row)
        db.session.commit()
        report = evaluate_widget_settings_runtime_truth(row, storefront_slug=slug)
        self.assertIn("cart_bridge", report)
        self.assertEqual(report["cart_bridge"]["last_event_type"], "cart_detected")


class CartBridgeMissingAlertTests(unittest.TestCase):
    def _store(self, *, page_url: str, cart_bridge=None) -> dict:
        rt = {"config_loaded": True}
        if cart_bridge is not None:
            rt["cart_bridge"] = cart_bridge
        return {
            "store_id": 1,
            "store_slug": "demo-shop",
            "display_name": "Demo Shop",
            "widget_last_runtime_slug": "demo-shop",
            "widget_last_beacon_json": json.dumps(
                {"page_url": page_url, "runtime_truth": rt}, ensure_ascii=False
            ),
        }

    def test_alert_when_cart_page_and_no_bridge_event(self) -> None:
        alerts = build_cart_event_bridge_missing_alerts(
            stores=[self._store(page_url="https://4hz49e.zid.store/cart")]
        )
        self.assertTrue(alerts)
        self.assertEqual(alerts[0]["kind"], "cart_event_bridge_missing")
        rec = (alerts[0].get("records") or [{}])[0]
        self.assertEqual(rec.get("platform"), "zid")

    def test_no_alert_when_bridge_event_present(self) -> None:
        alerts = build_cart_event_bridge_missing_alerts(
            stores=[
                self._store(
                    page_url="https://4hz49e.zid.store/cart",
                    cart_bridge={"last_event_at": 1717000000000},
                )
            ]
        )
        self.assertEqual(alerts, [])

    def test_no_alert_when_not_cart_page(self) -> None:
        alerts = build_cart_event_bridge_missing_alerts(
            stores=[self._store(page_url="https://4hz49e.zid.store/products/abc")]
        )
        self.assertEqual(alerts, [])


class CartBridgeJsWiringTests(unittest.TestCase):
    def test_bridge_module_contract_and_logs(self) -> None:
        text = _BRIDGE.read_text(encoding="utf-8")
        for tag in (
            "[CF CART EVENT SOURCE]",
            "[CF CART EVENT NORMALIZED]",
            "[CF CART EVENT BRIDGE DISPATCH]",
            "[CF CART EVENT BRIDGE BACKEND SYNC]",
        ):
            self.assertIn(tag, text)
        self.assertIn("Cf.Triggers.onNormalizedCartEvent", text)
        self.assertIn("Cf.CartBridge", text)
        self.assertIn("routed_to", text)
        self.assertIn("cartflowSyncCartState", text)
        self.assertIn("syncBackendCartState", text)

    def test_sources_module_has_zid_and_stubs(self) -> None:
        text = _SOURCES.read_text(encoding="utf-8")
        self.assertIn("reportSignal", text)
        for name in (
            "zidCartEventSource",
            "sallaCartEventSource",
            "shopifyCartEventSource",
            "genericCartEventSource",
        ):
            self.assertIn(name, text)

    def test_zid_adapter_suppresses_false_positive_on_load(self) -> None:
        text = _SOURCES.read_text(encoding="utf-8")
        # Per-layer detection diagnostics present.
        self.assertIn("[CF ZID DETECTION LAYER]", text)
        for key in (
            "layer_name",
            "emitted_event_type",
            "cart_count",
            "cart_total",
            "page_url",
            "trigger_reason",
        ):
            self.assertIn(key, text)
        # Initial-load hydration must populate state only (no dispatch).
        self.assertIn("_loadWindowActive", text)
        self.assertIn("initial_load_window_hydration_only", text)
        # URL fallback no longer emits on page load.
        self.assertIn("url_fallback_no_emit_on_load", text)

    def test_triggers_exposes_normalized_entry(self) -> None:
        text = _TRIGGERS.read_text(encoding="utf-8")
        self.assertIn("onNormalizedCartEvent", text)
        self.assertIn("cartBridgeHasCart", text)

    def test_config_snapshot_includes_cart_bridge(self) -> None:
        text = _CONFIG.read_text(encoding="utf-8")
        self.assertIn("cart_bridge", text)
        self.assertIn("CartBridge", text)

    def test_loader_registers_new_modules(self) -> None:
        text = _RUNTIME_LOADER.read_text(encoding="utf-8")
        self.assertIn("cartflow_cart_sources.js", text)
        self.assertIn("cartflow_cart_event_bridge.js", text)
        self.assertIn("cartflow_storefront_cart_bridge_contract.js", text)
        self.assertIn("cartflow_storefront_cart_adapters.js", text)
        self.assertIn("cartflow_storefront_cart_bridge_core.js", text)

    def test_widget_loader_runtime_version_bumped(self) -> None:
        text = _WIDGET_LOADER.read_text(encoding="utf-8")
        self.assertIn("v2-storefront-cart-bridge-v1", text)


if __name__ == "__main__":
    unittest.main()
