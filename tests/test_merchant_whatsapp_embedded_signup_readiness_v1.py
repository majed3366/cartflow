# -*- coding: utf-8 -*-
"""Tests for WhatsApp Embedded Signup readiness foundation V1."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from services.merchant_whatsapp_embedded_signup_readiness_v1 import (
    EMBEDDED_SIGNUP_CONNECTED,
    EMBEDDED_SIGNUP_FAILED,
    EMBEDDED_SIGNUP_NOT_STARTED,
    EMBEDDED_SIGNUP_PAIRING_REQUIRED,
    embedded_signup_fields_for_api,
    evaluate_embedded_signup_readiness,
)
from services.merchant_whatsapp_mode_v1 import (
    WHATSAPP_MODE_CARTFLOW_MANAGED,
    WHATSAPP_MODE_MERCHANT_WHATSAPP,
)


class EmbeddedSignupReadinessTests(unittest.TestCase):
    def test_path_a_not_applicable(self) -> None:
        store = SimpleNamespace(
            whatsapp_mode=WHATSAPP_MODE_CARTFLOW_MANAGED,
            store_whatsapp_number="+966500000111",
            whatsapp_recovery_enabled=True,
        )
        ev = evaluate_embedded_signup_readiness(store)
        self.assertFalse(ev.applicable)
        self.assertEqual(ev.status, EMBEDDED_SIGNUP_NOT_STARTED)

    def test_path_b_not_started_without_setup(self) -> None:
        store = SimpleNamespace(
            whatsapp_mode=WHATSAPP_MODE_MERCHANT_WHATSAPP,
            whatsapp_recovery_enabled=False,
            store_whatsapp_number="",
            whatsapp_onboarding_journey=None,
            whatsapp_embedded_signup_status=None,
        )
        ev = evaluate_embedded_signup_readiness(store)
        self.assertTrue(ev.applicable)
        self.assertEqual(ev.status, EMBEDDED_SIGNUP_NOT_STARTED)
        self.assertTrue(ev.launch_ready)

    def test_path_b_pairing_required_with_number_and_recovery(self) -> None:
        store = SimpleNamespace(
            whatsapp_mode=WHATSAPP_MODE_MERCHANT_WHATSAPP,
            store_whatsapp_number="+966500000222",
            whatsapp_recovery_enabled=True,
            whatsapp_onboarding_journey="existing_whatsapp_business",
            whatsapp_embedded_signup_status=None,
        )
        ev = evaluate_embedded_signup_readiness(store)
        self.assertTrue(ev.applicable)
        self.assertEqual(ev.status, EMBEDDED_SIGNUP_PAIRING_REQUIRED)

    def test_persisted_connected(self) -> None:
        store = SimpleNamespace(
            whatsapp_mode=WHATSAPP_MODE_MERCHANT_WHATSAPP,
            whatsapp_embedded_signup_status=EMBEDDED_SIGNUP_CONNECTED,
        )
        ev = evaluate_embedded_signup_readiness(store)
        self.assertEqual(ev.status, EMBEDDED_SIGNUP_CONNECTED)

    def test_persisted_failed(self) -> None:
        store = SimpleNamespace(
            whatsapp_mode=WHATSAPP_MODE_MERCHANT_WHATSAPP,
            whatsapp_embedded_signup_status=EMBEDDED_SIGNUP_FAILED,
        )
        ev = evaluate_embedded_signup_readiness(store)
        self.assertEqual(ev.status, EMBEDDED_SIGNUP_FAILED)

    def test_api_block_shape(self) -> None:
        store = SimpleNamespace(
            whatsapp_mode=WHATSAPP_MODE_MERCHANT_WHATSAPP,
            store_whatsapp_number="+966500000333",
            whatsapp_recovery_enabled=True,
            whatsapp_onboarding_journey="existing_whatsapp_business",
        )
        block = embedded_signup_fields_for_api(store)["whatsapp_embedded_signup"]
        self.assertIn("status", block)
        self.assertIn("connect_href", block)
        self.assertEqual(block["connect_href"], "/dashboard#whatsapp-connect")
        self.assertTrue(block["foundation_only"])


if __name__ == "__main__":
    unittest.main()
