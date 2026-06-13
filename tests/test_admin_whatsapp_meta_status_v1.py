# -*- coding: utf-8 -*-
"""Admin WhatsApp Meta Graph connection verification."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from services.admin_whatsapp_meta_status_v1 import (
    fetch_whatsapp_meta_status,
    read_whatsapp_meta_env,
)


class AdminWhatsappMetaStatusEnvTests(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {
            "WHATSAPP_ACCESS_TOKEN": "tok",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
            "WHATSAPP_BUSINESS_ACCOUNT_ID": "waba456",
        },
        clear=False,
    )
    def test_reads_primary_env_names(self) -> None:
        env = read_whatsapp_meta_env()
        self.assertEqual(env["access_token"], "tok")
        self.assertEqual(env["phone_number_id"], "pn123")
        self.assertEqual(env["waba_id"], "waba456")

    @patch.dict(
        "os.environ",
        {
            "WHATSAPP_API_TOKEN": "legacy-tok",
            "WHATSAPP_PHONE_ID": "legacy-pn",
            "WABA_ID": "legacy-waba",
        },
        clear=False,
    )
    def test_reads_legacy_env_fallbacks(self) -> None:
        env = read_whatsapp_meta_env()
        self.assertEqual(env["access_token"], "legacy-tok")
        self.assertEqual(env["phone_number_id"], "legacy-pn")
        self.assertEqual(env["waba_id"], "legacy-waba")


class AdminWhatsappMetaStatusFetchTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_token(self) -> None:
        out = fetch_whatsapp_meta_status()
        self.assertFalse(out["connected"])
        self.assertFalse(out["meta_response_ok"])
        self.assertEqual(out["error"], "access_token_missing")

    @patch.dict(
        "os.environ",
        {"WHATSAPP_ACCESS_TOKEN": "tok"},
        clear=True,
    )
    def test_missing_phone_id(self) -> None:
        out = fetch_whatsapp_meta_status()
        self.assertEqual(out["error"], "phone_number_id_missing")

    @patch.dict(
        "os.environ",
        {
            "WHATSAPP_ACCESS_TOKEN": "tok",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
            "WHATSAPP_BUSINESS_ACCOUNT_ID": "waba456",
        },
        clear=True,
    )
    @patch("services.admin_whatsapp_meta_status_v1.requests.get")
    def test_successful_meta_response(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "pn123",
            "verified_name": "CartFlow",
            "display_phone_number": "+966 50 000 0000",
        }
        mock_get.return_value = mock_resp

        out = fetch_whatsapp_meta_status()
        self.assertTrue(out["connected"])
        self.assertTrue(out["meta_response_ok"])
        self.assertIsNone(out["error"])
        self.assertEqual(out["verified_name"], "CartFlow")
        self.assertEqual(out["display_phone_number"], "+966 50 000 0000")
        self.assertEqual(out["phone_number_id"], "pn123")
        self.assertEqual(out["waba_id"], "waba456")
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        self.assertIn("graph.facebook.com/v23.0/pn123", call_kwargs[0][0])
        self.assertEqual(call_kwargs[1]["headers"]["Authorization"], "Bearer tok")
        self.assertNotIn("access_token", out)
        self.assertNotIn("token", out)

    @patch.dict(
        "os.environ",
        {
            "WHATSAPP_ACCESS_TOKEN": "tok",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
        },
        clear=True,
    )
    @patch("services.admin_whatsapp_meta_status_v1.requests.get")
    def test_meta_error_response(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {
            "error": {"message": "Invalid OAuth access token", "type": "OAuthException"}
        }
        mock_get.return_value = mock_resp

        out = fetch_whatsapp_meta_status()
        self.assertFalse(out["connected"])
        self.assertFalse(out["meta_response_ok"])
        self.assertEqual(out["error"], "Invalid OAuth access token")


class AdminWhatsappMetaStatusRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")

    def tearDown(self) -> None:
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def test_meta_status_requires_admin_session(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "meta-status-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.get("/admin/api/whatsapp/meta-status")
        self.assertEqual(r.status_code, 401)
        body = r.json()
        self.assertFalse(body.get("ok"))

    @patch("services.admin_whatsapp_meta_status_v1.fetch_whatsapp_meta_status")
    def test_meta_status_ok_with_admin_session(self, mock_fetch) -> None:
        from fastapi.testclient import TestClient

        from main import app

        mock_fetch.return_value = {
            "connected": True,
            "phone_number_id": "pn123",
            "verified_name": "CartFlow",
            "display_phone_number": "+966500000000",
            "waba_id": "waba456",
            "meta_response_ok": True,
            "error": None,
            "verified_at": "2026-06-13T00:00:00+00:00",
        }
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "meta-status-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={
                "password": "meta-status-auth-test",
                "next": "/admin/whatsapp",
            },
        )
        r = client.get("/admin/api/whatsapp/meta-status")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("connected"))
        self.assertNotIn("access_token", body)
        self.assertNotIn("token", body)


if __name__ == "__main__":
    unittest.main()
