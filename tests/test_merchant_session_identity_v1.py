# -*- coding: utf-8 -*-
"""Merchant Session Identity Panel V1 — unit + surface guards."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


class MerchantSessionIdentityGuards(unittest.TestCase):
    def test_static_panel_wired(self) -> None:
        html = (ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
        self.assertIn("merchant_session_identity_v1.js", html)
        self.assertIn("merchant_session_identity_v1.css", html)
        self.assertIn('id="ma-gtb-account-btn"', html)
        self.assertIn('aria-controls="ma-account-identity-panel"', html)

        js = (ROOT / "static" / "merchant_session_identity_v1.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("/api/merchant/session-identity", js)
        self.assertIn("ma-account-identity", js)
        self.assertNotIn("simulation_run_id", js)

        py = (ROOT / "services" / "merchant_session_identity_v1.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("أنت تعرض نفس التاجر والمتجر", py)
        self.assertIn("/dev/living-store-home-review", py)
        self.assertNotIn("simulation_run_id", py)

    def test_build_identity_living_store_review(self) -> None:
        from services.living_store_reality_prod_v1 import REVIEW_EMAIL
        from services.merchant_session_identity_v1 import (
            build_merchant_session_identity_v1,
        )

        user = MagicMock()
        user.id = 429
        user.email = REVIEW_EMAIL
        user.merchant_name = "Living Store Review"
        user.primary_store_id = 1

        store = MagicMock()
        store.id = 1
        store.zid_store_id = "demo"
        store.widget_display_name = "Living Store Demo"
        store.access_token = ""
        store.name = "demo"

        with patch(
            "services.merchant_session_identity_v1.parse_merchant_session_cookie_value",
            return_value=429,
        ), patch(
            "services.merchant_session_identity_v1._parse_cookie_exp",
            return_value=2_000_000_000,
        ), patch(
            "services.merchant_session_identity_v1.get_merchant_user_by_id",
            return_value=user,
        ), patch(
            "services.merchant_session_identity_v1.get_primary_store_for_merchant",
            return_value=store,
        ), patch(
            "services.merchant_session_identity_v1.is_development_env",
            return_value=False,
        ):
            payload = build_merchant_session_identity_v1(
                cookies={"cartflow_merchant_session": "429:2000000000:x"},
                dashboard_store_slug="demo",
            )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["merchant_email"], REVIEW_EMAIL)
        self.assertEqual(payload["store_slug"], "demo")
        self.assertEqual(payload["merchant_id"], 429)
        self.assertTrue(payload["is_living_store_review"])
        self.assertTrue(payload["consistency"]["ok"])
        self.assertIn("نفس التاجر والمتجر", payload["consistency"]["message_ar"])
        self.assertNotIn("simulation_run_id", payload)

    def test_build_identity_mismatch(self) -> None:
        from services.merchant_session_identity_v1 import (
            build_merchant_session_identity_v1,
        )

        user = MagicMock()
        user.id = 10
        user.email = "merchant@example.com"
        user.merchant_name = "Test"
        user.primary_store_id = 2

        store = MagicMock()
        store.id = 2
        store.zid_store_id = "my-store"
        store.widget_display_name = "My Store"
        store.access_token = "tok"
        store.name = "My Store"
        store.updated_at = None
        store.created_at = None

        with patch(
            "services.merchant_session_identity_v1.parse_merchant_session_cookie_value",
            return_value=10,
        ), patch(
            "services.merchant_session_identity_v1._parse_cookie_exp",
            return_value=2_000_000_000,
        ), patch(
            "services.merchant_session_identity_v1.get_merchant_user_by_id",
            return_value=user,
        ), patch(
            "services.merchant_session_identity_v1.get_primary_store_for_merchant",
            return_value=store,
        ), patch(
            "services.merchant_session_identity_v1.is_development_env",
            return_value=False,
        ), patch(
            "services.merchant_session_identity_v1.is_merchant_store_platform_connected",
            return_value=True,
        ):
            payload = build_merchant_session_identity_v1(
                cookies={"cartflow_merchant_session": "10:2000000000:x"},
                dashboard_store_slug="other-store",
            )

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["consistency"]["ok"])
        self.assertEqual(
            payload["consistency"]["action_href"],
            "/dev/living-store-home-review",
        )
        self.assertIn("اختلاف في الجلسة", payload["consistency"]["message_ar"])


if __name__ == "__main__":
    unittest.main()
