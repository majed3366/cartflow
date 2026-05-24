# -*- coding: utf-8 -*-
"""Production 24h / template window enforcement on Twilio send path."""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from services.whatsapp_production_reality_v2 import (
    WINDOW_INSIDE,
    WINDOW_OUTSIDE,
    WINDOW_UNKNOWN,
    clear_inbound_observations_for_tests,
    enforce_whatsapp_template_window_before_send,
    evaluate_whatsapp_template_enforcement,
    provider_templates_approved_for_store,
    record_customer_inbound_observed,
)
from services.whatsapp_send import resolve_whatsapp_recovery_log_status, send_whatsapp


class TestWhatsappTemplateEnforcementV1(unittest.TestCase):
    def setUp(self) -> None:
        clear_inbound_observations_for_tests()

    def tearDown(self) -> None:
        clear_inbound_observations_for_tests()

    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=False)
    def test_sandbox_never_blocks_cold_cart(self, _prod: object) -> None:
        v = evaluate_whatsapp_template_enforcement(
            customer_phone="966500000099",
            store_slug="demo",
        )
        self.assertEqual(v["mode"], "sandbox")
        self.assertEqual(v["action"], "send")
        self.assertFalse(v["blocked"])
        block = enforce_whatsapp_template_window_before_send(
            customer_phone="966500000099",
            store_slug="demo",
        )
        self.assertIsNone(block)

    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=True)
    def test_production_blocks_outside_24h_without_approval(self, _prod: object) -> None:
        now = datetime.now(timezone.utc)
        record_customer_inbound_observed(
            customer_phone_key="966500000010",
            observed_at=now - timedelta(hours=30),
        )
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CARTFLOW_WHATSAPP_PROVIDER_TEMPLATES_APPROVED", None)
            v = evaluate_whatsapp_template_enforcement(
                customer_phone="966500000010",
            )
        self.assertEqual(v["window_24h"], WINDOW_OUTSIDE)
        self.assertTrue(v["template_required"])
        self.assertFalse(v["template_available"])
        self.assertEqual(v["action"], "block")
        block = enforce_whatsapp_template_window_before_send(
            customer_phone="966500000010",
        )
        self.assertIsNotNone(block)
        self.assertEqual(block.get("error"), "template_required_outside_24h")

    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=True)
    def test_production_allows_inside_24h(self, _prod: object) -> None:
        now = datetime.now(timezone.utc)
        record_customer_inbound_observed(
            customer_phone_key="966500000011",
            observed_at=now - timedelta(hours=1),
        )
        v = evaluate_whatsapp_template_enforcement(
            customer_phone="966500000011",
        )
        self.assertEqual(v["window_24h"], WINDOW_INSIDE)
        self.assertEqual(v["action"], "send")
        self.assertIsNone(
            enforce_whatsapp_template_window_before_send(
                customer_phone="966500000011",
            )
        )

    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=True)
    @patch.dict(
        os.environ,
        {"CARTFLOW_WHATSAPP_PROVIDER_TEMPLATES_APPROVED": "1"},
        clear=False,
    )
    def test_production_allows_outside_24h_with_ops_approval_flag(
        self, _prod: object
    ) -> None:
        now = datetime.now(timezone.utc)
        record_customer_inbound_observed(
            customer_phone_key="966500000012",
            observed_at=now - timedelta(hours=48),
        )
        self.assertTrue(provider_templates_approved_for_store(None))
        v = evaluate_whatsapp_template_enforcement(
            customer_phone="966500000012",
        )
        self.assertEqual(v["window_24h"], WINDOW_OUTSIDE)
        self.assertTrue(v["template_available"])
        self.assertEqual(v["action"], "send")

    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=True)
    def test_unknown_window_blocks_without_approval(self, _prod: object) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CARTFLOW_WHATSAPP_PROVIDER_TEMPLATES_APPROVED", None)
            v = evaluate_whatsapp_template_enforcement(
                customer_phone="966500000013",
            )
        self.assertEqual(v["window_24h"], WINDOW_UNKNOWN)
        self.assertEqual(v["action"], "block")

    def test_blocked_log_status_mapping(self) -> None:
        st = resolve_whatsapp_recovery_log_status(
            {
                "ok": False,
                "error": "template_required_outside_24h",
                "log_status": "blocked_template_required",
            }
        )
        self.assertEqual(st, "blocked_template_required")

    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=True)
    @patch("services.whatsapp_send.Client")
    def test_send_whatsapp_skips_twilio_when_blocked(
        self, mock_client: object, _prod: object
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "TWILIO_ACCOUNT_SID": "ACtest",
                "TWILIO_AUTH_TOKEN": "tok",
                "TWILIO_WHATSAPP_FROM": "whatsapp:+15550001111",
            },
            clear=False,
        ):
            os.environ.pop("CARTFLOW_WHATSAPP_PROVIDER_TEMPLATES_APPROVED", None)
            out = send_whatsapp("966500000014", "hello recovery")
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "template_required_outside_24h")
        mock_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
