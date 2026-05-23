# -*- coding: utf-8 -*-
"""WhatsApp Production Reality v2 — window + template foundation (no send gates)."""
from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from services.whatsapp_production_reality_v2 import (
    READINESS_PARTIAL,
    READINESS_PRODUCTION_READY,
    READINESS_SANDBOX_ONLY,
    WINDOW_INSIDE,
    WINDOW_OUTSIDE,
    WINDOW_UNKNOWN,
    clear_inbound_observations_for_tests,
    decide_template_routing,
    evaluate_conversation_window,
    evaluate_store_whatsapp_production_readiness,
    observe_inbound_whatsapp_message,
    record_customer_inbound_observed,
    simulate_whatsapp_window_check_dev,
)


class WhatsappProductionRealityV2WindowTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_inbound_observations_for_tests()

    def tearDown(self) -> None:
        clear_inbound_observations_for_tests()

    def test_inside_24h_window(self) -> None:
        now = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
        record_customer_inbound_observed(
            customer_phone_key="966500000001",
            observed_at=now - timedelta(hours=2),
        )
        w = evaluate_conversation_window(
            customer_phone_key="966500000001",
            now=now,
        )
        self.assertEqual(w.conversation_window_status, WINDOW_INSIDE)
        t = decide_template_routing(w)
        self.assertTrue(t.freeform_allowed)
        self.assertFalse(t.template_required)

    def test_outside_24h_window(self) -> None:
        now = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
        record_customer_inbound_observed(
            customer_phone_key="966500000002",
            observed_at=now - timedelta(hours=30),
        )
        w = evaluate_conversation_window(
            customer_phone_key="966500000002",
            now=now,
        )
        self.assertEqual(w.conversation_window_status, WINDOW_OUTSIDE)
        t = decide_template_routing(w)
        self.assertFalse(t.freeform_allowed)
        self.assertTrue(t.template_required)

    def test_missing_history_unknown(self) -> None:
        w = evaluate_conversation_window(customer_phone_key="966500000003")
        self.assertEqual(w.conversation_window_status, WINDOW_UNKNOWN)
        t = decide_template_routing(w)
        self.assertFalse(t.freeform_allowed)
        self.assertTrue(t.template_required)

    def test_inbound_observe_logs(self) -> None:
        with patch(
            "services.whatsapp_production_reality_v2._emit_lines"
        ) as mock_emit:
            out = observe_inbound_whatsapp_message("مرحبا", "whatsapp:+966500000004")
        self.assertTrue(out.get("observed"))
        lines = [str(c[0][0]) for c in mock_emit.call_args_list]
        joined = "\n".join(lines)
        self.assertIn("[WA WINDOW CHECK]", joined)
        self.assertIn("[WA TEMPLATE DECISION]", joined)


class WhatsappProductionRealityV2ReadinessTests(unittest.TestCase):
    @patch.dict(os.environ, {"PRODUCTION_MODE": ""}, clear=False)
    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=False)
    def test_provider_disconnected_sandbox_only(self, _mock: object) -> None:
        store = MagicMock()
        store.slug = "demo"
        store.whatsapp_recovery_enabled = True
        store.reason_templates_json = '{"price":{}}'
        r = evaluate_store_whatsapp_production_readiness(store)
        self.assertFalse(r.provider_connected)
        self.assertEqual(r.merchant_readiness_level, READINESS_SANDBOX_ONLY)

    @patch.dict(
        os.environ,
        {
            "PRODUCTION_MODE": "true",
            "TWILIO_ACCOUNT_SID": "ACx",
            "TWILIO_AUTH_TOKEN": "tok",
            "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886",
            "CARTFLOW_PUBLIC_BASE_URL": "https://app.example",
        },
        clear=False,
    )
    @patch(
        "services.cartflow_provider_readiness.get_twilio_readiness",
        return_value={"ready": True},
    )
    def test_partial_when_templates_missing(self, _tw: object) -> None:
        store = MagicMock()
        store.slug = "shop1"
        store.whatsapp_recovery_enabled = True
        store.reason_templates_json = ""
        store.trigger_templates_json = ""
        r = evaluate_store_whatsapp_production_readiness(store)
        self.assertTrue(r.provider_connected)
        self.assertFalse(r.templates_ready)
        self.assertTrue(r.delivery_truth_ready)
        self.assertEqual(r.merchant_readiness_level, READINESS_PARTIAL)

    @patch.dict(
        os.environ,
        {
            "PRODUCTION_MODE": "true",
            "TWILIO_ACCOUNT_SID": "ACx",
            "TWILIO_AUTH_TOKEN": "tok",
            "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886",
            "TWILIO_STATUS_CALLBACK_URL": "https://app.example/webhook/whatsapp/status",
        },
        clear=False,
    )
    @patch(
        "services.cartflow_provider_readiness.get_twilio_readiness",
        return_value={"ready": True},
    )
    def test_production_ready_all_signals(self, _tw: object) -> None:
        store = MagicMock()
        store.slug = "shop2"
        store.whatsapp_recovery_enabled = True
        store.reason_templates_json = '{"price":{"1":"hi"}}'
        store.trigger_templates_json = ""
        r = evaluate_store_whatsapp_production_readiness(store)
        self.assertTrue(r.provider_connected)
        self.assertTrue(r.templates_ready)
        self.assertTrue(r.delivery_truth_ready)
        self.assertEqual(r.merchant_readiness_level, READINESS_PRODUCTION_READY)


class WhatsappWindowSimulateDevTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_inbound_observations_for_tests()

    def tearDown(self) -> None:
        clear_inbound_observations_for_tests()

    def test_simulate_inside_24h_helper(self) -> None:
        out = simulate_whatsapp_window_check_dev(
            phone="966500000010",
            last_inbound_hours_ago=1,
        )
        self.assertTrue(out.get("ok"))
        self.assertEqual(
            (out.get("window") or {}).get("conversation_window_status"),
            WINDOW_INSIDE,
        )
        tpl = out.get("template") or {}
        self.assertTrue(tpl.get("freeform_allowed"))
        self.assertFalse(tpl.get("template_required"))

    def test_simulate_same_phone_inside_then_outside(self) -> None:
        """Regression: second simulate with older inbound must not keep first cache."""
        phone = "966500000099"
        inside = simulate_whatsapp_window_check_dev(
            phone=phone, last_inbound_hours_ago=1
        )
        outside = simulate_whatsapp_window_check_dev(
            phone=phone, last_inbound_hours_ago=25
        )
        self.assertEqual(
            (inside.get("window") or {}).get("conversation_window_status"),
            WINDOW_INSIDE,
        )
        self.assertEqual(
            (outside.get("window") or {}).get("conversation_window_status"),
            WINDOW_OUTSIDE,
        )

    def test_simulate_outside_24h_helper(self) -> None:
        out = simulate_whatsapp_window_check_dev(
            phone="966500000011",
            last_inbound_hours_ago=25,
        )
        self.assertTrue(out.get("ok"))
        self.assertEqual(
            (out.get("window") or {}).get("conversation_window_status"),
            WINDOW_OUTSIDE,
        )
        tpl = out.get("template") or {}
        self.assertFalse(tpl.get("freeform_allowed"))
        self.assertTrue(tpl.get("template_required"))

    @patch.dict(os.environ, {"ENV": "development"}, clear=False)
    def test_dev_endpoint_inside_24h(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/dev/whatsapp-window-simulate",
            json={"phone": "966500000012", "last_inbound_hours_ago": 1},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(
            (data.get("window") or {}).get("conversation_window_status"),
            WINDOW_INSIDE,
        )

    @patch.dict(os.environ, {"ENV": "development"}, clear=False)
    def test_dev_endpoint_outside_24h(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/dev/whatsapp-window-simulate",
            json={"phone": "966500000013", "last_inbound_hours_ago": 25},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(
            (data.get("window") or {}).get("conversation_window_status"),
            WINDOW_OUTSIDE,
        )

    @patch.dict(os.environ, {"ENV": "production"}, clear=False)
    def test_dev_endpoint_blocked_outside_development(self) -> None:
        client = TestClient(app)
        resp = client.post(
            "/dev/whatsapp-window-simulate",
            json={"phone": "966500000014", "last_inbound_hours_ago": 1},
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
