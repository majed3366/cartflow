# -*- coding: utf-8 -*-
"""Widget Product Identity v1 — safe capture module and sync enrichment tests."""
from __future__ import annotations

import json
import pathlib
import unittest
import uuid

from fastapi.testclient import TestClient

import main
from extensions import db
from models import AbandonedCart, Store
from schema_store_identity import ensure_store_identity_schema
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_CAPTURE = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_product_identity_capture.js"
_TRACKING = _ROOT / "static" / "cart_abandon_tracking.js"
_WIDGET = _ROOT / "static" / "cartflow_widget.js"
_LOADER = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_loader.js"
_PARTIAL = _ROOT / "templates" / "partials" / "cart_abandon_tracking.html"


class WidgetProductIdentityCaptureStaticTests(unittest.TestCase):
    def test_capture_module_exists_and_exports_api(self) -> None:
        s = _CAPTURE.read_text(encoding="utf-8")
        self.assertIn("cartflowCaptureProductLines", s)
        self.assertIn("cartflowAttachProductLines", s)
        self.assertIn("MAX_LINES = 20", s)
        self.assertIn("window.cart.products", s)
        self.assertIn("zid.cart.products", s)
        self.assertIn("[PRODUCT IDENTITY]", s)
        self.assertNotIn("fetch(", s)
        self.assertNotIn("XMLHttpRequest", s)

    def test_loader_includes_capture_module_early(self) -> None:
        s = _LOADER.read_text(encoding="utf-8")
        self.assertIn("cartflow_product_identity_capture.js", s)
        cfg = s.index("cartflow_widget_config.js")
        cap = s.index("cartflow_product_identity_capture.js")
        fetch = s.index("cartflow_widget_fetch.js")
        self.assertLess(cfg, cap)
        self.assertLess(cap, fetch)

    def test_tracking_and_widget_enrich_sync_only(self) -> None:
        tracking = _TRACKING.read_text(encoding="utf-8")
        widget = _WIDGET.read_text(encoding="utf-8")
        self.assertIn("cartflowAttachProductLines", tracking)
        self.assertIn('event: "cart_state_sync"', tracking)
        self.assertIn('event: "cart_abandoned"', tracking)
        self.assertIn("cartflowAttachProductLines", widget)
        self.assertIn('event: "cart_state_sync"', widget)
        # Bridge / triggers must not be modified to require product fields
        bridge = (_ROOT / "static/cartflow_widget_runtime/cartflow_cart_event_bridge.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("cartflowAttachProductLines", bridge)

    def test_partial_loads_capture_before_tracking(self) -> None:
        html = _PARTIAL.read_text(encoding="utf-8")
        cap = html.index("cartflow_product_identity_capture.js")
        trk = html.index("cart_abandon_tracking.js")
        self.assertLess(cap, trk)


class WidgetProductIdentityCaptureIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(main.app)
        db.create_all()
        ensure_store_identity_schema(db)
        self.slug = f"pi-cap-{uuid.uuid4().hex[:6]}"
        self.store = Store(zid_store_id=self.slug, vip_cart_threshold=1000)
        db.session.add(self.store)
        db.session.commit()
        register_store_identity_alias(
            store_id=int(self.store.id),
            alias_kind=ALIAS_KIND_CARTFLOW_ZID,
            alias_value=self.slug,
            platform="cartflow",
        )
        db.session.commit()

    def test_cart_state_sync_persists_lines_additively(self) -> None:
        session_id = f"s_pi_{uuid.uuid4().hex[:8]}"
        cart_id = f"c_pi_{uuid.uuid4().hex[:10]}"
        lines = [
            {
                "product_id": "prod-1",
                "variant_id": "var-1",
                "sku": "SKU-1",
                "name": "Test Product",
                "unit_price": 99.0,
                "quantity": 2,
            }
        ]
        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "add",
                "store": self.slug,
                "session_id": session_id,
                "cart_id": cart_id,
                "cart_total": 198.0,
                "items_count": 1,
                "cart": [],
                "lines": lines,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json().get("cart_state_sync"))

        ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cart_id).first()
        self.assertIsNotNone(ac)
        raw = json.loads(ac.raw_payload or "{}")
        self.assertIsInstance(raw.get("lines"), list)
        self.assertEqual(len(raw["lines"]), 1)
        self.assertEqual(raw["lines"][0]["product_id"], "prod-1")
        self.assertEqual(raw["lines"][0]["name"], "Test Product")

    def test_cart_state_sync_empty_lines_does_not_break(self) -> None:
        session_id = f"s_pi_{uuid.uuid4().hex[:8]}"
        cart_id = f"c_pi_{uuid.uuid4().hex[:10]}"
        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "page_load",
                "store": self.slug,
                "session_id": session_id,
                "cart_id": cart_id,
                "cart_total": 0.0,
                "items_count": 0,
                "cart": [],
                "lines": [],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json().get("cart_state_sync"))


if __name__ == "__main__":
    unittest.main()
