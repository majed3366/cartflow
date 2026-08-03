# -*- coding: utf-8 -*-
"""Isolated tests for Meta recovery template create tool (mocked HTTP only)."""
from __future__ import annotations

import json
import os
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from tools.meta.create_recovery_template_v1 import (
    TEMPLATE_BODY_TEXT,
    TEMPLATE_CATEGORY,
    TEMPLATE_EXAMPLE_VALUE,
    TEMPLATE_LANGUAGE,
    TEMPLATE_NAME,
    build_template_payload,
    compare_remote_to_contract,
    fetch_templates_by_name,
    main,
    run_create_recovery_template,
    submit_template_create,
    template_create_url,
    validate_template_contract,
)


class ContractTests(unittest.TestCase):
    def test_payload_body_only_no_header(self) -> None:
        payload = build_template_payload()
        errors = validate_template_contract(payload)
        self.assertEqual(errors, [])
        types = [c["type"] for c in payload["components"]]
        self.assertEqual(types, ["BODY"])
        self.assertNotIn("HEADER", types)
        self.assertNotIn("FOOTER", types)
        self.assertNotIn("BUTTONS", types)

    def test_exact_name_language_category(self) -> None:
        payload = build_template_payload()
        self.assertEqual(payload["name"], "cartflow_cart_reminder_ar_v1")
        self.assertEqual(payload["language"], "ar")
        self.assertEqual(payload["category"], "MARKETING")

    def test_exact_arabic_body(self) -> None:
        payload = build_template_payload()
        self.assertEqual(payload["components"][0]["text"], TEMPLATE_BODY_TEXT)
        self.assertIn("{{1}}", payload["components"][0]["text"])
        self.assertEqual(payload["components"][0]["text"].count("{{1}}"), 1)
        self.assertEqual(payload["components"][0]["text"].count("{{"), 1)

    def test_exact_example(self) -> None:
        payload = build_template_payload()
        self.assertEqual(
            payload["components"][0]["example"]["body_text"],
            [[TEMPLATE_EXAMPLE_VALUE]],
        )

    def test_validate_rejects_header(self) -> None:
        payload = build_template_payload()
        payload["components"].insert(0, {"type": "HEADER", "format": "TEXT", "text": "x"})
        errors = validate_template_contract(payload)
        self.assertIn("header_component_forbidden", errors)


class DryRunAndGateTests(unittest.TestCase):
    @patch("tools.meta.create_recovery_template_v1.requests.get")
    @patch("tools.meta.create_recovery_template_v1.requests.post")
    def test_dry_run_performs_no_http(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "WHATSAPP_ACCESS_TOKEN": "tok-secret",
                "WHATSAPP_BUSINESS_ACCOUNT_ID": "123456789012345",
            },
            clear=False,
        ):
            out = run_create_recovery_template(execute=False)
        self.assertTrue(out["ok"])
        self.assertTrue(out["dry_run"])
        self.assertEqual(out["status"], "DRY_RUN")
        mock_post.assert_not_called()
        mock_get.assert_not_called()

    @patch("tools.meta.create_recovery_template_v1.requests.post")
    def test_execution_requires_execute_flag_via_main(self, mock_post: MagicMock) -> None:
        with patch.dict(
            os.environ,
            {
                "WHATSAPP_ACCESS_TOKEN": "tok-secret",
                "WHATSAPP_BUSINESS_ACCOUNT_ID": "123456789012345",
            },
            clear=False,
        ):
            code = main([])  # no --execute
        self.assertEqual(code, 0)
        mock_post.assert_not_called()

    @patch("tools.meta.create_recovery_template_v1.requests.get")
    @patch("tools.meta.create_recovery_template_v1.requests.post")
    def test_missing_token_fails_before_http(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WHATSAPP_ACCESS_TOKEN", None)
            os.environ["WHATSAPP_BUSINESS_ACCOUNT_ID"] = "123456789012345"
            out = run_create_recovery_template(execute=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "meta_access_token_missing")
        mock_post.assert_not_called()
        mock_get.assert_not_called()

    @patch("tools.meta.create_recovery_template_v1.requests.get")
    @patch("tools.meta.create_recovery_template_v1.requests.post")
    def test_missing_waba_fails_before_http(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        with patch.dict(os.environ, {"WHATSAPP_ACCESS_TOKEN": "tok-secret"}, clear=False):
            os.environ.pop("WHATSAPP_BUSINESS_ACCOUNT_ID", None)
            os.environ.pop("WABA_ID", None)
            out = run_create_recovery_template(execute=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "meta_waba_id_missing")
        mock_post.assert_not_called()
        mock_get.assert_not_called()


class ExecutePathTests(unittest.TestCase):
    def _env(self) -> dict[str, str]:
        return {
            "WHATSAPP_ACCESS_TOKEN": "tok-secret-NEVER-LOG",
            "WHATSAPP_BUSINESS_ACCOUNT_ID": "111222333444555",
        }

    @patch("tools.meta.create_recovery_template_v1.requests.get")
    @patch("tools.meta.create_recovery_template_v1.requests.post")
    def test_successful_pending_response(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: {"data": []}
        )
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "id": "tpl_123",
                "status": "PENDING",
                "category": "MARKETING",
            },
        )
        with patch.dict(os.environ, self._env(), clear=False):
            out = run_create_recovery_template(execute=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["template_id"], "tpl_123")
        self.assertEqual(out["status"], "PENDING")
        self.assertEqual(out["category"], "MARKETING")
        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        self.assertIn("/message_templates", url)
        self.assertNotIn("/messages", url.replace("/message_templates", ""))
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["name"], TEMPLATE_NAME)
        self.assertEqual(payload["language"], TEMPLATE_LANGUAGE)
        self.assertEqual(payload["category"], TEMPLATE_CATEGORY)

    @patch("tools.meta.create_recovery_template_v1.requests.get")
    @patch("tools.meta.create_recovery_template_v1.requests.post")
    def test_safe_meta_error_parsing(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"data": []})
        mock_post.return_value = MagicMock(
            status_code=400,
            json=lambda: {
                "error": {
                    "message": "Invalid OAuth access token.",
                    "code": 190,
                    "error_subcode": 463,
                }
            },
        )
        with patch.dict(os.environ, self._env(), clear=False):
            out = run_create_recovery_template(execute=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "190")
        self.assertEqual(out["error_subcode"], "463")
        self.assertEqual(out["error_message_safe"], "meta_auth_or_token_error")
        self.assertNotIn("tok-secret-NEVER-LOG", str(out))

    @patch("tools.meta.create_recovery_template_v1.requests.get")
    @patch("tools.meta.create_recovery_template_v1.requests.post")
    def test_existing_same_template_stops(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "id": "existing1",
                        "name": TEMPLATE_NAME,
                        "language": TEMPLATE_LANGUAGE,
                        "category": TEMPLATE_CATEGORY,
                        "status": "APPROVED",
                        "components": [
                            {"type": "BODY", "text": TEMPLATE_BODY_TEXT},
                        ],
                    }
                ]
            },
        )
        with patch.dict(os.environ, self._env(), clear=False):
            out = run_create_recovery_template(execute=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "template_already_exists")
        self.assertEqual(out["existing_comparison"], "SAME")
        mock_post.assert_not_called()

    @patch("tools.meta.create_recovery_template_v1.requests.get")
    @patch("tools.meta.create_recovery_template_v1.requests.post")
    def test_existing_different_template_stops(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "id": "existing2",
                        "name": TEMPLATE_NAME,
                        "language": TEMPLATE_LANGUAGE,
                        "category": TEMPLATE_CATEGORY,
                        "status": "APPROVED",
                        "components": [
                            {
                                "type": "BODY",
                                "text": "نص مختلف تماماً مع {{1}}",
                            }
                        ],
                    }
                ]
            },
        )
        with patch.dict(os.environ, self._env(), clear=False):
            out = run_create_recovery_template(execute=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["existing_comparison"], "DIFFERENT")
        mock_post.assert_not_called()

    @patch("tools.meta.create_recovery_template_v1.requests.get")
    @patch("tools.meta.create_recovery_template_v1.requests.post")
    def test_no_secrets_in_logs(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"data": []})
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "1", "status": "PENDING", "category": "MARKETING"},
        )
        buf = StringIO()
        with patch.dict(os.environ, self._env(), clear=False):
            with patch("sys.stdout", buf):
                run_create_recovery_template(execute=True)
                # also dry-run print path
                run_create_recovery_template(execute=False)
        printed = buf.getvalue()
        self.assertNotIn("tok-secret-NEVER-LOG", printed)
        self.assertNotIn("Bearer ", printed)
        self.assertIn("REDACTED", printed)

    def test_no_whatsapp_message_endpoint_in_create_url(self) -> None:
        url = template_create_url("999888777")
        self.assertTrue(url.endswith("/999888777/message_templates"))
        self.assertNotIn("/messages", url.replace("/message_templates", ""))

    def test_compare_helper(self) -> None:
        same = {
            "name": TEMPLATE_NAME,
            "language": TEMPLATE_LANGUAGE,
            "category": TEMPLATE_CATEGORY,
            "components": [{"type": "BODY", "text": TEMPLATE_BODY_TEXT}],
        }
        self.assertEqual(compare_remote_to_contract(same), "SAME")
        diff = dict(same)
        diff["components"] = [{"type": "BODY", "text": "other {{1}}"}]
        self.assertEqual(compare_remote_to_contract(diff), "DIFFERENT")


class UnitHttpHelperTests(unittest.TestCase):
    def test_fetch_and_submit_helpers_use_message_templates(self) -> None:
        session = MagicMock()
        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = {"data": []}
        session.get.return_value = get_resp
        out = fetch_templates_by_name(
            waba_id="123",
            access_token="tok",
            name=TEMPLATE_NAME,
            session=session,
        )
        self.assertTrue(out["ok"])
        self.assertIn("message_templates", session.get.call_args[0][0])

        post_resp = MagicMock(status_code=200)
        post_resp.json.return_value = {"id": "x", "status": "PENDING"}
        session.post.return_value = post_resp
        created = submit_template_create(
            waba_id="123",
            access_token="tok",
            payload=build_template_payload(),
            session=session,
        )
        self.assertTrue(created["ok"])
        self.assertIn("message_templates", session.post.call_args[0][0])
        self.assertNotIn(
            "/messages",
            session.post.call_args[0][0].replace("/message_templates", ""),
        )


if __name__ == "__main__":
    unittest.main()
