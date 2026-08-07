# -*- coding: utf-8 -*-
"""Admin Meta phone register — allowlisted, never echoes PIN."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from services.admin_whatsapp_meta_register_v1 import register_whatsapp_phone


class RegisterWhatsappPhoneTests(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {"WHATSAPP_ACCESS_TOKEN": "tok", "WHATSAPP_BUSINESS_ACCOUNT_ID": "waba"},
        clear=True,
    )
    @patch("services.admin_whatsapp_meta_register_v1.fetch_whatsapp_meta_status")
    @patch("services.admin_whatsapp_meta_register_v1.requests.post")
    def test_success_register(self, mock_post: MagicMock, mock_status: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}
        mock_post.return_value = mock_resp
        mock_status.return_value = {
            "phone_number_id": "1260388737156321",
            "display_phone_number": "+966 57 970 6669",
            "verified_name": "Cartflow",
            "registration_status": "CONNECTED",
            "platform_type": "CLOUD_API",
            "is_pin_enabled": True,
            "code_verification_status": "VERIFIED",
            "name_status": "AVAILABLE_WITHOUT_REVIEW",
            "cloud_api_registered": True,
            "diagnostic_extras": {"health_status": {"can_send_message": "AVAILABLE"}},
            "meta_response_ok": True,
            "error": None,
        }
        out = register_whatsapp_phone(phone_number_id="1260388737156321", pin="120456")
        self.assertTrue(out["ok"])
        self.assertEqual(out["registration_response"], {"success": True})
        self.assertEqual(out["after_status"]["registration_status"], "CONNECTED")
        self.assertNotIn("pin", out)
        body = mock_post.call_args[1]["json"]
        self.assertEqual(body["messaging_product"], "whatsapp")
        self.assertEqual(body["pin"], "120456")

    def test_rejects_non_allowlisted_phone(self) -> None:
        out = register_whatsapp_phone(phone_number_id="1182183628307692", pin="120456")
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_message_safe"], "phone_number_id_not_allowlisted")

    @patch.dict(
        "os.environ",
        {"WHATSAPP_ACCESS_TOKEN": "tok"},
        clear=True,
    )
    @patch("services.admin_whatsapp_meta_register_v1.requests.post")
    def test_meta_rejection_sanitized(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "error": {
                "message": "Invalid OAuth access token",
                "type": "OAuthException",
                "code": 190,
                "error_subcode": 123,
                "fbtrace_id": "abc",
            }
        }
        mock_post.return_value = mock_resp
        out = register_whatsapp_phone(phone_number_id="1260388737156321", pin="120456")
        self.assertFalse(out["ok"])
        self.assertEqual(out["http_status"], 400)
        self.assertEqual(out["error_code"], 190)
        self.assertEqual(out["error_message_safe"], "meta_auth_or_token_error")
        self.assertEqual(out["fbtrace_id"], "abc")
        self.assertNotIn("120456", str(out))


if __name__ == "__main__":
    unittest.main()
