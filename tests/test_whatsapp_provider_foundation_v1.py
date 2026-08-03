# -*- coding: utf-8 -*-
"""WhatsApp provider foundation V1 — Meta/Twilio selector + Meta Cloud send."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

import requests

from services.whatsapp_provider import (
    MODE_SESSION_TEXT,
    MODE_TEMPLATE,
    PROVIDER_META,
    PROVIDER_TWILIO,
    resolve_whatsapp_provider,
    send_whatsapp_message,
)
from services.whatsapp_providers.meta_cloud import (
    build_meta_template_payload,
    normalize_meta_recipient,
    send_via_meta,
)
from services.whatsapp_providers.contracts import WhatsAppProviderRequest


class ResolveProviderTests(unittest.TestCase):
    def test_default_provider_is_twilio_when_env_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WHATSAPP_PROVIDER", None)
            self.assertEqual(resolve_whatsapp_provider(), PROVIDER_TWILIO)

    def test_explicit_twilio(self) -> None:
        with patch.dict(os.environ, {"WHATSAPP_PROVIDER": "twilio"}, clear=False):
            self.assertEqual(resolve_whatsapp_provider(), PROVIDER_TWILIO)

    def test_explicit_meta(self) -> None:
        with patch.dict(os.environ, {"WHATSAPP_PROVIDER": "meta"}, clear=False):
            self.assertEqual(resolve_whatsapp_provider(), PROVIDER_META)

    def test_unknown_falls_back_to_twilio(self) -> None:
        with patch.dict(os.environ, {"WHATSAPP_PROVIDER": "something_else"}, clear=False):
            self.assertEqual(resolve_whatsapp_provider(), PROVIDER_TWILIO)

    def test_context_provider_override(self) -> None:
        self.assertEqual(resolve_whatsapp_provider("meta"), PROVIDER_META)
        self.assertEqual(resolve_whatsapp_provider("twilio"), PROVIDER_TWILIO)


class MetaPayloadTests(unittest.TestCase):
    def test_normalize_recipient(self) -> None:
        self.assertEqual(normalize_meta_recipient("+966 50 000 0000"), "966500000000")
        self.assertEqual(normalize_meta_recipient("bad"), "")

    def test_template_payload_construction(self) -> None:
        payload = build_meta_template_payload(
            to_digits="966500000000",
            template_name="cartflow_recovery",
            template_language="ar",
            template_parameters=["hello"],
        )
        self.assertEqual(payload["messaging_product"], "whatsapp")
        self.assertEqual(payload["type"], "template")
        self.assertEqual(payload["to"], "966500000000")
        self.assertEqual(payload["template"]["name"], "cartflow_recovery")
        self.assertEqual(payload["template"]["language"]["code"], "ar")
        self.assertEqual(
            payload["template"]["components"][0]["parameters"][0]["text"],
            "hello",
        )
        # No secrets in payload
        blob = str(payload).lower()
        self.assertNotIn("bearer", blob)
        self.assertNotIn("access_token", blob)


class MetaSendTests(unittest.TestCase):
    def _req(self, **kwargs: object) -> WhatsAppProviderRequest:
        base = dict(
            to_phone="+966500000001",
            provider=PROVIDER_META,
            message_mode=MODE_TEMPLATE,
            template_name="hello_world",
            template_language="en_US",
            template_parameters=[],
            recovery_key="rk-1",
            store_slug="demo",
        )
        base.update(kwargs)
        return WhatsAppProviderRequest(**base)  # type: ignore[arg-type]

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_ACCESS_TOKEN": "",
            "WHATSAPP_API_TOKEN": "",
            "WHATSAPP_CLOUD_API_TOKEN": "",
            "META_WHATSAPP_TOKEN": "",
            "WHATSAPP_PHONE_NUMBER_ID": "pn1",
        },
        clear=False,
    )
    def test_missing_meta_token(self) -> None:
        out = send_via_meta(self._req())
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "meta_access_token_missing")
        self.assertFalse(out.get("accepted"))

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-VALUE",
            "WHATSAPP_PHONE_NUMBER_ID": "",
            "WHATSAPP_PHONE_ID": "",
        },
        clear=False,
    )
    def test_missing_phone_number_id(self) -> None:
        out = send_via_meta(self._req())
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "meta_phone_number_id_missing")

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-VALUE",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
        },
        clear=False,
    )
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_meta_accepted_response(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "messages": [{"id": "wamid.ABC123"}],
        }
        mock_post.return_value = mock_resp

        out = send_via_meta(self._req())
        self.assertTrue(out["ok"])
        self.assertTrue(out["accepted"])
        self.assertEqual(out["sid"], "wamid.ABC123")
        self.assertEqual(out["external_message_id"], "wamid.ABC123")
        self.assertEqual(out["provider"], PROVIDER_META)
        self.assertFalse(out["raw_payload_stored"])
        call_kwargs = mock_post.call_args
        self.assertIn("graph.facebook.com", call_kwargs[0][0])
        self.assertIn("/pn123/messages", call_kwargs[0][0])
        headers = call_kwargs[1]["headers"]
        self.assertEqual(headers["Authorization"], "Bearer tok-secret-VALUE")

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-VALUE",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
        },
        clear=False,
    )
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_meta_graph_error_response(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "error": {
                "message": "Session has expired",
                "code": 190,
                "error_subcode": 463,
            }
        }
        mock_post.return_value = mock_resp

        out = send_via_meta(self._req())
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "190")
        self.assertEqual(out["error_subcode"], "463")
        self.assertIn("Session has expired", out["error_message_safe"] or "")
        self.assertNotIn("tok-secret-VALUE", str(out))

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-VALUE",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
        },
        clear=False,
    )
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_timeout(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.Timeout("timed out")
        out = send_via_meta(self._req())
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "provider_timeout")
        self.assertTrue(out["retryable"])

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-VALUE",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
        },
        clear=False,
    )
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_malformed_response(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("no json")
        mock_post.return_value = mock_resp
        out = send_via_meta(self._req())
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "invalid_json_response")


class ProviderBoundaryTests(unittest.TestCase):
    @patch.dict(os.environ, {"WHATSAPP_PROVIDER": "twilio"}, clear=False)
    @patch(
        "services.whatsapp_send.send_whatsapp",
        return_value={"ok": True, "sid": "SM123", "status": "queued", "provider": "twilio"},
    )
    def test_explicit_twilio_selection_delegates(self, mock_tw: MagicMock) -> None:
        out = send_whatsapp_message(
            "+966500000002",
            "hello",
            {"recovery_key": "rk", "store_slug": "s1"},
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["sid"], "SM123")
        self.assertEqual(out["provider"], PROVIDER_TWILIO)
        mock_tw.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-VALUE",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
            "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": "cartflow_recovery",
            "WHATSAPP_META_RECOVERY_TEMPLATE_LANGUAGE": "ar",
        },
        clear=False,
    )
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_explicit_meta_selection(
        self,
        mock_post: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "wamid.XYZ"}]}
        mock_post.return_value = mock_resp

        out = send_whatsapp_message(
            "+966500000003",
            "recovery body MUST NOT appear as {{1}}",
            {
                "recovery_key": "rk-meta",
                "store_slug": "s1",
                "store_display_name": "متجر الأمان",
            },
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["provider"], PROVIDER_META)
        self.assertEqual(out["message_mode"], MODE_TEMPLATE)
        self.assertEqual(out["external_message_id"], "wamid.XYZ")
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["type"], "template")
        self.assertEqual(payload["template"]["name"], "cartflow_recovery")
        body_text = payload["template"]["components"][0]["parameters"][0]["text"]
        self.assertEqual(body_text, "متجر الأمان")
        self.assertNotIn("MUST NOT appear", body_text)

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-VALUE",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
        },
        clear=False,
    )
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    def test_meta_missing_template_name_fails_safe(
        self, _pre: MagicMock, _win: MagicMock
    ) -> None:
        os.environ.pop("WHATSAPP_META_RECOVERY_TEMPLATE_NAME", None)
        out = send_whatsapp_message("+966500000004", "body", {"recovery_key": "rk"})
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "meta_template_name_missing")

    @patch.dict(os.environ, {"WHATSAPP_PROVIDER": "meta"}, clear=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.send_via_meta")
    @patch("services.whatsapp_providers.twilio_provider.send_via_twilio")
    def test_no_automatic_fallback_to_twilio(
        self,
        mock_twilio: MagicMock,
        mock_meta: MagicMock,
        _pre: MagicMock,
    ) -> None:
        mock_meta.return_value = {
            "ok": False,
            "accepted": False,
            "provider": PROVIDER_META,
            "error_code": "190",
            "error": "Session has expired",
            "raw_payload_stored": False,
            "message_mode": MODE_TEMPLATE,
        }
        with patch.dict(
            os.environ,
            {"WHATSAPP_META_RECOVERY_TEMPLATE_NAME": "t1"},
            clear=False,
        ):
            with patch(
                "services.whatsapp_provider._proven_session_window_allows_freeform",
                return_value=False,
            ):
                out = send_whatsapp_message(
                    "+966500000005",
                    "x",
                    {"recovery_key": "rk", "store_display_name": "متجر"},
                )
        self.assertFalse(out["ok"])
        self.assertEqual(out["provider"], PROVIDER_META)
        mock_twilio.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-NEVER-LOG",
            "WHATSAPP_PHONE_NUMBER_ID": "pn123",
            "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": "t1",
        },
        clear=False,
    )
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_no_secret_leakage_in_result(
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
        out = send_whatsapp_message("+966500000006", "body", {"recovery_key": "rk"})
        blob = str(out)
        self.assertNotIn("tok-secret-NEVER-LOG", blob)
        self.assertNotIn("Bearer ", blob)


class RecoveryPathWiringTests(unittest.TestCase):
    def test_recovery_path_imports_provider_boundary(self) -> None:
        import main as main_mod

        self.assertTrue(hasattr(main_mod, "send_recovery_whatsapp_via_provider"))
        # Bound to provider-neutral send
        from services.whatsapp_provider import send_whatsapp_message

        self.assertIs(
            main_mod.send_recovery_whatsapp_via_provider,
            send_whatsapp_message,
        )

    def test_recovery_impl_source_calls_provider_not_direct_send_whatsapp(self) -> None:
        import inspect

        import main as main_mod

        src = inspect.getsource(main_mod._run_recovery_sequence_after_cart_abandoned_impl)
        self.assertIn("send_recovery_whatsapp_via_provider", src)
        # Direct send_whatsapp call removed from recovery send site
        self.assertNotIn("wa_result = send_whatsapp(", src)


class TwilioBehaviorUnchangedTests(unittest.TestCase):
    @patch.dict(os.environ, {"WHATSAPP_PROVIDER": "twilio"}, clear=False)
    @patch(
        "services.whatsapp_send.send_whatsapp",
        return_value={"ok": True, "sid": "SMlegacy", "status": "queued"},
    )
    def test_default_path_preserves_legacy_shape(self, mock_send: MagicMock) -> None:
        os.environ.pop("WHATSAPP_PROVIDER", None)
        out = send_whatsapp_message("966500000007", "hi", {"reason_tag": "price"})
        self.assertTrue(out["ok"])
        self.assertEqual(out["sid"], "SMlegacy")
        self.assertIn("accepted", out)
        mock_send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
