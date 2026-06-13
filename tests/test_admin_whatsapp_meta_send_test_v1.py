# -*- coding: utf-8 -*-
"""Admin Meta WhatsApp hello_world test send."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from services.admin_whatsapp_meta_send_test_v1 import send_meta_whatsapp_test_message


class AdminWhatsappMetaSendTestServiceTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_token(self) -> None:
        out = send_meta_whatsapp_test_message("+966501234567")
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "access_token_missing")
        self.assertIsNone(out["message_id"])

    @patch.dict(
        "os.environ",
        {"WHATSAPP_ACCESS_TOKEN": "tok"},
        clear=True,
    )
    def test_missing_phone_number_id(self) -> None:
        out = send_meta_whatsapp_test_message("+966501234567")
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "phone_number_id_missing")

    @patch.dict(
        "os.environ",
        {
            "WHATSAPP_ACCESS_TOKEN": "tok",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
        },
        clear=True,
    )
    def test_invalid_to(self) -> None:
        out = send_meta_whatsapp_test_message("bad")
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "invalid_to")

    @patch.dict(
        "os.environ",
        {
            "WHATSAPP_ACCESS_TOKEN": "tok",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
        },
        clear=True,
    )
    @patch("services.admin_whatsapp_meta_send_test_v1.requests.post")
    def test_meta_success_returns_message_id(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "messaging_product": "whatsapp",
            "messages": [{"id": "wamid.TEST123"}],
        }
        mock_post.return_value = mock_resp

        out = send_meta_whatsapp_test_message("+966501234567")
        self.assertTrue(out["ok"])
        self.assertEqual(out["message_id"], "wamid.TEST123")
        self.assertIsNone(out["error"])
        self.assertEqual(out["provider"], "meta")
        call_kwargs = mock_post.call_args
        self.assertIn("graph.facebook.com/v23.0/pn123/messages", call_kwargs[0][0])
        payload = call_kwargs[1]["json"]
        self.assertEqual(payload["to"], "966501234567")
        self.assertEqual(payload["template"]["name"], "hello_world")
        self.assertNotIn("access_token", out)

    @patch.dict(
        "os.environ",
        {
            "WHATSAPP_ACCESS_TOKEN": "tok",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
        },
        clear=True,
    )
    @patch("services.admin_whatsapp_meta_send_test_v1.requests.post")
    def test_meta_failure_safe_error(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "error": {
                "message": "Recipient phone number not in allowed list",
                "type": "OAuthException",
            }
        }
        mock_post.return_value = mock_resp

        out = send_meta_whatsapp_test_message("+966501234567")
        self.assertFalse(out["ok"])
        self.assertEqual(
            out["error"], "Recipient phone number not in allowed list"
        )
        self.assertIsNone(out["message_id"])


class AdminWhatsappMetaSendTestRouteTests(unittest.TestCase):
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

    def test_requires_admin_auth(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "meta-send-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.post(
            "/admin/api/whatsapp/meta-send-test",
            json={"to": "+966501234567"},
        )
        self.assertEqual(r.status_code, 401)

    @patch("services.admin_whatsapp_meta_send_test_v1.send_meta_whatsapp_test_message")
    def test_ok_with_admin_session(self, mock_send) -> None:
        mock_send.return_value = {
            "ok": True,
            "provider": "meta",
            "message_id": "wamid.TEST123",
            "error": None,
        }
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "meta-send-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={
                "password": "meta-send-auth-test",
                "next": "/admin/whatsapp",
            },
        )
        r = client.post(
            "/admin/api/whatsapp/meta-send-test",
            json={"to": "+966501234567"},
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("message_id"), "wamid.TEST123")
        self.assertNotIn("access_token", body)


if __name__ == "__main__":
    unittest.main()
