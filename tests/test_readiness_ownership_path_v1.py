# -*- coding: utf-8 -*-
"""Readiness Ownership Path v1 — every blocker has an owner."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from services.merchant_production_readiness_path_v1 import (
    _production_path_checks,
)
from services.merchant_onboarding_reality_v1 import (
    LEVEL_PRODUCTION_READY,
    MerchantOnboardingReality,
)
from services.readiness_ownership_path_v1 import (
    OWNER_CARTFLOW_OPS,
    OWNER_MERCHANT,
    OWNER_PROVIDER,
    OWNERSHIP_BY_CODE,
    build_readiness_ownership_path,
    owners_for_code,
)


class ReadinessOwnershipPathV1Tests(unittest.TestCase):
    def test_every_catalog_code_has_owner(self) -> None:
        reality = MerchantOnboardingReality(
            onboarding_state=LEVEL_PRODUCTION_READY,
        )
        for item in _production_path_checks(reality):
            owners = owners_for_code(item.code)
            self.assertTrue(owners, msg=item.code)
            self.assertIn(item.code, OWNERSHIP_BY_CODE)

    def test_templates_approved_owners(self) -> None:
        owners = owners_for_code("templates_approved")
        self.assertIn(OWNER_MERCHANT, owners)
        self.assertIn(OWNER_PROVIDER, owners)

    def test_delivery_truth_owner_ops(self) -> None:
        owners = owners_for_code("delivery_truth")
        self.assertEqual(owners, [OWNER_CARTFLOW_OPS])

    @patch.dict(os.environ, {"PRODUCTION_MODE": ""}, clear=False)
    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=False)
    @patch("services.cartflow_onboarding_readiness._phone_coverage_readonly", return_value=(False, False))
    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_sandbox_blockers_all_have_owners(
        self, mock_ms: object, *_mocks: object
    ) -> None:
        mock_ms.return_value = {
            "first_cart_detected": False,
            "first_recovery_scheduled": False,
            "first_whatsapp_sent": False,
            "first_reply_received": False,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.slug = "own-demo"
        store.zid_store_id = "z1"
        store.access_token = "tok"
        store.is_active = True
        store.recovery_attempts = 2
        store.cartflow_widget_enabled = True
        store.whatsapp_recovery_enabled = True
        store.reason_templates_json = '{"price":{"1":"x"}}'
        store.recovery_delay_minutes = 10
        store.store_whatsapp_number = "+966500000001"
        own = build_readiness_ownership_path(store, emit_logs=False, emit_path_logs=False)
        self.assertTrue(own.blockers)
        for b in own.blockers:
            self.assertTrue(b.owners, msg=b.code)
            self.assertTrue(b.owners_display_ar)
            self.assertTrue(b.action_ar)
            self.assertTrue(b.expected_result_ar)
        self.assertTrue(own.admin_knows_who_should_act)

    @patch("builtins.print")
    def test_readiness_owner_log(self, mock_print: object) -> None:
        build_readiness_ownership_path(None, emit_logs=True, emit_path_logs=False)
        printed = " ".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("[READINESS OWNER]", printed)
        self.assertIn("owner=", printed)

    def test_admin_can_know_who_should_act(self) -> None:
        own = build_readiness_ownership_path(None, emit_logs=False, emit_path_logs=False)
        self.assertTrue(own.admin_knows_who_should_act)


if __name__ == "__main__":
    unittest.main()
