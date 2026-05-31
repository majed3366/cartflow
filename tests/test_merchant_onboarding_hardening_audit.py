# -*- coding: utf-8 -*-
"""Onboarding V2 hardening audit — real merchant journey scenarios 1–10."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from services.merchant_onboarding_journey_v2 import build_activation_journey_v2

_MILESTONES_EMPTY = {
    "first_cart_detected": False,
    "first_recovery_scheduled": False,
    "first_whatsapp_sent": False,
    "first_reply_received": False,
    "first_recovered_cart": False,
}
_MILESTONES_WIDGET_ONLY = {
    **_MILESTONES_EMPTY,
    "first_cart_detected": True,
}
_MILESTONES_SANDBOX_VERIFIED = {
    **_MILESTONES_EMPTY,
    "first_cart_detected": True,
    "first_recovery_scheduled": True,
    "first_whatsapp_sent": True,
}


def _store(**overrides: object) -> MagicMock:
    s = MagicMock()
    s.id = 42
    s.zid_store_id = "shop-audit"
    s.merchant_user_id = 99
    s.access_token = ""
    s.store_whatsapp_number = ""
    s.whatsapp_recovery_enabled = True
    s.reason_templates_json = ""
    s.cartflow_widget_enabled = False
    s.is_active = True
    s.recovery_attempts = 3
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def _step(journey: object, step_id: str) -> object:
    return next(s for s in journey.steps if s.step_id == step_id)


@patch(
    "services.cartflow_onboarding_readiness._phone_coverage_readonly",
    return_value=(True, True),
)
@patch("services.cartflow_onboarding_readiness._milestones_readonly")
@patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=False)
class OnboardingHardeningAudit(unittest.TestCase):
    """PASS/FAIL gates for merchant onboarding truth."""

    def test_scenario_1_fresh_merchant(
        self, _mock_real: object, mock_ms: object, _mock_phone: object
    ) -> None:
        mock_ms.return_value = dict(_MILESTONES_EMPTY)
        store = _store()
        j = build_activation_journey_v2(store, merchant_user_id=99)
        self.assertEqual(j.completed_steps, 1, "only account may be complete")
        self.assertEqual(j.total_steps, 6)
        self.assertFalse(j.onboarding_complete)
        self.assertTrue(_step(j, "account").is_complete)
        for sid in (
            "widget_test",
            "connect_store",
            "configure_whatsapp",
            "review_messages",
            "ready_for_launch",
        ):
            st = _step(j, sid)
            self.assertFalse(st.is_complete, sid)
            self.assertIn(st.status, ("current", "locked"), sid)
        self.assertFalse(j.nav_locks["settings"].unlocked)
        self.assertFalse(j.nav_locks["whatsapp"].unlocked)
        self.assertFalse(j.nav_locks["trigger-templates"].unlocked)
        self.assertFalse(j.nav_locks["widget"].unlocked)

    def test_scenario_2_widget_test_only(
        self, _mock_real: object, mock_ms: object, _mock_phone: object
    ) -> None:
        mock_ms.return_value = dict(_MILESTONES_WIDGET_ONLY)
        store = _store(cartflow_widget_enabled=True)
        j = build_activation_journey_v2(store, merchant_user_id=99)
        self.assertEqual(j.completed_steps, 2)
        self.assertTrue(_step(j, "widget_test").is_complete)
        self.assertFalse(_step(j, "connect_store").is_complete)
        self.assertTrue(j.nav_locks["settings"].unlocked)
        self.assertFalse(j.nav_locks["whatsapp"].unlocked)
        self.assertFalse(j.nav_locks["trigger-templates"].unlocked)

    def test_scenario_3_store_connected(
        self, _mock_real: object, mock_ms: object, _mock_phone: object
    ) -> None:
        mock_ms.return_value = dict(_MILESTONES_SANDBOX_VERIFIED)
        store = _store(access_token="tok-live", cartflow_widget_enabled=True)
        j = build_activation_journey_v2(store, merchant_user_id=99)
        self.assertTrue(_step(j, "connect_store").is_complete)
        self.assertTrue(j.nav_locks["whatsapp"].unlocked)
        self.assertFalse(j.nav_locks["trigger-templates"].unlocked)
        self.assertGreater(j.completed_steps, 2)

    def test_scenario_4_whatsapp_configured(
        self, _mock_real: object, mock_ms: object, _mock_phone: object
    ) -> None:
        mock_ms.return_value = dict(_MILESTONES_SANDBOX_VERIFIED)
        store = _store(
            access_token="tok-live",
            store_whatsapp_number="+966500000001",
            whatsapp_recovery_enabled=True,
            cartflow_widget_enabled=True,
        )
        j = build_activation_journey_v2(store, merchant_user_id=99)
        self.assertTrue(_step(j, "configure_whatsapp").is_complete)
        self.assertTrue(j.nav_locks["trigger-templates"].unlocked)

    def test_scenario_5_templates_reviewed(
        self, _mock_real: object, mock_ms: object, _mock_phone: object
    ) -> None:
        mock_ms.return_value = dict(_MILESTONES_SANDBOX_VERIFIED)
        store = _store(
            access_token="tok-live",
            store_whatsapp_number="+966500000001",
            reason_templates_json='{"price":{"ar":"test"}}',
            cartflow_widget_enabled=False,
        )
        j = build_activation_journey_v2(store, merchant_user_id=99)
        self.assertTrue(_step(j, "review_messages").is_complete)
        self.assertFalse(_step(j, "ready_for_launch").is_complete)
        self.assertFalse(j.onboarding_complete)

    def test_scenario_6_fully_activated(
        self, _mock_real: object, mock_ms: object, _mock_phone: object
    ) -> None:
        mock_ms.return_value = dict(_MILESTONES_SANDBOX_VERIFIED)
        store = _store(
            access_token="tok-live",
            store_whatsapp_number="+966500000001",
            reason_templates_json='{"price":{"ar":"test"}}',
            cartflow_widget_enabled=True,
        )
        j = build_activation_journey_v2(store, merchant_user_id=99)
        self.assertEqual(j.completed_steps, 6)
        self.assertTrue(j.onboarding_complete)
        self.assertFalse(j.show_journey)
        self.assertIsNotNone(j.readiness_card)
        assert j.readiness_card is not None
        checklist = " ".join(j.readiness_card.checklist_ar)
        self.assertIn("الودجيت", checklist)
        self.assertIn("واتساب", checklist)
        self.assertIn("متجر", checklist)
        self.assertIn("استرجاع", checklist)

    def test_scenario_7_regression_disconnect_store(
        self, _mock_real: object, mock_ms: object, _mock_phone: object
    ) -> None:
        mock_ms.return_value = dict(_MILESTONES_SANDBOX_VERIFIED)
        complete = _store(
            access_token="tok-live",
            store_whatsapp_number="+966500000001",
            reason_templates_json='{"price":{"ar":"test"}}',
            cartflow_widget_enabled=True,
        )
        j_before = build_activation_journey_v2(complete, merchant_user_id=99)
        self.assertTrue(j_before.onboarding_complete)
        regressed = _store(
            access_token="",
            store_whatsapp_number="+966500000001",
            reason_templates_json='{"price":{"ar":"test"}}',
            cartflow_widget_enabled=True,
        )
        j_after = build_activation_journey_v2(regressed, merchant_user_id=99)
        self.assertFalse(_step(j_after, "connect_store").is_complete)
        self.assertLess(j_after.completed_steps, j_before.completed_steps)
        self.assertFalse(j_after.onboarding_complete)
        self.assertIsNone(j_after.readiness_card)
        self.assertFalse(_step(j_after, "ready_for_launch").is_complete)

    def test_scenario_8_regression_disable_whatsapp(
        self, _mock_real: object, mock_ms: object, _mock_phone: object
    ) -> None:
        mock_ms.return_value = dict(_MILESTONES_SANDBOX_VERIFIED)
        complete = _store(
            access_token="tok-live",
            store_whatsapp_number="+966500000001",
            reason_templates_json='{"price":{"ar":"test"}}',
            cartflow_widget_enabled=True,
        )
        j_before = build_activation_journey_v2(complete, merchant_user_id=99)
        regressed = _store(
            access_token="tok-live",
            store_whatsapp_number="",
            whatsapp_recovery_enabled=False,
            reason_templates_json='{"price":{"ar":"test"}}',
            cartflow_widget_enabled=True,
        )
        j_after = build_activation_journey_v2(regressed, merchant_user_id=99)
        self.assertFalse(_step(j_after, "configure_whatsapp").is_complete)
        self.assertTrue(_step(j_after, "review_messages").is_complete)
        self.assertLess(j_after.completed_steps, j_before.completed_steps)
        self.assertFalse(j_after.onboarding_complete)
        self.assertIsNone(j_after.readiness_card)

    def test_scenario_9_direct_url_nav_locks(
        self, _mock_real: object, mock_ms: object, _mock_phone: object
    ) -> None:
        mock_ms.return_value = dict(_MILESTONES_EMPTY)
        store = _store()
        j = build_activation_journey_v2(store, merchant_user_id=99)
        for page in ("whatsapp", "widget", "trigger-templates", "settings"):
            lock = j.nav_locks[page]
            self.assertFalse(lock.unlocked, page)
            self.assertTrue(lock.reason_ar)
            self.assertTrue(lock.required_step_title_ar)
            self.assertTrue(lock.cta_href)

    def test_scenario_10_mobile_css_present(
        self, _mock_real: object, mock_ms: object, _mock_phone: object
    ) -> None:
        mock_ms.return_value = dict(_MILESTONES_EMPTY)
        from pathlib import Path

        css = Path("static/merchant_app.css").read_text(encoding="utf-8")
        self.assertIn(".ma-journey-v2-panel", css)
        self.assertIn(".ma-journey-gate-card", css)
        self.assertIn(".ma-journey-gated", css)
        self.assertIn("@media (max-width: 639px)", css)
        idx = css.find(".ma-journey-v2-panel")
        mobile_idx = css.find("@media (max-width: 639px)", idx)
        self.assertGreater(mobile_idx, idx)
        self.assertIn(".ma-journey-v2-action", css[mobile_idx : mobile_idx + 1200])
        for cls in (
            ".ma-journey-v2-progress-bar",
            ".ma-journey-v2-checklist",
            ".ma-journey-v2-action",
        ):
            self.assertIn(cls, css)

    def test_account_not_complete_for_wrong_merchant(
        self, _mock_real: object, mock_ms: object, _mock_phone: object
    ) -> None:
        mock_ms.return_value = dict(_MILESTONES_EMPTY)
        store = _store(merchant_user_id=99)
        j = build_activation_journey_v2(store, merchant_user_id=100)
        self.assertFalse(_step(j, "account").is_complete)
        self.assertEqual(j.completed_steps, 0)


if __name__ == "__main__":
    unittest.main()
