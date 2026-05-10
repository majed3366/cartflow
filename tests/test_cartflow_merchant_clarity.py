# -*- coding: utf-8 -*-
"""Merchant operational clarity layer (additive copy only)."""

from __future__ import annotations

import unittest

from services import cartflow_merchant_clarity as mc


class CartflowMerchantClarityTests(unittest.TestCase):
    def test_waiting_is_not_failure_for_queued(self) -> None:
        self.assertTrue(mc.status_waiting_not_failure("queued"))
        p: dict = {}
        mc.attach_merchant_clarity_to_normal_recovery_payload(
            p,
            phase_key="pending_send",
            coarse="pending",
            latest_log_status="queued",
            blocker_key=None,
            behavioral={},
            sent_ct=0,
            phase_steps=[{"done": False, "current": True, "label_ar": "بانتظار الإرسال"}],
        )
        self.assertTrue(p.get("merchant_clarity_waiting_is_normal"))
        out = p.get("merchant_clarity_outcome_ar") or ""
        self.assertIn("طبيعي", out)

    def test_intentional_stop_for_customer_replied_blocker(self) -> None:
        self.assertTrue(
            mc.status_intentional_customer_stop(
                "skipped_followup_customer_replied",
                "customer_replied",
            )
        )
        p: dict = {}
        mc.attach_merchant_clarity_to_normal_recovery_payload(
            p,
            phase_key="behavioral_replied",
            coarse="replied",
            latest_log_status="skipped_followup_customer_replied",
            blocker_key="customer_replied",
            behavioral={},
            sent_ct=1,
            phase_steps=[],
        )
        self.assertTrue(p.get("merchant_clarity_intentional_stop"))
        self.assertEqual(p.get("merchant_clarity_group_ar"), mc.GROUP_STOPPED_CUSTOMER)

    def test_duplicate_blocked_not_marked_failure(self) -> None:
        p: dict = {}
        mc.attach_merchant_clarity_to_normal_recovery_payload(
            p,
            phase_key="first_message_sent",
            coarse="sent",
            latest_log_status="skipped_duplicate",
            blocker_key="duplicate_attempt_blocked",
            behavioral={},
            sent_ct=1,
            phase_steps=[],
        )
        self.assertEqual(p.get("merchant_clarity_group_ar"), mc.GROUP_PROTECTED)
        out = p.get("merchant_clarity_outcome_ar") or ""
        self.assertNotIn("فشل", out.lower())

    def test_return_to_site_overrides_duplicate_blocker_presentation(self) -> None:
        p: dict = {}
        mc.attach_merchant_clarity_to_normal_recovery_payload(
            p,
            phase_key="customer_returned",
            coarse="returned",
            latest_log_status="skipped_duplicate",
            blocker_key="duplicate_attempt_blocked",
            behavioral={"user_returned_to_site": True},
            sent_ct=0,
            phase_steps=[],
        )
        self.assertEqual(p.get("merchant_clarity_group_ar"), mc.GROUP_STOPPED_CUSTOMER)
        self.assertTrue(p.get("merchant_clarity_intentional_stop"))
        h = p.get("merchant_clarity_headline_ar") or ""
        self.assertIn("موقع", h)
        o = p.get("merchant_clarity_outcome_ar") or ""
        self.assertIn("عودة", o)

    def test_headline_consistency_reply(self) -> None:
        p: dict = {}
        mc.attach_merchant_clarity_to_normal_recovery_payload(
            p,
            phase_key="behavioral_replied",
            coarse="replied",
            latest_log_status="mock_sent",
            blocker_key=None,
            behavioral={"customer_replied": True},
            sent_ct=1,
            phase_steps=[],
        )
        h = p.get("merchant_clarity_headline_ar") or ""
        self.assertIn("تفاعل", h)

    def test_runtime_section_supplements_onboarding(self) -> None:
        sec = mc.build_merchant_clarity_runtime_section(
            {"onboarding_ready": False, "sandbox_mode_active": True}
        )
        self.assertEqual(sec.get("layer_version"), "1")
        self.assertIn("إعداد", sec.get("trust_supplement_ar") or "")

    def test_onboarding_enrich_adds_field(self) -> None:
        vis: dict = {}
        mc.enrich_onboarding_visibility(
            vis,
            {"sandbox_mode_active": True, "blocking_steps": ["recovery_disabled"]},
        )
        self.assertIn("merchant_operational_clarity_ar", vis)

    def test_no_contradictory_group_for_sent_success(self) -> None:
        p: dict = {}
        mc.attach_merchant_clarity_to_normal_recovery_payload(
            p,
            phase_key="first_message_sent",
            coarse="sent",
            latest_log_status="mock_sent",
            blocker_key=None,
            behavioral={},
            sent_ct=1,
            phase_steps=[],
        )
        self.assertEqual(p.get("merchant_clarity_group_ar"), mc.GROUP_NORMAL)

    def test_purchase_complete_positive_tone(self) -> None:
        p: dict = {}
        mc.attach_merchant_clarity_to_normal_recovery_payload(
            p,
            phase_key="stopped_purchase",
            coarse="stopped",
            latest_log_status="stopped_converted",
            blocker_key="purchase_completed",
            behavioral={},
            sent_ct=1,
            phase_steps=[],
        )
        self.assertEqual(p.get("merchant_clarity_group_ar"), mc.GROUP_NORMAL)


if __name__ == "__main__":
    unittest.main()
