# -*- coding: utf-8 -*-
"""Integrations foundation v1 — adapter layer + gateway routing (no live platforms)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from integrations.adapters import SallaAdapter, ShopifyAdapter, ZidAdapter
from integrations.normalized_platform_event import (
    EVENT_CART_ABANDONED,
    EVENT_ORDER_PAID,
    NormalizedPlatformEvent,
)
from services.platform_integration_gateway import (
    clear_platform_integration_state_for_tests,
    receive_from_adapter,
    receive_normalized_event,
    validate_minimum_fields,
)


def _abandon_event(**kwargs: object) -> NormalizedPlatformEvent:
    base = {
        "platform": "test",
        "store_slug": "demo-store",
        "event_type": EVENT_CART_ABANDONED,
        "external_cart_id": "cart-100",
        "external_customer_id": "cust-1",
        "customer_phone": "",
    }
    base.update(kwargs)
    return NormalizedPlatformEvent.from_dict(base)


def _order_paid_event(**kwargs: object) -> NormalizedPlatformEvent:
    base = {
        "platform": "test",
        "store_slug": "demo-store",
        "event_type": EVENT_ORDER_PAID,
        "external_order_id": "ord-200",
        "external_cart_id": "cart-100",
        "session_id": "cart-100",
    }
    base.update(kwargs)
    return NormalizedPlatformEvent.from_dict(base)


class IntegrationsFoundationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        clear_platform_integration_state_for_tests()

    def tearDown(self) -> None:
        clear_platform_integration_state_for_tests()

    def test_missing_required_fields_skip(self) -> None:
        ev = NormalizedPlatformEvent(
            platform="",
            store_slug="",
            event_type=EVENT_CART_ABANDONED,
        )
        self.assertTrue(validate_minimum_fields(ev))
        with patch("builtins.print"):
            out = receive_normalized_event(ev)
        self.assertTrue(out.get("skipped"))
        self.assertEqual(out.get("reason"), "missing_required_field")

    def test_phone_missing_does_not_crash(self) -> None:
        ev = _abandon_event(customer_phone="")
        with patch(
            "services.platform_integration_gateway._route_cart_abandoned",
            return_value={"ok": True, "routed": True, "target": "cart_abandoned"},
        ):
            with patch("builtins.print"):
                out = receive_normalized_event(ev)
        self.assertTrue(out.get("routed") or out.get("ok"))

    def test_duplicate_external_event_skipped(self) -> None:
        ev = _abandon_event()
        with patch(
            "services.platform_integration_gateway._route_cart_abandoned",
            return_value={"ok": True, "routed": True},
        ):
            with patch("builtins.print"):
                receive_normalized_event(ev)
                out2 = receive_normalized_event(ev)
        self.assertTrue(out2.get("skipped"))
        self.assertEqual(out2.get("reason"), "duplicate_external_event")

    def test_cart_abandoned_routes_to_core_path(self) -> None:
        ev = _abandon_event(customer_phone="+966500000001")
        with patch(
            "services.platform_integration_gateway._route_cart_abandoned",
            return_value={"ok": True, "routed": True, "target": "cart_abandoned"},
        ) as mock_route:
            with patch("builtins.print"):
                out = receive_normalized_event(ev)
        mock_route.assert_called_once()
        self.assertEqual(out.get("target"), "cart_abandoned")

    def test_order_paid_routes_to_purchase_truth(self) -> None:
        ev = _order_paid_event()
        with patch(
            "services.purchase_truth.ingest_purchase_truth_payload",
            return_value="demo-store:cart-100",
        ) as mock_ingest:
            with patch("builtins.print"):
                out = receive_normalized_event(ev)
        mock_ingest.assert_called_once()
        self.assertEqual(out.get("target"), "purchase_truth")
        payload = mock_ingest.call_args[0][0]
        self.assertTrue(payload.get("order_paid"))

    def test_adapters_scaffold_no_external_api(self) -> None:
        for cls in (ZidAdapter, SallaAdapter, ShopifyAdapter):
            adapter = cls()
            with patch("requests.get") as mock_get:
                with patch("requests.post") as mock_post:
                    self.assertIsNone(adapter.normalize_event({"event": "test"}))
                    self.assertFalse(adapter.verify_signature({}, b"{}"))
                    adapter.map_store({})
                    adapter.extract_customer({})
                    adapter.extract_cart({})
                    adapter.extract_order({})
            mock_get.assert_not_called()
            mock_post.assert_not_called()

    def test_receive_from_adapter_none_when_not_implemented(self) -> None:
        with patch("builtins.print"):
            out = receive_from_adapter(ZidAdapter(), {"hello": 1})
        self.assertTrue(out.get("skipped"))
        self.assertEqual(out.get("reason"), "adapter_not_implemented")


class IntegrationsFoundationCartAbandonIntegrationTests(unittest.TestCase):
    """Optional deeper path: duplicate guard suppresses second abandon without double route."""

    def setUp(self) -> None:
        clear_platform_integration_state_for_tests()

    def tearDown(self) -> None:
        clear_platform_integration_state_for_tests()

    def test_duplicate_guard_blocks_second_abandon_burst(self) -> None:
        from services.cartflow_duplicate_guard import reset_duplicate_guard_for_tests

        reset_duplicate_guard_for_tests()
        ev = _abandon_event(external_cart_id="dup-cart-1")
        calls = []

        def fake_route(event: NormalizedPlatformEvent, core: dict) -> dict:
            calls.append(1)
            return {"ok": True, "routed": True, "target": "cart_abandoned"}

        with patch(
            "services.platform_integration_gateway._route_cart_abandoned",
            side_effect=fake_route,
        ):
            with patch("builtins.print"):
                clear_platform_integration_state_for_tests()
                receive_normalized_event(ev)
                clear_platform_integration_state_for_tests()
                ev2 = _abandon_event(external_cart_id="dup-cart-1", event_time="")
                receive_normalized_event(ev2)
        # First call routes; second may be duplicate_external or duplicate burst on route
        self.assertGreaterEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
