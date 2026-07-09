# -*- coding: utf-8 -*-
"""Cart Page V2 Phase 0 — primary action projection tests."""
from __future__ import annotations

import os
import unittest

from services.cart_page_primary_action_v1 import (
    ENV_PRIMARY_ACTION,
    KEY_ARCHIVE,
    KEY_CONTACT,
    KEY_FOLLOW_UP,
    KEY_NO_ACTION,
    KEY_REOPEN,
    KEY_REVIEW,
    KEY_WAIT,
    ROW_KEY,
    attach_cart_page_primary_action_v1,
    ensure_normal_carts_primary_action_v1,
    project_cart_page_primary_action_v1,
)


class CartPagePrimaryActionProjectionV1Tests(unittest.TestCase):
    def test_automatic_states_project_to_wait(self) -> None:
        for state in (
            "active",
            "waiting_first_send",
            "waiting_customer_reply",
            "customer_reply",
            "customer_engaged",
            "return_to_site",
            "waiting_purchase_window",
            "waiting_next_scheduled",
        ):
            row = {
                "customer_lifecycle_state": state,
                "customer_lifecycle_dashboard_action": "archive",
            }
            out = project_cart_page_primary_action_v1(row)
            self.assertEqual(out["key"], KEY_WAIT, msg=state)
            self.assertNotEqual(out["key"], KEY_ARCHIVE)
            if state in ("return_to_site", "waiting_purchase_window"):
                self.assertNotIn("secondary_key", out)
            else:
                self.assertEqual(out.get("secondary_key"), KEY_ARCHIVE)
                self.assertTrue(out.get("secondary_demoted"))

    def test_intervention_contact_executable(self) -> None:
        out = project_cart_page_primary_action_v1(
            {
                "customer_lifecycle_state": "needs_intervention",
                "customer_lifecycle_dashboard_action": "archive",
                "merchant_decision_key": "contact_customer",
                "merchant_intervention_executable": True,
                "merchant_has_customer_phone": True,
            }
        )
        self.assertEqual(out["key"], KEY_CONTACT)
        self.assertEqual(out.get("secondary_key"), KEY_ARCHIVE)
        self.assertTrue(out.get("secondary_demoted"))

    def test_intervention_no_phone_follow_up(self) -> None:
        out = project_cart_page_primary_action_v1(
            {
                "customer_lifecycle_state": "needs_intervention",
                "merchant_decision_key": "obtain_contact",
                "merchant_has_customer_phone": False,
                "customer_lifecycle_merchant_needed_ar": "نعم",
                "customer_lifecycle_dashboard_action": "archive",
            }
        )
        self.assertEqual(out["key"], KEY_FOLLOW_UP)

    def test_intervention_channel_follow_up(self) -> None:
        out = project_cart_page_primary_action_v1(
            {
                "customer_lifecycle_state": "needs_intervention",
                "merchant_decision_key": "fix_channel",
                "customer_lifecycle_label_ar": "يحتاج إعداد",
                "customer_lifecycle_dashboard_action": "archive",
            }
        )
        self.assertEqual(out["key"], KEY_FOLLOW_UP)

    def test_intervention_not_executable_review(self) -> None:
        out = project_cart_page_primary_action_v1(
            {
                "customer_lifecycle_state": "needs_intervention",
                "customer_lifecycle_merchant_needed_ar": "نعم",
                "merchant_intervention_executable": False,
                "merchant_has_customer_phone": True,
                "customer_lifecycle_dashboard_action": "archive",
            }
        )
        self.assertEqual(out["key"], KEY_REVIEW)

    def test_completed_projects_to_no_action(self) -> None:
        for row in (
            {"customer_lifecycle_state": "completed"},
            {
                "customer_lifecycle_state": "completed",
                "customer_lifecycle_completed_variant": "purchased",
            },
            {"customer_lifecycle_state": "recovery_followup_complete"},
        ):
            out = project_cart_page_primary_action_v1(row)
            self.assertEqual(out["key"], KEY_NO_ACTION)

    def test_archived_projects_to_reopen(self) -> None:
        for row in (
            {
                "customer_lifecycle_state": "archived",
                "customer_lifecycle_dashboard_action": "reopen",
            },
            {
                "customer_lifecycle_state": "waiting_first_send",
                "customer_lifecycle_is_archived_visual": True,
                "customer_lifecycle_dashboard_action": "reopen",
            },
        ):
            out = project_cart_page_primary_action_v1(row)
            self.assertEqual(out["key"], KEY_REOPEN)

    def test_archive_never_co_primary_for_active(self) -> None:
        row = {
            "customer_lifecycle_state": "waiting_first_send",
            "customer_lifecycle_dashboard_action": "archive",
        }
        out = project_cart_page_primary_action_v1(row)
        self.assertEqual(out["key"], KEY_WAIT)
        self.assertNotEqual(out["key"], KEY_ARCHIVE)
        self.assertEqual(out.get("secondary_key"), KEY_ARCHIVE)
        self.assertTrue(out.get("secondary_demoted"))

    def test_vip_manual_follow_up(self) -> None:
        out = project_cart_page_primary_action_v1(
            {
                "customer_lifecycle_state": "needs_intervention",
                "is_vip_lane": True,
                "customer_lifecycle_dashboard_action": "archive",
            }
        )
        self.assertEqual(out["key"], KEY_FOLLOW_UP)

    def test_attach_and_ensure_payload(self) -> None:
        os.environ[ENV_PRIMARY_ACTION] = "1"
        row: dict = {"customer_lifecycle_state": "waiting_customer_reply"}
        attach_cart_page_primary_action_v1(row)
        self.assertIn(ROW_KEY, row)
        self.assertEqual(row[ROW_KEY]["key"], KEY_WAIT)

        payload = {
            "merchant_carts_page_rows": [
                {"customer_lifecycle_state": "completed"},
            ],
            "merchant_archived_carts_page_rows": [
                {
                    "customer_lifecycle_state": "archived",
                    "customer_lifecycle_dashboard_action": "reopen",
                },
            ],
        }
        ensure_normal_carts_primary_action_v1(payload)
        self.assertEqual(
            payload["merchant_carts_page_rows"][0][ROW_KEY]["key"], KEY_NO_ACTION
        )
        self.assertEqual(
            payload["merchant_archived_carts_page_rows"][0][ROW_KEY]["key"], KEY_REOPEN
        )

    def test_flag_off_skips_attach(self) -> None:
        os.environ[ENV_PRIMARY_ACTION] = "0"
        try:
            row: dict = {"customer_lifecycle_state": "waiting_first_send"}
            attach_cart_page_primary_action_v1(row)
            self.assertNotIn(ROW_KEY, row)
        finally:
            os.environ[ENV_PRIMARY_ACTION] = "1"


if __name__ == "__main__":
    unittest.main()
