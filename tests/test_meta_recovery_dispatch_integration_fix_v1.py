# -*- coding: utf-8 -*-
"""
Meta Recovery Dispatch Integration Fix V1 — service-level tests.

Proves Scheduler-style recovery send → provider boundary → mocked Meta Graph
with v2 template contract, failure provider persistence, and Twilio regression.
"""
from __future__ import annotations

import inspect
import os
import unittest
from unittest.mock import MagicMock, patch

from services.meta_recovery_template_contract_v1 import TEMPLATE_NAME as META_V2_TEMPLATE
from services.whatsapp_provider import (
    META_RECOVERY_TEMPLATE_CARTFLOW_V2,
    PROVIDER_META,
    PROVIDER_TWILIO,
    send_whatsapp_message,
)


_STORE_NAME = "مساعد المتجر"
_CHECKOUT = "https://smartreplyai.net/demo/store/checkout"
_PHONE = "+966546518011"
_FREEFORM = "سبب اخر\n\nhttps://smartreplyai.net/api/recover/r?t=fake"


def _meta_env() -> dict[str, str]:
    return {
        "WHATSAPP_PROVIDER": "meta",
        "WHATSAPP_ACCESS_TOKEN": "tok-test-meta-dispatch",
        "WHATSAPP_PHONE_NUMBER_ID": "pn-dispatch-1",
        "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": META_V2_TEMPLATE,
        "WHATSAPP_META_RECOVERY_TEMPLATE_LANGUAGE": "ar",
    }


def _recovery_send_context(**extra: object) -> dict:
    ctx: dict = {
        "reason_tag": "other",
        "recovery_key": "demo:cf_cart_meta_dispatch_test",
        "store_slug": "demo",
        "store_name": _STORE_NAME,
        "store_display_name": _STORE_NAME,
        "checkout_url": _CHECKOUT,
        "session_id": "sess-meta-dispatch",
    }
    ctx.update(extra)
    return ctx


class MetaDispatchSuccessTests(unittest.TestCase):
    @patch.dict(os.environ, _meta_env(), clear=False)
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.twilio_provider.send_via_twilio")
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_scheduler_style_recovery_reaches_mocked_graph_once(
        self,
        mock_post: MagicMock,
        mock_twilio: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        """Recovery freeform body must not become Meta {{1}}; Graph once; no Twilio."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "wamid.DISPATCH.OK"}]}
        mock_post.return_value = mock_resp

        import main as main_mod

        out = main_mod.send_recovery_whatsapp_via_provider(
            _PHONE,
            _FREEFORM,
            _recovery_send_context(),
        )

        self.assertTrue(out.get("ok") is True)
        self.assertEqual(out.get("provider"), PROVIDER_META)
        self.assertEqual(out.get("external_message_id") or out.get("sid"), "wamid.DISPATCH.OK")
        self.assertEqual(out.get("accepted"), True)
        mock_twilio.assert_not_called()
        self.assertEqual(mock_post.call_count, 1)

        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["type"], "template")
        self.assertEqual(payload["template"]["name"], META_RECOVERY_TEMPLATE_CARTFLOW_V2)
        comps = payload["template"]["components"]
        body_text = comps[0]["parameters"][0]["text"]
        self.assertEqual(body_text, _STORE_NAME)
        self.assertNotIn("سبب اخر", body_text)
        self.assertNotIn("recover/r", body_text)

        self.assertEqual(comps[1]["type"], "button")
        self.assertEqual(comps[1]["sub_type"], "url")
        token = comps[1]["parameters"][0]["text"]
        self.assertTrue(token)
        self.assertNotEqual(token, _CHECKOUT)
        from services.recovery_checkout_redirect_v1 import resolve_checkout_redirect_token

        resolved = resolve_checkout_redirect_token(token, check_archived=False)
        self.assertTrue(resolved.ok)
        assert resolved.claims is not None
        self.assertEqual(resolved.claims.destination_url, _CHECKOUT)

        # QUICK_REPLY has static payload — no runtime merchant param
        self.assertEqual(comps[2]["sub_type"], "quick_reply")


class MetaDispatchFailurePersistTests(unittest.TestCase):
    @patch.dict(os.environ, _meta_env(), clear=False)
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.twilio_provider.send_via_twilio")
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_meta_graph_failure_keeps_provider_meta_no_twilio_fallback(
        self,
        mock_post: MagicMock,
        mock_twilio: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "error": {"message": "Invalid parameter", "code": 100, "error_subcode": 33}
        }
        mock_post.return_value = mock_resp

        import main as main_mod

        out = main_mod.send_recovery_whatsapp_via_provider(
            _PHONE,
            _FREEFORM,
            _recovery_send_context(),
        )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("provider"), PROVIDER_META)
        self.assertTrue(out.get("error_code") or out.get("error"))
        mock_twilio.assert_not_called()
        self.assertEqual(mock_post.call_count, 1)

        fields = main_mod._wa_result_provider_persist_kwargs(out)
        self.assertEqual(fields.get("provider"), PROVIDER_META)
        self.assertFalse(fields.get("provider_accepted"))
        self.assertTrue(fields.get("error_code") or fields.get("error_message_safe"))

    @patch.dict(os.environ, _meta_env(), clear=False)
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.twilio_provider.send_via_twilio")
    def test_missing_checkout_fails_meta_with_provider_persisted(
        self,
        mock_twilio: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        """Schedule 1114-class failure: Meta resolves, checkout missing → provider still meta."""
        import main as main_mod

        ctx = _recovery_send_context()
        ctx.pop("checkout_url", None)
        out = main_mod.send_recovery_whatsapp_via_provider(_PHONE, _FREEFORM, ctx)

        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("provider"), PROVIDER_META)
        self.assertEqual(out.get("error_code"), "meta_checkout_url_missing")
        mock_twilio.assert_not_called()

        fields = main_mod._wa_result_provider_persist_kwargs(out)
        self.assertEqual(fields["provider"], PROVIDER_META)
        self.assertEqual(fields["error_code"], "meta_checkout_url_missing")


class ReasonArmCheckoutPropagationTests(unittest.TestCase):
    def test_reason_arm_synth_copies_checkout_url(self) -> None:
        import main as main_mod

        src = inspect.getsource(
            main_mod._schedule_normal_recovery_after_cart_recovery_reason_saved
        )
        self.assertIn('"checkout_url"', src)
        self.assertIn('"cart_url"', src)

    def test_failure_path_persists_provider_from_wa_result(self) -> None:
        import main as main_mod

        src = inspect.getsource(
            main_mod._run_recovery_sequence_after_cart_abandoned_impl
        )
        self.assertIn("_wa_result_provider_persist_kwargs", src)
        fail_idx = src.find('status="whatsapp_failed"')
        self.assertGreater(fail_idx, 0)
        # Failure persist block must pass provider= (not only success path)
        window = src[fail_idx : fail_idx + 800]
        self.assertIn("provider=", window)
        self.assertIn("_wa_prov", window)

    def test_arm_context_includes_checkout_from_abandoned_cart(self) -> None:
        import main as main_mod

        src = inspect.getsource(main_mod._build_recovery_context_from_arm)
        self.assertIn("checkout_url", src)
        self.assertIn("cart_url", src)


class TwilioRegressionTests(unittest.TestCase):
    @patch.dict(os.environ, {"WHATSAPP_PROVIDER": "twilio"}, clear=False)
    @patch(
        "services.whatsapp_send.send_whatsapp",
        return_value={
            "ok": True,
            "sid": "SMtwilio_dispatch_reg",
            "status": "queued",
            "provider": "twilio",
        },
    )
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_twilio_provider_unchanged(
        self,
        mock_meta_post: MagicMock,
        mock_tw: MagicMock,
    ) -> None:
        import main as main_mod

        out = main_mod.send_recovery_whatsapp_via_provider(
            _PHONE,
            _FREEFORM,
            _recovery_send_context(),
        )
        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("provider"), PROVIDER_TWILIO)
        self.assertEqual(out.get("sid"), "SMtwilio_dispatch_reg")
        mock_tw.assert_called_once()
        mock_meta_post.assert_not_called()
        # Twilio still receives freeform body (unchanged behavior)
        called_args = mock_tw.call_args[0]
        self.assertEqual(called_args[0], _PHONE)
        self.assertIn("سبب اخر", called_args[1])


class BoundaryDirectTests(unittest.TestCase):
    """Same assertions via provider module (no main alias)."""

    @patch.dict(os.environ, _meta_env(), clear=False)
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_send_whatsapp_message_v2_graph(
        self,
        mock_post: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"messages": [{"id": "wamid.BOUND"}]},
        )
        out = send_whatsapp_message(_PHONE, _FREEFORM, _recovery_send_context())
        self.assertEqual(out["provider"], PROVIDER_META)
        self.assertEqual(mock_post.call_count, 1)
        name = mock_post.call_args[1]["json"]["template"]["name"]
        self.assertEqual(name, META_V2_TEMPLATE)


if __name__ == "__main__":
    unittest.main()
