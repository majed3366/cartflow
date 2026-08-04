# -*- coding: utf-8 -*-
"""Meta Recovery Template Parameter Mapping V1 — store display name → {{1}}."""
from __future__ import annotations

import inspect
import os
import unittest
from unittest.mock import MagicMock, patch

from services.whatsapp_provider import (
    META_RECOVERY_TEMPLATE_CARTFLOW_V1,
    MODE_SESSION_TEXT,
    MODE_TEMPLATE,
    PROVIDER_META,
    PROVIDER_TWILIO,
    normalize_store_display_name,
    resolve_meta_template_parameters,
    resolve_store_display_name_from_context,
    send_whatsapp_message,
)
from services.whatsapp_providers.meta_cloud import build_meta_template_payload


class NormalizeStoreDisplayNameTests(unittest.TestCase):
    def test_arabic_preserved(self) -> None:
        self.assertEqual(normalize_store_display_name("  متجر الأمان  "), "متجر الأمان")

    def test_whitespace_trimmed(self) -> None:
        self.assertEqual(normalize_store_display_name("  Shop  "), "Shop")

    def test_empty_rejected(self) -> None:
        self.assertIsNone(normalize_store_display_name(""))
        self.assertIsNone(normalize_store_display_name("   "))
        self.assertIsNone(normalize_store_display_name(None))

    def test_newline_rejected(self) -> None:
        self.assertIsNone(normalize_store_display_name("متجر\nخطين"))

    def test_url_like_rejected(self) -> None:
        self.assertIsNone(normalize_store_display_name("https://example.com/cart"))
        self.assertIsNone(normalize_store_display_name("www.store.com"))

    def test_overlong_rejected(self) -> None:
        self.assertIsNone(normalize_store_display_name("س" * 61))


class ResolveParametersTests(unittest.TestCase):
    def test_explicit_template_parameters_take_precedence(self) -> None:
        params, err = resolve_meta_template_parameters(
            {
                "template_parameters": ["اسم صريح"],
                "store_display_name": "يجب ألا يُستخدم",
                "store_slug": "slug-ignored",
            },
            template_name=META_RECOVERY_TEMPLATE_CARTFLOW_V1,
        )
        self.assertIsNone(err)
        self.assertEqual(params, ["اسم صريح"])

    def test_store_display_name_maps_to_param(self) -> None:
        params, err = resolve_meta_template_parameters(
            {"store_display_name": "متجر التجربة"},
            template_name=META_RECOVERY_TEMPLATE_CARTFLOW_V1,
        )
        self.assertIsNone(err)
        self.assertEqual(params, ["متجر التجربة"])

    def test_slug_fallback(self) -> None:
        with patch(
            "services.whatsapp_provider.resolve_store_display_name_from_context",
            wraps=resolve_store_display_name_from_context,
        ):
            with patch(
                "services.whatsapp_production_reality_v2.resolve_store_for_template_enforcement",
                return_value=None,
            ):
                params, err = resolve_meta_template_parameters(
                    {"store_slug": "my_cool_store"},
                    template_name=META_RECOVERY_TEMPLATE_CARTFLOW_V1,
                )
        self.assertIsNone(err)
        self.assertEqual(params, ["my cool store"])

    def test_missing_store_display_name(self) -> None:
        with patch(
            "services.whatsapp_production_reality_v2.resolve_store_for_template_enforcement",
            return_value=None,
        ):
            params, err = resolve_meta_template_parameters(
                {"store_slug": "demo"},
                template_name=META_RECOVERY_TEMPLATE_CARTFLOW_V1,
            )
        self.assertIsNone(params)
        self.assertEqual(err, "meta_store_display_name_missing")

    def test_v1_template_rejects_wrong_explicit_count(self) -> None:
        params, err = resolve_meta_template_parameters(
            {"template_parameters": ["a", "b"]},
            template_name=META_RECOVERY_TEMPLATE_CARTFLOW_V1,
        )
        self.assertIsNone(params)
        self.assertEqual(err, "meta_template_parameter_count_invalid")


class MetaTemplatePayloadMappingTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-VALUE",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
            "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": META_RECOVERY_TEMPLATE_CARTFLOW_V1,
            "WHATSAPP_META_RECOVERY_TEMPLATE_LANGUAGE": "ar",
        },
        clear=False,
    )
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_exact_payload_cartflow_cart_reminder_ar_v1(
        self,
        mock_post: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "wamid.MAP1"}]}
        mock_post.return_value = mock_resp

        recovery_copy = (
            "هلا 👋 لاحظنا إنك ما كمّلت الطلب — نقدر نساعدك بخطوة بسيطة إذا حاب."
        )
        out = send_whatsapp_message(
            "+966500000100",
            recovery_copy,
            {
                "recovery_key": "rk-map",
                "store_display_name": "متجر الأمان",
                "store_slug": "aman-store",
                "checkout_url": "https://merchant.com/cart/restore/abc123",
            },
        )
        self.assertTrue(out["ok"])
        payload = mock_post.call_args[1]["json"]
        from services.meta_recovery_template_contract_v1 import BUTTON_QUICK_REPLY_PAYLOAD
        from services.recovery_checkout_redirect_v1 import resolve_checkout_redirect_token

        comps = payload["template"]["components"]
        self.assertEqual(comps[0]["type"], "body")
        self.assertEqual(comps[0]["parameters"][0]["text"], "متجر الأمان")
        self.assertEqual(comps[1]["type"], "button")
        self.assertEqual(comps[1]["sub_type"], "url")
        url_param = comps[1]["parameters"][0]["text"]
        resolved = resolve_checkout_redirect_token(url_param, check_archived=False)
        self.assertTrue(resolved.ok)
        assert resolved.claims is not None
        self.assertEqual(
            resolved.claims.destination_url,
            "https://merchant.com/cart/restore/abc123",
        )
        self.assertEqual(comps[2]["sub_type"], "quick_reply")
        self.assertEqual(comps[2]["parameters"][0]["payload"], BUTTON_QUICK_REPLY_PAYLOAD)
        self.assertNotEqual(
            comps[0]["parameters"][0]["text"],
            recovery_copy,
        )
        self.assertNotIn(recovery_copy, str(payload))

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-VALUE",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
            "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": META_RECOVERY_TEMPLATE_CARTFLOW_V1,
        },
        clear=False,
    )
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_full_recovery_message_never_used_as_param(
        self,
        mock_post: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "wamid.X"}]}
        mock_post.return_value = mock_resp
        msg = "FULL_RECOVERY_MESSAGE_BODY_UNIQUE"
        send_whatsapp_message(
            "+966500000101",
            msg,
            {
                "store_display_name": "متجر",
                "template_parameters": ["متجر"],
                "checkout_url": "https://merchant.com/cart/restore/abc123",
            },
        )
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(
            payload["template"]["components"][0]["parameters"][0]["text"],
            "متجر",
        )
        self.assertNotIn(msg, str(payload))

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": META_RECOVERY_TEMPLATE_CARTFLOW_V1,
        },
        clear=False,
    )
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_missing_store_display_name_fails_before_http(
        self,
        mock_post: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        with patch(
            "services.whatsapp_production_reality_v2.resolve_store_for_template_enforcement",
            return_value=None,
        ):
            out = send_whatsapp_message(
                "+966500000102",
                "recovery text",
                {"store_slug": "demo", "recovery_key": "rk"},
            )
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "meta_store_display_name_missing")
        mock_post.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_ACCESS_TOKEN": "tok",
            "WHATSAPP_PHONE_NUMBER_ID": "pn1",
        },
        clear=False,
    )
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_missing_template_name_fails_before_http(
        self,
        mock_post: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        os.environ.pop("WHATSAPP_META_RECOVERY_TEMPLATE_NAME", None)
        out = send_whatsapp_message(
            "+966500000103",
            "body",
            {"store_display_name": "متجر", "recovery_key": "rk"},
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "meta_template_name_missing")
        mock_post.assert_not_called()

    @patch.dict(os.environ, {"WHATSAPP_PROVIDER": "twilio"}, clear=False)
    @patch(
        "services.whatsapp_send.send_whatsapp",
        return_value={"ok": True, "sid": "SM_tw", "status": "queued", "provider": "twilio"},
    )
    def test_twilio_path_unchanged_uses_full_body(self, mock_send: MagicMock) -> None:
        out = send_whatsapp_message(
            "+966500000104",
            "full recovery for twilio",
            {"store_display_name": "ignored-for-twilio"},
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["provider"], PROVIDER_TWILIO)
        self.assertEqual(mock_send.call_args[0][1], "full recovery for twilio")

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_ACCESS_TOKEN": "tok-secret",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
        },
        clear=False,
    )
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=True)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_session_text_still_uses_body(
        self,
        mock_post: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "wamid.S"}]}
        mock_post.return_value = mock_resp
        body = "session freeform recovery line"
        out = send_whatsapp_message(
            "+966500000105",
            body,
            {"message_mode": MODE_SESSION_TEXT, "store_display_name": "متجر"},
        )
        self.assertTrue(out["ok"])
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["type"], "text")
        self.assertEqual(payload["text"]["body"], body)

    def test_no_main_provider_business_logic(self) -> None:
        import main as main_mod

        src = inspect.getsource(main_mod._run_recovery_sequence_after_cart_abandoned_impl)
        self.assertIn("store_display_name", src)
        self.assertNotIn("build_meta_template_payload", src)
        self.assertNotIn("graph.facebook.com", src)
        self.assertNotIn("template_parameters", src)
        self.assertNotIn("message_mode", src)
        self.assertIn("send_recovery_whatsapp_via_provider", src)

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-NEVER",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
            "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": META_RECOVERY_TEMPLATE_CARTFLOW_V1,
        },
        clear=False,
    )
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_no_secret_leakage(
        self,
        mock_post: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "error": {"message": "Invalid OAuth access token.", "code": 190}
        }
        mock_post.return_value = mock_resp
        out = send_whatsapp_message(
            "+966500000106",
            "body",
            {
                "store_display_name": "متجر",
                "checkout_url": "https://merchant.com/cart/restore/abc123",
            },
        )
        self.assertNotIn("tok-secret-NEVER", str(out))
        self.assertNotIn("Bearer ", str(out))


if __name__ == "__main__":
    unittest.main()
