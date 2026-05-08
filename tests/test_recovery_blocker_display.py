# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from services.recovery_blocker_display import (
    get_recovery_blocker_display_state,
    log_status_to_recovery_blocker_key,
    recovery_blocker_from_latest_log_status,
)


class RecoveryBlockerDisplayTests(unittest.TestCase):
    def test_missing_customer_phone_label(self) -> None:
        d = get_recovery_blocker_display_state("missing_customer_phone")
        self.assertEqual(d.get("label_ar"), "لا يوجد رقم عميل")
        self.assertEqual(d.get("severity"), "warning")

    def test_whatsapp_failed_label(self) -> None:
        d = get_recovery_blocker_display_state("whatsapp_failed")
        self.assertEqual(d.get("label_ar"), "فشل إرسال واتساب")
        self.assertEqual(d.get("severity"), "error")

    def test_customer_replied_label(self) -> None:
        d = get_recovery_blocker_display_state("customer_replied")
        self.assertEqual(d.get("label_ar"), "العميل رد")

    def test_user_returned_label(self) -> None:
        d = get_recovery_blocker_display_state("user_returned")
        self.assertEqual(d.get("label_ar"), "عاد العميل للموقع")

    def test_log_status_maps_skipped_phone(self) -> None:
        self.assertEqual(
            log_status_to_recovery_blocker_key("skipped_no_verified_phone"),
            "missing_customer_phone",
        )

    def test_log_status_maps_whatsapp_failed(self) -> None:
        self.assertEqual(log_status_to_recovery_blocker_key("whatsapp_failed"), "whatsapp_failed")

    def test_recovery_success_status_returns_no_blocker(self) -> None:
        self.assertIsNone(log_status_to_recovery_blocker_key("mock_sent"))
        self.assertIsNone(recovery_blocker_from_latest_log_status("mock_sent"))

    def test_unknown_reason_falls_back(self) -> None:
        d = get_recovery_blocker_display_state("totally_unknown_reason_xyz")
        self.assertEqual(d.get("key"), "automation_disabled")
