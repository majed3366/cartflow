# -*- coding: utf-8 -*-
"""Phase 0 — journey identity shadow resolver (observation only)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from services.journey_identity_resolver_v1 import (
    has_stable_cart_id,
    is_synthetic_cart_id,
    journey_identity_shadow_logging_enabled,
    maybe_log_journey_identity_shadow,
    resolve_journey_identity_shadow,
)


class JourneyIdentityStableCartRulesTests(unittest.TestCase):
    def test_synthetic_cf_w_prefix(self) -> None:
        self.assertTrue(is_synthetic_cart_id("cf_w_abc123"))
        self.assertFalse(has_stable_cart_id("cf_w_abc123"))

    def test_synthetic_fp_prefix(self) -> None:
        self.assertTrue(is_synthetic_cart_id("fp:deadbeef"))
        self.assertFalse(has_stable_cart_id("fp:deadbeef"))

    def test_stable_platform_cart_id(self) -> None:
        self.assertFalse(is_synthetic_cart_id("zid-cart-99881"))
        self.assertTrue(has_stable_cart_id("zid-cart-99881"))


class JourneyIdentityShadowResolverTests(unittest.TestCase):
    def test_session_id_only(self) -> None:
        payload = {
            "store": "demo",
            "session_id": "s_only_1",
        }
        r = resolve_journey_identity_shadow(payload)
        self.assertTrue(r.bid_rk.endswith(":s_only_1"))
        self.assertEqual(r.jid_rk, "")
        self.assertEqual(r.recommended_rk, r.bid_rk)
        self.assertEqual(r.current_rk, r.bid_rk)
        self.assertFalse(r.mismatch)

    def test_session_id_and_stable_cart_id(self) -> None:
        payload = {
            "store": "demo",
            "session_id": "s_mismatch_1",
            "cart_id": "platform-cart-42",
        }
        r = resolve_journey_identity_shadow(payload)
        self.assertEqual(r.bid_rk, "demo:s_mismatch_1")
        self.assertEqual(r.jid_rk, "demo:platform-cart-42")
        self.assertEqual(r.recommended_rk, r.jid_rk)
        self.assertEqual(r.current_rk, r.bid_rk)
        self.assertTrue(r.mismatch)
        self.assertIn("session", r.mismatch_reason)

    def test_synthetic_cart_id_ignored_for_jid(self) -> None:
        payload = {
            "store": "demo",
            "session_id": "s_syn_1",
            "cart_id": "cf_w_abc123",
        }
        r = resolve_journey_identity_shadow(payload)
        self.assertEqual(r.jid_rk, "")
        self.assertEqual(r.recommended_rk, r.bid_rk)
        self.assertFalse(r.mismatch)
        self.assertTrue(r.is_synthetic_cart_id)

    def test_cart_id_only_no_crash(self) -> None:
        payload = {
            "store": "demo",
            "cart_id": "external-cart-77",
        }
        r = resolve_journey_identity_shadow(payload)
        self.assertEqual(r.jid_rk, "demo:external-cart-77")
        self.assertEqual(r.recommended_rk, r.jid_rk)
        self.assertEqual(r.current_rk, r.jid_rk)
        self.assertFalse(r.mismatch)


class JourneyIdentityShadowFlagTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev = os.environ.get("CARTFLOW_JOURNEY_IDENTITY_MODE")

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("CARTFLOW_JOURNEY_IDENTITY_MODE", None)
        else:
            os.environ["CARTFLOW_JOURNEY_IDENTITY_MODE"] = self._prev

    def test_flag_off_emits_no_shadow_log(self) -> None:
        os.environ["CARTFLOW_JOURNEY_IDENTITY_MODE"] = "off"
        self.assertFalse(journey_identity_shadow_logging_enabled())
        with patch(
            "services.journey_identity_resolver_v1.emit_journey_identity_shadow_log"
        ) as mock_emit:
            out = maybe_log_journey_identity_shadow(
                {"store": "demo", "session_id": "s1"},
                source="test_off",
            )
        self.assertIsNone(out)
        mock_emit.assert_not_called()

    def test_flag_shadow_emits_log(self) -> None:
        os.environ["CARTFLOW_JOURNEY_IDENTITY_MODE"] = "shadow"
        self.assertTrue(journey_identity_shadow_logging_enabled())
        with patch(
            "services.journey_identity_resolver_v1.emit_journey_identity_shadow_log"
        ) as mock_emit:
            out = maybe_log_journey_identity_shadow(
                {
                    "store": "demo",
                    "session_id": "s_shadow_1",
                    "cart_id": "real-cart-1",
                },
                source="test_shadow",
            )
        self.assertIsNotNone(out)
        mock_emit.assert_called_once()
        args, kwargs = mock_emit.call_args
        self.assertEqual(kwargs.get("source"), "test_shadow")
        self.assertTrue(args[0].mismatch)


class JourneyIdentityNoBehaviorRegressionTests(unittest.TestCase):
    def test_recovery_key_from_payload_unchanged(self) -> None:
        from main import _recovery_key_from_payload

        payload = {
            "store": "demo",
            "session_id": "s_reg_1",
            "cart_id": "cart-reg-1",
        }
        before = _recovery_key_from_payload(payload)
        resolve_journey_identity_shadow(payload)
        after = _recovery_key_from_payload(payload)
        self.assertEqual(before, after)
        self.assertEqual(before, "demo:s_reg_1")


if __name__ == "__main__":
    unittest.main()
