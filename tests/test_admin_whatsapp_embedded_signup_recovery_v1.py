# -*- coding: utf-8 -*-
"""Tests for admin Embedded Signup recovery (Phase 2B)."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from services.admin_whatsapp_embedded_signup_recovery_v1 import (
    TARGET_PHONE_NUMBER_ID,
    TARGET_WABA_ID,
    assert_existing_assets,
    complete_embedded_signup_recovery,
    public_recovery_config,
)


class AssertAssetsTests(unittest.TestCase):
    def test_assert_ok(self) -> None:
        r = assert_existing_assets(
            waba_id=TARGET_WABA_ID, phone_number_id=TARGET_PHONE_NUMBER_ID
        )
        self.assertTrue(r["ok"])
        self.assertFalse(r["aborted"])

    def test_assert_waba_mismatch_aborts(self) -> None:
        r = assert_existing_assets(
            waba_id="999", phone_number_id=TARGET_PHONE_NUMBER_ID
        )
        self.assertTrue(r["aborted"])
        self.assertFalse(r["waba_match"])

    def test_assert_phone_mismatch_aborts(self) -> None:
        r = assert_existing_assets(
            waba_id=TARGET_WABA_ID, phone_number_id="999"
        )
        self.assertTrue(r["aborted"])
        self.assertFalse(r["phone_match"])


class PublicConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._keys = [
            "META_WHATSAPP_APP_ID",
            "META_WHATSAPP_CONFIGURATION_ID",
            "META_WHATSAPP_APP_SECRET",
        ]
        self._prev = {k: os.environ.get(k) for k in self._keys}

    def tearDown(self) -> None:
        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_public_config_never_includes_secret(self) -> None:
        os.environ["META_WHATSAPP_APP_ID"] = "1485048632921274"
        os.environ["META_WHATSAPP_CONFIGURATION_ID"] = "27774549568822736"
        os.environ["META_WHATSAPP_APP_SECRET"] = "unit-test-secret-value-not-real"
        cfg = public_recovery_config()
        self.assertTrue(cfg["ready"])
        self.assertTrue(cfg["app_secret_configured"])
        self.assertEqual(cfg["app_id"], "1485048632921274")
        self.assertNotIn("app_secret", cfg)
        self.assertNotIn("access_token", cfg)
        blob = str(cfg)
        self.assertNotIn("unit-test-secret-value-not-real", blob)


class CompleteRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._keys = [
            "META_WHATSAPP_APP_ID",
            "META_WHATSAPP_CONFIGURATION_ID",
            "META_WHATSAPP_APP_SECRET",
        ]
        self._prev = {k: os.environ.get(k) for k in self._keys}
        os.environ["META_WHATSAPP_APP_ID"] = "1485048632921274"
        os.environ["META_WHATSAPP_CONFIGURATION_ID"] = "27774549568822736"
        os.environ["META_WHATSAPP_APP_SECRET"] = "unit-test-secret-value-not-real"

    def tearDown(self) -> None:
        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_mismatch_aborts_before_exchange(self) -> None:
        with patch(
            "services.admin_whatsapp_embedded_signup_recovery_v1.requests.get"
        ) as mock_get:
            r = complete_embedded_signup_recovery(
                code="fake-code",
                waba_id="111",
                phone_number_id=TARGET_PHONE_NUMBER_ID,
            )
            mock_get.assert_not_called()
        self.assertTrue(r["aborted"])
        self.assertFalse(r["ok"])
        self.assertFalse(r["register_called"])
        self.assertNotIn("access_token", r)

    @patch("services.admin_whatsapp_embedded_signup_recovery_v1.requests.get")
    def test_success_path_no_token_leak_no_register(self, mock_get) -> None:
        exchange = MagicMock()
        exchange.status_code = 200
        exchange.content = b'{"access_token":"SECRET_TOKEN_VALUE","token_type":"bearer"}'
        exchange.json.return_value = {
            "access_token": "SECRET_TOKEN_VALUE",
            "token_type": "bearer",
        }

        confirm = MagicMock()
        confirm.status_code = 200
        confirm.content = b'{"id":"1260388737156321","display_phone_number":"+966579706669"}'
        confirm.json.return_value = {
            "id": TARGET_PHONE_NUMBER_ID,
            "display_phone_number": "+966 57 970 6669",
            "verified_name": "CartFlow",
        }
        mock_get.side_effect = [exchange, confirm]

        r = complete_embedded_signup_recovery(
            code="exchangeable-code",
            waba_id=TARGET_WABA_ID,
            phone_number_id=TARGET_PHONE_NUMBER_ID,
            session_event="FINISH",
        )
        self.assertTrue(r["ok"])
        self.assertEqual(r.get("resolution_source"), "browser_session")
        self.assertTrue(r["fresh_authorization_obtained"])
        self.assertFalse(r["register_called"])
        self.assertFalse(r["assets_created"])
        self.assertFalse(r["assets_deleted"])
        self.assertNotIn("access_token", r)
        self.assertNotIn("SECRET_TOKEN_VALUE", str(r))
        self.assertIn("STOP", r.get("next_phase") or "")

    @patch("services.admin_whatsapp_embedded_signup_recovery_v1.requests.get")
    def test_shared_waba_fallback_success(self, mock_get) -> None:
        exchange = MagicMock()
        exchange.status_code = 200
        exchange.content = b'{"access_token":"SECRET_TOKEN_VALUE"}'
        exchange.json.return_value = {"access_token": "SECRET_TOKEN_VALUE"}

        debug = MagicMock()
        debug.status_code = 200
        debug.content = b"{}"
        debug.json.return_value = {
            "data": {
                "is_valid": True,
                "type": "USER",
                "app_id": "1485048632921274",
                "scopes": [
                    "whatsapp_business_management",
                    "whatsapp_business_messaging",
                ],
                "granular_scopes": [
                    {
                        "scope": "whatsapp_business_management",
                        "target_ids": [TARGET_WABA_ID, "999"],
                    }
                ],
            }
        }

        phones = MagicMock()
        phones.status_code = 200
        phones.content = b"{}"
        phones.json.return_value = {
            "data": [
                {
                    "id": TARGET_PHONE_NUMBER_ID,
                    "display_phone_number": "+966 57 970 6669",
                    "verified_name": "CartFlow",
                }
            ]
        }
        mock_get.side_effect = [exchange, debug, phones]

        r = complete_embedded_signup_recovery(
            code="exchangeable-code",
            waba_id="",
            phone_number_id="",
            allow_shared_waba_fallback=True,
        )
        self.assertTrue(r["ok"])
        self.assertEqual(r.get("resolution_source"), "server_shared_waba_fallback")
        self.assertEqual(r.get("waba_id"), TARGET_WABA_ID)
        self.assertEqual(r.get("phone_number_id"), TARGET_PHONE_NUMBER_ID)
        self.assertFalse(r.get("register_called"))
        self.assertNotIn("SECRET_TOKEN_VALUE", str(r))
        self.assertNotIn("access_token", r)

    @patch("services.admin_whatsapp_embedded_signup_recovery_v1.requests.get")
    def test_shared_waba_fallback_target_waba_not_shared(self, mock_get) -> None:
        exchange = MagicMock()
        exchange.status_code = 200
        exchange.content = b'{"access_token":"SECRET_TOKEN_VALUE"}'
        exchange.json.return_value = {"access_token": "SECRET_TOKEN_VALUE"}

        debug = MagicMock()
        debug.status_code = 200
        debug.content = b"{}"
        debug.json.return_value = {
            "data": {
                "is_valid": True,
                "scopes": ["whatsapp_business_management"],
                "granular_scopes": [
                    {"scope": "whatsapp_business_management", "target_ids": ["111"]}
                ],
            }
        }
        mock_get.side_effect = [exchange, debug]

        r = complete_embedded_signup_recovery(
            code="exchangeable-code",
            allow_shared_waba_fallback=True,
        )
        self.assertFalse(r["ok"])
        self.assertEqual(r.get("error"), "target_waba_not_shared")
        self.assertFalse(r.get("register_called"))

    @patch("services.admin_whatsapp_embedded_signup_recovery_v1.requests.get")
    def test_shared_waba_fallback_target_phone_not_confirmed(self, mock_get) -> None:
        exchange = MagicMock()
        exchange.status_code = 200
        exchange.content = b'{"access_token":"SECRET_TOKEN_VALUE"}'
        exchange.json.return_value = {"access_token": "SECRET_TOKEN_VALUE"}

        debug = MagicMock()
        debug.status_code = 200
        debug.content = b"{}"
        debug.json.return_value = {
            "data": {
                "is_valid": True,
                "scopes": ["whatsapp_business_management"],
                "granular_scopes": [
                    {
                        "scope": "whatsapp_business_management",
                        "target_ids": [TARGET_WABA_ID],
                    }
                ],
            }
        }
        phones = MagicMock()
        phones.status_code = 200
        phones.content = b"{}"
        phones.json.return_value = {
            "data": [{"id": "000", "display_phone_number": "+10000000000"}]
        }
        mock_get.side_effect = [exchange, debug, phones]

        r = complete_embedded_signup_recovery(
            code="exchangeable-code",
            allow_shared_waba_fallback=True,
        )
        self.assertFalse(r["ok"])
        self.assertEqual(r.get("error"), "target_phone_not_confirmed")
        self.assertEqual(r.get("waba_id"), TARGET_WABA_ID)
        self.assertFalse(r.get("register_called"))

    def test_missing_ids_without_fallback_flag_aborts(self) -> None:
        with patch(
            "services.admin_whatsapp_embedded_signup_recovery_v1.requests.get"
        ) as mock_get:
            r = complete_embedded_signup_recovery(
                code="exchangeable-code",
                waba_id="",
                phone_number_id="",
                allow_shared_waba_fallback=False,
            )
            mock_get.assert_not_called()
        self.assertEqual(r.get("error"), "missing_session_asset_ids")
        self.assertFalse(r.get("ok"))


class RouteAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        self._prev_app = os.environ.get("META_WHATSAPP_APP_ID")
        self._prev_cfg = os.environ.get("META_WHATSAPP_CONFIGURATION_ID")
        self._prev_sec = os.environ.get("META_WHATSAPP_APP_SECRET")

    def tearDown(self) -> None:
        for key, prev in (
            ("CARTFLOW_ADMIN_PASSWORD", self._prev_admin),
            ("SECRET_KEY", self._prev_secret),
            ("META_WHATSAPP_APP_ID", self._prev_app),
            ("META_WHATSAPP_CONFIGURATION_ID", self._prev_cfg),
            ("META_WHATSAPP_APP_SECRET", self._prev_sec),
        ):
            if prev is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prev

    def test_config_requires_admin(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "es-recovery-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.get("/admin/api/whatsapp/embedded-signup-recovery/config")
        self.assertEqual(r.status_code, 401)

    def test_config_ok_with_admin_session(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "es-recovery-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        os.environ["META_WHATSAPP_APP_ID"] = "1485048632921274"
        os.environ["META_WHATSAPP_CONFIGURATION_ID"] = "27774549568822736"
        os.environ["META_WHATSAPP_APP_SECRET"] = "unit-test-secret-value-not-real"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={
                "password": "es-recovery-auth-test",
                "next": "/admin/whatsapp/embedded-signup-recovery",
            },
        )
        r = client.get("/admin/api/whatsapp/embedded-signup-recovery/config")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("ready"))
        self.assertEqual(body.get("app_id"), "1485048632921274")
        self.assertEqual(body.get("configuration_id"), "27774549568822736")
        self.assertNotIn("app_secret", body)
        self.assertTrue(body.get("stop_before_register"))

    def test_page_requires_admin(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "es-recovery-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.get(
            "/admin/whatsapp/embedded-signup-recovery", follow_redirects=False
        )
        self.assertIn(r.status_code, (302, 303, 401))


if __name__ == "__main__":
    unittest.main()
