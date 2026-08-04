# -*- coding: utf-8 -*-
"""Recovery Template V1 Buttons upgrade — contract, send params, quick-reply inbound."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from services.meta_recovery_template_contract_v1 import (
    BUTTON_QUICK_REPLY_PAYLOAD,
    BUTTON_QUICK_REPLY_TEXT,
    BUTTON_URL_TEXT,
    TEMPLATE_BODY_TEXT,
    TEMPLATE_CHECKOUT_URL_EXAMPLE,
    TEMPLATE_NAME,
    build_template_payload,
    decode_checkout_url_button_param,
    encode_checkout_url_button_param,
    is_customer_support_quick_reply,
    validate_template_contract,
)
from services.whatsapp_provider import (
    META_RECOVERY_TEMPLATE_CARTFLOW_V1,
    resolve_meta_template_button_url_param,
    resolve_meta_template_parameters,
    send_whatsapp_message,
)
from services.whatsapp_providers.meta_cloud import build_meta_template_payload


class ContractButtonsTests(unittest.TestCase):
    def test_body_unchanged(self) -> None:
        self.assertIn("{{1}}", TEMPLATE_BODY_TEXT)
        self.assertEqual(build_template_payload()["components"][0]["text"], TEMPLATE_BODY_TEXT)

    def test_url_and_quick_reply_buttons(self) -> None:
        payload = build_template_payload()
        self.assertEqual(validate_template_contract(payload), [])
        buttons = payload["components"][1]["buttons"]
        self.assertEqual(buttons[0]["type"], "URL")
        self.assertEqual(buttons[0]["text"], BUTTON_URL_TEXT)
        self.assertTrue(buttons[0]["url"].endswith("{{1}}"))
        self.assertEqual(buttons[1]["type"], "QUICK_REPLY")
        self.assertEqual(buttons[1]["text"], BUTTON_QUICK_REPLY_TEXT)

    def test_checkout_url_roundtrip_token(self) -> None:
        token = encode_checkout_url_button_param(TEMPLATE_CHECKOUT_URL_EXAMPLE)
        self.assertIsNotNone(token)
        self.assertEqual(decode_checkout_url_button_param(token or ""), TEMPLATE_CHECKOUT_URL_EXAMPLE)

    def test_same_template_name(self) -> None:
        self.assertEqual(TEMPLATE_NAME, "cartflow_cart_reminder_ar_v2")
        from services.whatsapp_provider import META_RECOVERY_TEMPLATE_CARTFLOW_V2

        self.assertEqual(META_RECOVERY_TEMPLATE_CARTFLOW_V2, TEMPLATE_NAME)
        self.assertEqual(META_RECOVERY_TEMPLATE_CARTFLOW_V1, "cartflow_cart_reminder_ar_v1")


class RuntimeParamsTests(unittest.TestCase):
    def test_store_name_and_checkout_url(self) -> None:
        params, err = resolve_meta_template_parameters(
            {"store_name": "متجر الأمان"},
            template_name=TEMPLATE_NAME,
        )
        self.assertIsNone(err)
        self.assertEqual(params, ["متجر الأمان"])
        btn, berr = resolve_meta_template_button_url_param(
            {"checkout_url": TEMPLATE_CHECKOUT_URL_EXAMPLE},
            template_name=TEMPLATE_NAME,
        )
        self.assertIsNone(berr)
        from services.recovery_checkout_redirect_v1 import resolve_checkout_redirect_token

        resolved = resolve_checkout_redirect_token(btn, check_archived=False)
        self.assertTrue(resolved.ok)
        assert resolved.claims is not None
        self.assertEqual(resolved.claims.destination_url, TEMPLATE_CHECKOUT_URL_EXAMPLE)

    def test_missing_checkout_url(self) -> None:
        btn, berr = resolve_meta_template_button_url_param(
            {"store_name": "متجر"},
            template_name=TEMPLATE_NAME,
        )
        self.assertIsNone(btn)
        self.assertEqual(berr, "meta_checkout_url_missing")

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_ACCESS_TOKEN": "tok-secret",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
            "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": TEMPLATE_NAME,
            "WHATSAPP_META_RECOVERY_TEMPLATE_LANGUAGE": "ar",
        },
        clear=False,
    )
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_send_includes_url_button_param(
        self, mock_post: MagicMock, _pre: MagicMock, _win: MagicMock
    ) -> None:
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"messages": [{"id": "wamid.BTN1"}]}
        )
        out = send_whatsapp_message(
            "+966500000200",
            "ignored recovery body",
            {
                "store_name": "متجر الأمان",
                "checkout_url": TEMPLATE_CHECKOUT_URL_EXAMPLE,
                "recovery_key": "rk-btn",
            },
        )
        self.assertTrue(out["ok"])
        payload = mock_post.call_args[1]["json"]
        comps = payload["template"]["components"]
        self.assertEqual(comps[0]["type"], "body")
        self.assertEqual(comps[0]["parameters"][0]["text"], "متجر الأمان")
        self.assertEqual(comps[1]["type"], "button")
        self.assertEqual(comps[1]["sub_type"], "url")
        self.assertEqual(comps[1]["index"], "0")
        from services.recovery_checkout_redirect_v1 import resolve_checkout_redirect_token

        resolved = resolve_checkout_redirect_token(
            comps[1]["parameters"][0]["text"], check_archived=False
        )
        self.assertTrue(resolved.ok)
        assert resolved.claims is not None
        self.assertEqual(resolved.claims.destination_url, TEMPLATE_CHECKOUT_URL_EXAMPLE)
        self.assertEqual(comps[2]["sub_type"], "quick_reply")
        self.assertEqual(comps[2]["parameters"][0]["payload"], BUTTON_QUICK_REPLY_PAYLOAD)
        self.assertNotIn("tok-secret", str(payload))
        self.assertNotIn(TEMPLATE_CHECKOUT_URL_EXAMPLE, comps[1]["parameters"][0]["text"])


class QuickReplyInboundTests(unittest.TestCase):
    def test_is_support_quick_reply(self) -> None:
        self.assertTrue(
            is_customer_support_quick_reply(text=BUTTON_QUICK_REPLY_TEXT, payload="")
        )
        self.assertTrue(
            is_customer_support_quick_reply(text="", payload=BUTTON_QUICK_REPLY_PAYLOAD)
        )
        self.assertFalse(is_customer_support_quick_reply(text="مرحبا", payload=""))

    @patch("services.meta_recovery_template_inbound_v1.continue_conversation_pipeline")
    @patch("services.meta_recovery_template_inbound_v1.persist_customer_interaction_event")
    def test_handle_support_button_no_ai(
        self, mock_persist: MagicMock, mock_pipe: MagicMock
    ) -> None:
        from services.meta_recovery_template_inbound_v1 import handle_meta_inbound_message

        mock_persist.return_value = True
        out = handle_meta_inbound_message(
            {
                "from": "966501234567",
                "message_id": "wamid.QR1",
                "text": BUTTON_QUICK_REPLY_TEXT,
                "button_payload": BUTTON_QUICK_REPLY_PAYLOAD,
                "type": "button",
            }
        )
        self.assertTrue(out["ok"])
        self.assertTrue(out["customer_requested_human_support"])
        self.assertTrue(out["interaction_event_stored"])
        self.assertFalse(out["ai_auto_reply"])
        mock_persist.assert_called_once()
        kwargs = mock_persist.call_args.kwargs
        self.assertTrue(kwargs["customer_requested_human_support"])
        mock_pipe.assert_called_once()

    @patch("services.meta_recovery_template_inbound_v1.handle_meta_inbound_message")
    def test_webhook_button_reaches_handler(self, mock_handle: MagicMock) -> None:
        from services.meta_whatsapp_webhook_v1 import (
            clear_webhook_state_for_tests,
            process_webhook_payload,
        )

        clear_webhook_state_for_tests()
        mock_handle.return_value = {"ok": True}
        process_webhook_payload(
            {
                "entry": [
                    {
                        "changes": [
                            {
                                "value": {
                                    "messages": [
                                        {
                                            "from": "966501234567",
                                            "id": "wamid.BTN",
                                            "type": "button",
                                            "button": {
                                                "text": BUTTON_QUICK_REPLY_TEXT,
                                                "payload": BUTTON_QUICK_REPLY_PAYLOAD,
                                            },
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        )
        mock_handle.assert_called_once()
        inbound = mock_handle.call_args[0][0]
        self.assertEqual(inbound["text"], BUTTON_QUICK_REPLY_TEXT)
        self.assertEqual(inbound["button_payload"], BUTTON_QUICK_REPLY_PAYLOAD)


class CheckoutRedirectTests(unittest.TestCase):
    def test_redirect_opens_checkout(self) -> None:
        from main import app
        from services.recovery_checkout_redirect_v1 import mint_checkout_redirect_token

        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk-legacy-test",
            now_ts=1_700_000_000,
        )
        client = TestClient(app)
        with patch(
            "routes.wa_checkout_redirect_v1.record_checkout_button_click",
            return_value={"ok": True},
        ):
            with patch(
                "services.recovery_checkout_redirect_v1.time.time",
                return_value=1_700_000_000,
            ):
                r = client.get(f"/wa/checkout/{token}", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers.get("location"), TEMPLATE_CHECKOUT_URL_EXAMPLE)

    def test_invalid_token(self) -> None:
        from main import app

        client = TestClient(app)
        r = client.get("/wa/checkout/not-a-valid-token!!!", follow_redirects=False)
        self.assertEqual(r.status_code, 400)


class NoProviderSwitchTests(unittest.TestCase):
    def test_default_still_twilio(self) -> None:
        from services.whatsapp_provider import resolve_whatsapp_provider

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WHATSAPP_PROVIDER", None)
            self.assertEqual(resolve_whatsapp_provider(), "twilio")

    def test_build_payload_helper_url_button(self) -> None:
        p = build_meta_template_payload(
            to_digits="9665",
            template_name=TEMPLATE_NAME,
            template_language="ar",
            template_parameters=["متجر"],
            template_button_url_param="abc",
            quick_reply_payload=BUTTON_QUICK_REPLY_PAYLOAD,
        )
        self.assertEqual(p["template"]["components"][1]["sub_type"], "url")
        self.assertNotIn("/messages", "message_templates")  # sanity


if __name__ == "__main__":
    unittest.main()
