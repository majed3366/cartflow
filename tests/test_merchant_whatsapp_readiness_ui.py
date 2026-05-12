# -*- coding: utf-8 -*-
"""Tests for merchant WhatsApp readiness card (interpretation layer only)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services.merchant_whatsapp_readiness_ui import build_merchant_whatsapp_readiness_card

_ST = object()


def _flags(**kwargs: bool) -> dict[str, bool]:
    base = {
        "dashboard_ready": True,
        "store_connected": True,
        "whatsapp_configured": True,
        "provider_ready": True,
        "recovery_enabled": True,
        "widget_installed": True,
        "test_recovery_possible": True,
        "sandbox_mode_active": False,
    }
    base.update(kwargs)
    return base


def _ob(flags: dict[str, bool], blocking: list[str]) -> dict:
    return {"flags": flags, "blocking_steps": blocking}


class MerchantWhatsAppReadinessDashboardHtmlTests(unittest.TestCase):
    def test_normal_carts_redirects_to_merchant_app_not_placeholder(self) -> None:
        r = TestClient(app).get("/dashboard/normal-carts", follow_redirects=False)
        self.assertEqual(r.status_code, 302, r.text[:500])
        loc = r.headers.get("location") or ""
        self.assertIn("#carts", loc)
        self.assertNotIn("data-cf-merchant-dashboard-placeholder", loc.lower())

    def test_dashboard_home_is_standalone_merchant_app(self) -> None:
        r = TestClient(app).get("/dashboard")
        self.assertEqual(r.status_code, 200, r.text[:500])
        t = r.text or ""
        tl = t.lower()
        self.assertIn("data-cf-merchant-app", tl)
        self.assertIn("CartFlow", t)
        self.assertNotIn("data-cf-merchant-dashboard-placeholder", tl)
        self.assertNotIn("data-cf-merchant-dashboard-v1", tl)
        self.assertIn("kpi-grid", t)
        self.assertIn("bottom-grid", t)
        self.assertIn("table-scroll", t)


class MerchantWhatsAppReadinessUiTests(unittest.TestCase):
    @patch(
        "services.merchant_whatsapp_readiness_ui.evaluate_onboarding_readiness",
        return_value=_ob(_flags(recovery_enabled=False), ["recovery_disabled"]),
    )
    def test_disabled_when_recovery_off(self, _m: object) -> None:
        c = build_merchant_whatsapp_readiness_card(_ST)
        self.assertEqual(c["state_key"], "disabled")
        self.assertIn("غير مفعل", c["badge_ar"])
        self.assertEqual(c["action_href"], "/dashboard#whatsapp")

    @patch(
        "services.merchant_whatsapp_readiness_ui.evaluate_onboarding_readiness",
        return_value=_ob(_flags(sandbox_mode_active=True), []),
    )
    def test_sandbox_when_flagged(self, _m: object) -> None:
        c = build_merchant_whatsapp_readiness_card(_ST)
        self.assertEqual(c["state_key"], "sandbox")
        self.assertIn("تجريبي", c["badge_ar"])

    @patch(
        "services.merchant_whatsapp_readiness_ui.evaluate_onboarding_readiness",
        return_value=_ob(_flags(whatsapp_configured=False), ["whatsapp_not_connected"]),
    )
    def test_setup_when_wa_not_configured(self, _m: object) -> None:
        c = build_merchant_whatsapp_readiness_card(_ST)
        self.assertEqual(c["state_key"], "setup")

    @patch(
        "services.merchant_whatsapp_readiness_ui.evaluate_onboarding_readiness",
        return_value=_ob(_flags(provider_ready=False), ["provider_not_ready"]),
    )
    def test_review_when_provider_not_ready(self, _m: object) -> None:
        c = build_merchant_whatsapp_readiness_card(_ST)
        self.assertEqual(c["state_key"], "review")
        self.assertIn("مراجعة", c["badge_ar"])
        self.assertNotIn("Twilio", c["title_ar"] + c["description_ar"])

    @patch(
        "services.merchant_whatsapp_readiness_ui.evaluate_onboarding_readiness",
        return_value=_ob(_flags(), []),
    )
    def test_ready_when_all_green(self, _m: object) -> None:
        c = build_merchant_whatsapp_readiness_card(_ST)
        self.assertEqual(c["state_key"], "ready")
        self.assertIn("جاهز", c["badge_ar"])

    def test_no_store_is_setup_not_disabled(self) -> None:
        with patch(
            "services.merchant_whatsapp_readiness_ui.evaluate_onboarding_readiness",
            return_value=_ob(
                _flags(
                    dashboard_ready=False,
                    recovery_enabled=False,
                    store_connected=False,
                ),
                ["dashboard_not_initialized"],
            ),
        ):
            c = build_merchant_whatsapp_readiness_card(None)
        self.assertEqual(c["state_key"], "setup")

    @patch(
        "services.merchant_whatsapp_readiness_ui.evaluate_onboarding_readiness",
        return_value=_ob(
            _flags(sandbox_mode_active=True, store_connected=False),
            ["store_not_connected"],
        ),
    )
    def test_sandbox_but_store_broken_is_setup(self, _m: object) -> None:
        c = build_merchant_whatsapp_readiness_card(_ST)
        self.assertEqual(c["state_key"], "setup")


if __name__ == "__main__":
    unittest.main()
