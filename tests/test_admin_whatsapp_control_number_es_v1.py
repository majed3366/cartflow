# -*- coding: utf-8 -*-
"""Tests for admin Control Number Embedded Signup (Phase C2)."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from services.admin_whatsapp_control_number_es_v1 import (
    CONTROL_PHONE_E164,
    CONTROL_WABA_ID,
    PRODUCTION_PHONE_NUMBER_ID,
    RECOVERY_MARKER,
    assert_control_assets,
    complete_control_number_es,
    normalize_e164,
    public_control_config,
)


class NormalizeE164Tests(unittest.TestCase):
    def test_control_variants(self) -> None:
        self.assertEqual(normalize_e164("+966 53 313 2601"), CONTROL_PHONE_E164)
        self.assertEqual(normalize_e164("966533132601"), CONTROL_PHONE_E164)
        self.assertEqual(normalize_e164("+966533132601"), CONTROL_PHONE_E164)


class AssertControlAssetsTests(unittest.TestCase):
    def test_ok_new_phone(self) -> None:
        r = assert_control_assets(
            waba_id=CONTROL_WABA_ID,
            phone_number_id="999888777666555",
            display_phone_number="+966 53 313 2601",
        )
        self.assertTrue(r["ok"])
        self.assertFalse(r["aborted"])

    def test_production_phone_aborts(self) -> None:
        r = assert_control_assets(
            waba_id=CONTROL_WABA_ID,
            phone_number_id=PRODUCTION_PHONE_NUMBER_ID,
            display_phone_number="+966579706669",
        )
        self.assertTrue(r["aborted"])
        self.assertIn("production_phone_id_appeared", r["reason"] or "")

    def test_new_waba_aborts(self) -> None:
        r = assert_control_assets(
            waba_id="111222333",
            phone_number_id="999888777666555",
            display_phone_number=CONTROL_PHONE_E164,
        )
        self.assertTrue(r["aborted"])
        self.assertFalse(r["waba_match"])

    def test_wrong_e164_aborts(self) -> None:
        r = assert_control_assets(
            waba_id=CONTROL_WABA_ID,
            phone_number_id="999888777666555",
            display_phone_number="+966500000000",
        )
        self.assertTrue(r["aborted"])


class PublicConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._keys = [
            "META_WHATSAPP_APP_ID",
            "META_WHATSAPP_CONFIGURATION_ID",
            "META_WHATSAPP_CONTROL_CONFIGURATION_ID",
            "META_WHATSAPP_APP_SECRET",
        ]
        self._prev = {k: os.environ.get(k) for k in self._keys}

    def tearDown(self) -> None:
        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_public_config_uses_control_configuration_id_only(self) -> None:
        os.environ["META_WHATSAPP_APP_ID"] = "1485048632921274"
        os.environ["META_WHATSAPP_CONFIGURATION_ID"] = "27774549568822736"
        os.environ["META_WHATSAPP_CONTROL_CONFIGURATION_ID"] = "999888777666555"
        os.environ["META_WHATSAPP_APP_SECRET"] = "unit-test-secret-value-not-real"
        cfg = public_control_config()
        self.assertTrue(cfg["ready"])
        self.assertEqual(cfg["configuration_id"], "999888777666555")
        self.assertEqual(
            cfg["configuration_id_source"], "META_WHATSAPP_CONTROL_CONFIGURATION_ID"
        )
        self.assertFalse(cfg["uses_recovery_configuration_id"])
        self.assertNotEqual(cfg["configuration_id"], "27774549568822736")
        self.assertNotIn("app_secret", cfg)
        self.assertNotIn("unit-test-secret-value-not-real", str(cfg))

    def test_ready_false_without_control_configuration_id(self) -> None:
        os.environ["META_WHATSAPP_APP_ID"] = "1485048632921274"
        os.environ["META_WHATSAPP_CONFIGURATION_ID"] = "27774549568822736"
        os.environ.pop("META_WHATSAPP_CONTROL_CONFIGURATION_ID", None)
        os.environ["META_WHATSAPP_APP_SECRET"] = "unit-test-secret-value-not-real"
        cfg = public_control_config()
        self.assertFalse(cfg["ready"])
        self.assertIsNone(cfg["configuration_id"])


class CompleteControlEsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._keys = [
            "META_WHATSAPP_APP_ID",
            "META_WHATSAPP_CONFIGURATION_ID",
            "META_WHATSAPP_CONTROL_CONFIGURATION_ID",
            "META_WHATSAPP_APP_SECRET",
        ]
        self._prev = {k: os.environ.get(k) for k in self._keys}
        os.environ["META_WHATSAPP_APP_ID"] = "1485048632921274"
        os.environ["META_WHATSAPP_CONFIGURATION_ID"] = "27774549568822736"
        os.environ["META_WHATSAPP_CONTROL_CONFIGURATION_ID"] = "999888777666555"
        os.environ["META_WHATSAPP_APP_SECRET"] = "unit-test-secret-value-not-real"

    def tearDown(self) -> None:
        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_production_phone_aborts_before_exchange(self) -> None:
        with patch(
            "services.admin_whatsapp_control_number_es_v1.requests.get"
        ) as mock_get:
            with patch(
                "services.admin_whatsapp_control_number_es_v1._exchange_code_internal"
            ) as mock_ex:
                r = complete_control_number_es(
                    code="fake-code",
                    waba_id=CONTROL_WABA_ID,
                    phone_number_id=PRODUCTION_PHONE_NUMBER_ID,
                )
                mock_ex.assert_not_called()
                mock_get.assert_not_called()
        self.assertTrue(r["aborted"])
        self.assertEqual(r["error"], "production_phone_id_appeared")
        self.assertFalse(r["register_called"])
        self.assertNotIn("access_token", r)

    def test_waba_mismatch_aborts_before_exchange(self) -> None:
        with patch(
            "services.admin_whatsapp_control_number_es_v1._exchange_code_internal"
        ) as mock_ex:
            r = complete_control_number_es(
                code="fake-code",
                waba_id="999",
                phone_number_id="888777666555444",
                display_phone_number=CONTROL_PHONE_E164,
            )
            mock_ex.assert_not_called()
        self.assertTrue(r["aborted"])
        self.assertEqual(r["error"], "asset_assertion_failed")

    @patch("services.admin_whatsapp_control_number_es_v1.requests.get")
    @patch("services.admin_whatsapp_control_number_es_v1._exchange_code_internal")
    def test_success_sanitized_no_register(self, mock_ex, mock_get) -> None:
        new_id = "555444333222111"
        mock_ex.return_value = (
            "SECRET_TOKEN_VALUE",
            {
                "ok": True,
                "token_obtained": True,
                "oauth_exchange": {"redirect_uri_mode": "dialog"},
                "graph_endpoint": "/v23.0/oauth/access_token",
            },
        )
        confirm = MagicMock()
        confirm.status_code = 200
        confirm.content = b'{"id":"555444333222111","display_phone_number":"+966 53 313 2601"}'
        confirm.json.return_value = {
            "id": new_id,
            "display_phone_number": "+966 53 313 2601",
            "verified_name": "CartFlow Control",
        }
        mock_get.return_value = confirm

        r = complete_control_number_es(
            code="fake-code",
            waba_id=CONTROL_WABA_ID,
            phone_number_id=new_id,
        )
        self.assertTrue(r["ok"])
        self.assertEqual(r["new_phone_number_id"], new_id)
        self.assertEqual(r["waba_id"], CONTROL_WABA_ID)
        self.assertEqual(r["control_phone"], CONTROL_PHONE_E164)
        self.assertTrue(r["production_phone_untouched"])
        self.assertFalse(r["register_called"])
        self.assertFalse(r["env_mutated"])
        self.assertFalse(r["db_mutated"])
        self.assertNotIn("access_token", r)
        self.assertNotIn("SECRET_TOKEN_VALUE", str(r))

    @patch("services.admin_whatsapp_control_number_es_v1.requests.get")
    @patch("services.admin_whatsapp_control_number_es_v1._exchange_code_internal")
    def test_fallback_finds_control_phone(self, mock_ex, mock_get) -> None:
        new_id = "555444333222111"
        mock_ex.return_value = (
            "SECRET_TOKEN_VALUE",
            {"ok": True, "token_obtained": True},
        )
        listed = MagicMock()
        listed.status_code = 200
        listed.content = b"{}"
        listed.json.return_value = {
            "data": [
                {
                    "id": PRODUCTION_PHONE_NUMBER_ID,
                    "display_phone_number": "+966 57 970 6669",
                },
                {
                    "id": new_id,
                    "display_phone_number": "+966 53 313 2601",
                },
            ]
        }
        mock_get.return_value = listed

        r = complete_control_number_es(
            code="fake-code",
            allow_waba_phone_fallback=True,
        )
        self.assertTrue(r["ok"])
        self.assertEqual(r["new_phone_number_id"], new_id)
        self.assertEqual(r["resolution_source"], "server_waba_phone_lookup")
        self.assertFalse(r["register_called"])


class RouteIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._keys = ["CARTFLOW_ADMIN_PASSWORD", "SECRET_KEY"]
        self._prev = {k: os.environ.get(k) for k in self._keys}
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "control-es-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"

    def tearDown(self) -> None:
        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_page_requires_admin(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)
        r = client.get("/admin/whatsapp/control-number-es", follow_redirects=False)
        self.assertIn(r.status_code, (302, 303, 401, 403))

    def test_config_requires_admin(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)
        r = client.get("/admin/api/whatsapp/control-number-es/config")
        self.assertEqual(r.status_code, 401)

    def test_register_allowlist_unchanged(self) -> None:
        from services.admin_whatsapp_meta_register_v1 import ALLOWED_REGISTER_PHONE_IDS

        self.assertEqual(ALLOWED_REGISTER_PHONE_IDS, frozenset({PRODUCTION_PHONE_NUMBER_ID}))


if __name__ == "__main__":
    unittest.main()
