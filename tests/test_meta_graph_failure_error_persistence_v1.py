# -*- coding: utf-8 -*-
"""
Meta Graph failure error persistence — mocked rejection survives into CartRecoveryLog context.
"""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from services.recovery_message_context_v1 import (
    merge_persist_context,
    serialize_context_json,
)
from services.whatsapp_provider import PROVIDER_META, send_whatsapp_message
from services.whatsapp_providers.meta_cloud import _safe_meta_error_fields


class SafeMetaErrorFieldsTests(unittest.TestCase):
    def test_extracts_code_subcode_message_and_fbtrace(self) -> None:
        code, sub, msg, retryable, trace = _safe_meta_error_fields(
            {
                "error": {
                    "message": "Invalid parameter",
                    "code": 100,
                    "error_subcode": 33,
                    "fbtrace_id": "AbC123_xy-Z",
                }
            },
            400,
        )
        self.assertEqual(code, "100")
        self.assertEqual(sub, "33")
        self.assertEqual(msg, "Invalid parameter")
        self.assertFalse(retryable)
        self.assertEqual(trace, "AbC123_xy-Z")

    def test_oauth_message_sanitized(self) -> None:
        code, _sub, msg, _r, _t = _safe_meta_error_fields(
            {"error": {"message": "Invalid OAuth access token.", "code": 190}},
            401,
        )
        self.assertEqual(code, "190")
        self.assertEqual(msg, "meta_auth_or_token_error")


class ContextMergeKeepsProviderErrorsTests(unittest.TestCase):
    def test_merge_persist_keeps_error_fields(self) -> None:
        ctx = merge_persist_context(
            message_context={
                "provider": "meta",
                "provider_status": "http_400",
                "error_code": "100",
                "error_subcode": "33",
                "error_message_safe": "Invalid parameter",
                "error_trace_id": "AbC123",
                "send_status": "whatsapp_failed",
            },
            recovery_key="demo:cf_cart_err_persist",
            store_slug="demo",
            session_id="sess-err",
            cart_id="cart-err",
            phone="+966546518011",
            message="freeform ignored",
            status="whatsapp_failed",
            step=1,
            provider="meta",
        )
        self.assertEqual(ctx.provider, "meta")
        self.assertEqual(ctx.error_code, "100")
        self.assertEqual(ctx.error_subcode, "33")
        self.assertEqual(ctx.error_message_safe, "Invalid parameter")
        self.assertEqual(ctx.provider_status, "http_400")
        self.assertEqual(ctx.error_trace_id, "AbC123")
        blob = json.loads(serialize_context_json(ctx))
        self.assertEqual(blob["error_code"], "100")
        self.assertEqual(blob["error_subcode"], "33")
        self.assertEqual(blob["error_message_safe"], "Invalid parameter")
        self.assertEqual(blob["provider_status"], "http_400")
        self.assertNotIn("Bearer", json.dumps(blob))
        self.assertNotIn("access_token", json.dumps(blob).lower())


class MetaGraphRejectionPersistenceE2ETests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-NEVER-LOG",
            "WHATSAPP_PHONE_NUMBER_ID": "pn-err-1",
            "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": "cartflow_cart_reminder_ar_v2",
            "WHATSAPP_META_RECOVERY_TEMPLATE_LANGUAGE": "ar",
        },
        clear=False,
    )
    @patch("services.whatsapp_provider._proven_session_window_allows_freeform", return_value=False)
    @patch("services.whatsapp_provider._apply_shared_preflight_guards", return_value=None)
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_mocked_graph_rejection_survives_into_persisted_context(
        self,
        mock_post: MagicMock,
        _pre: MagicMock,
        _win: MagicMock,
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "error": {
                "message": "(#100) Invalid parameter",
                "type": "OAuthException",
                "code": 100,
                "error_subcode": 2388044,
                "fbtrace_id": "AGxYz_trace99",
            }
        }
        mock_post.return_value = mock_resp

        import main as main_mod

        out = main_mod.send_recovery_whatsapp_via_provider(
            "+966546518011",
            "سبب اخر\n\nhttps://example.com/recover",
            {
                "store_display_name": "مساعد المتجر",
                "store_name": "مساعد المتجر",
                "checkout_url": "https://smartreplyai.net/demo/store/checkout",
                "recovery_key": "demo:cf_cart_meta_err_persist",
                "store_slug": "demo",
                "session_id": "sess-meta-err",
                "reason_tag": "other",
            },
        )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("provider"), PROVIDER_META)
        self.assertEqual(out.get("error_code"), "100")
        self.assertEqual(out.get("error_subcode"), "2388044")
        self.assertIn("Invalid parameter", str(out.get("error_message_safe") or ""))
        self.assertEqual(out.get("error_trace_id"), "AGxYz_trace99")
        self.assertEqual(out.get("provider_status"), "http_400")
        self.assertNotIn("tok-secret-NEVER-LOG", str(out))

        fields = main_mod._wa_result_provider_persist_kwargs(out)
        self.assertEqual(fields["error_code"], "100")
        self.assertEqual(fields["error_subcode"], "2388044")
        self.assertEqual(fields["error_trace_id"], "AGxYz_trace99")

        fail_ctx = {
            "provider": fields.get("provider") or "",
            "provider_status": fields.get("provider_status") or "",
            "error_code": fields.get("error_code") or "",
            "error_subcode": fields.get("error_subcode") or "",
            "error_message_safe": fields.get("error_message_safe") or "",
            "error_trace_id": fields.get("error_trace_id") or "",
            "send_status": "whatsapp_failed",
        }
        persisted = merge_persist_context(
            message_context=fail_ctx,
            recovery_key="demo:cf_cart_meta_err_persist",
            store_slug="demo",
            session_id="sess-meta-err",
            cart_id="cf_cart_meta_err_persist",
            phone="+966546518011",
            message="سبب اخر",
            status="whatsapp_failed",
            step=1,
            provider="meta",
        )
        blob = json.loads(serialize_context_json(persisted))
        self.assertEqual(blob["error_code"], "100")
        self.assertEqual(blob["error_subcode"], "2388044")
        self.assertIn("Invalid parameter", blob["error_message_safe"])
        self.assertEqual(blob["provider_status"], "http_400")
        self.assertEqual(blob["error_trace_id"], "AGxYz_trace99")
        self.assertEqual(blob["provider"], "meta")
        dumped = json.dumps(blob)
        self.assertNotIn("tok-secret", dumped)
        self.assertNotIn("Authorization", dumped)
        self.assertNotIn("Bearer", dumped)


class EvidenceEndpointExposesErrorsTests(unittest.TestCase):
    def test_evidence_handler_includes_error_fields(self) -> None:
        import inspect

        from routes import dev_diagnostics

        src = inspect.getsource(dev_diagnostics.dev_meta_pilot_evidence)
        self.assertIn("error_code", src)
        self.assertIn("error_subcode", src)
        self.assertIn("error_message_safe", src)
        self.assertIn("provider_status", src)
        self.assertIn("context_from_log_row", src)


if __name__ == "__main__":
    unittest.main()
