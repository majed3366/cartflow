# -*- coding: utf-8 -*-
"""Meta Dispatch Request Evidence V1 — sanitized wire capture tests."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from services.meta_dispatch_request_evidence_v1 import (
    build_sanitized_dispatch_evidence,
    clear_meta_dispatch_evidence_for_tests,
    get_last_meta_dispatch_evidence,
    mask_recipient_e164,
    record_meta_dispatch_request,
    record_meta_dispatch_response,
)
from services.whatsapp_providers.meta_cloud import (
    META_PROVIDER_GRAPH_BASE,
    build_meta_template_payload,
    send_via_meta,
)
from services.whatsapp_providers.contracts import (
    MODE_TEMPLATE,
    PROVIDER_META,
    WhatsAppProviderRequest,
)


class MaskRecipientTests(unittest.TestCase):
    def test_phone_masked(self) -> None:
        m = mask_recipient_e164("966546518011")
        self.assertTrue(m.startswith("+966"))
        self.assertTrue(m.endswith("11"))
        self.assertNotIn("546518", m)
        self.assertIn("*", m)


class SanitizeBuildTests(unittest.TestCase):
    def test_checkout_token_redacted_and_secrets_absent(self) -> None:
        payload = build_meta_template_payload(
            to_digits="966546518011",
            template_name="cartflow_cart_reminder_ar_v2",
            template_language="ar",
            template_parameters=["مساعد المتجر"],
            template_button_url_param="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc",
            quick_reply_payload="cartflow_customer_support_v1",
        )
        ev = build_sanitized_dispatch_evidence(
            graph_endpoint=f"{META_PROVIDER_GRAPH_BASE}/PNID123/messages",
            graph_version="v23.0",
            phone_number_id="PNID123",
            payload=payload,
        )
        blob = json.dumps(ev)
        self.assertNotIn("eyJ", blob)
        self.assertIn("[redacted]", blob)
        self.assertNotIn("Bearer", blob)
        self.assertNotIn("tok-secret", blob.lower())
        self.assertNotIn("546518", blob)
        self.assertEqual(ev["http_phone_number_id"], "PNID123")
        self.assertEqual(ev["http_template_name"], "cartflow_cart_reminder_ar_v2")
        self.assertTrue(ev["verification"]["checks"]["template_name_ok"])
        self.assertTrue(ev["verification"]["checks"]["url_button_present"])
        self.assertTrue(ev["verification"]["checks"]["quick_reply_present"])


class CaptureMatchesOutboundTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_meta_dispatch_evidence_for_tests()

    def _req(self) -> WhatsAppProviderRequest:
        return WhatsAppProviderRequest(
            to_phone="+966546518011",
            provider=PROVIDER_META,
            message_mode=MODE_TEMPLATE,
            template_name="cartflow_cart_reminder_ar_v2",
            template_language="ar",
            template_parameters=["مساعد المتجر"],
            template_button_url_param="opaque-checkout-token-ABCDEFG1234567890",
            recovery_key="demo:cf_wire_capture",
            store_slug="demo",
        )

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-NEVER",
            "WHATSAPP_PHONE_NUMBER_ID": "pn-wire-99",
            "WHATSAPP_BUSINESS_ACCOUNT_ID": "waba-wire-1",
            "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": "cartflow_cart_reminder_ar_v2",
        },
        clear=False,
    )
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_capture_matches_http_client_payload_on_failure(
        self, mock_post: MagicMock
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "error": {
                "message": "(#131030) Recipient phone number not in allowed list",
                "code": 131030,
                "fbtrace_id": "AbTrace1",
            }
        }
        mock_post.return_value = mock_resp

        out = send_via_meta(self._req())
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error_code"), "131030")

        # Exact outbound args used by HTTP client
        call_url = mock_post.call_args[0][0] if mock_post.call_args[0] else mock_post.call_args.kwargs.get("url")
        if call_url is None:
            call_url = mock_post.call_args.args[0]
        call_json = mock_post.call_args.kwargs.get("json")
        self.assertIn("pn-wire-99", call_url)
        self.assertEqual(call_json["template"]["name"], "cartflow_cart_reminder_ar_v2")

        ev = get_last_meta_dispatch_evidence()
        assert ev is not None
        self.assertEqual(ev["http_phone_number_id"], "pn-wire-99")
        self.assertEqual(ev["resolved_phone_number_id"], "pn-wire-99")
        self.assertEqual(ev["http_template_name"], call_json["template"]["name"])
        self.assertEqual(ev["request"]["graph_endpoint"], call_url)
        self.assertIn("/pn-wire-99/messages", ev["request"]["graph_endpoint"])
        self.assertEqual(ev["request"]["template"]["name"], "cartflow_cart_reminder_ar_v2")
        self.assertEqual(ev["request"]["template"]["language"]["code"], "ar")
        self.assertEqual(ev["response"]["http_status"], 400)
        self.assertEqual(ev["response"]["error"]["code"], 131030)
        dumped = json.dumps(ev)
        self.assertNotIn("tok-secret-NEVER", dumped)
        self.assertNotIn("Bearer", dumped)
        self.assertIn("[redacted]", dumped)
        # Result carries durable-attachable evidence
        self.assertIn("meta_dispatch_evidence", out)
        self.assertEqual(
            out["meta_dispatch_evidence"]["http_phone_number_id"], "pn-wire-99"
        )

    @patch.dict(
        os.environ,
        {
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-NEVER",
            "WHATSAPP_PHONE_NUMBER_ID": "pn-wire-ok",
        },
        clear=False,
    )
    @patch("services.whatsapp_providers.meta_cloud.requests.post")
    def test_evidence_on_success_path(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "wamid.WIREOK"}]}
        mock_post.return_value = mock_resp
        out = send_via_meta(self._req())
        self.assertTrue(out.get("ok"))
        ev = get_last_meta_dispatch_evidence()
        assert ev is not None
        self.assertEqual(ev["http_phone_number_id"], "pn-wire-ok")
        self.assertEqual(ev["response"]["http_status"], 200)
        self.assertTrue(ev["response"].get("accepted"))
        self.assertEqual(ev["response"]["messages"][0]["id"], "wamid.WIREOK")
        self.assertNotIn("tok-secret-NEVER", json.dumps(ev))


class RecordHelpersTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_meta_dispatch_evidence_for_tests()

    def test_record_roundtrip(self) -> None:
        payload = build_meta_template_payload(
            to_digits="966500000001",
            template_name="cartflow_cart_reminder_ar_v2",
            template_language="ar",
            template_parameters=["Shop"],
            template_button_url_param="shorttok",
            quick_reply_payload="cartflow_customer_support_v1",
        )
        # shorttok may not redact if < 20 chars - force long
        payload["template"]["components"][1]["parameters"][0]["text"] = "x" * 50
        record_meta_dispatch_request(
            graph_endpoint=f"{META_PROVIDER_GRAPH_BASE}/PID/messages",
            graph_version="v23.0",
            phone_number_id="PID",
            payload=payload,
            recovery_key="rk",
        )
        record_meta_dispatch_response(
            status_code=400,
            body={"error": {"code": 131030, "message": "Recipient phone number not in allowed list"}},
        )
        ev = get_last_meta_dispatch_evidence()
        assert ev is not None
        self.assertEqual(ev["response"]["error"]["code"], 131030)


class DevEndpointTests(unittest.TestCase):
    def test_route_allowlisted_in_source(self) -> None:
        from pathlib import Path

        main_src = Path("main.py").read_text(encoding="utf-8")
        self.assertIn('"/dev/meta-dispatch-request"', main_src)
        diag = Path("routes/dev_diagnostics.py").read_text(encoding="utf-8")
        self.assertIn("dev_meta_dispatch_request", diag)


if __name__ == "__main__":
    unittest.main()
