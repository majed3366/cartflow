# -*- coding: utf-8 -*-
"""Meta Recovery Template V2 contract + ops (mocked Graph; no message send)."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from services.meta_recovery_template_contract_v1 import (
    BUTTON_QUICK_REPLY_TEXT,
    BUTTON_URL_TEXT,
    COMPARISON_DIFFERENT,
    COMPARISON_SAME,
    STATUS_APPROVED,
    STATUS_NOT_CREATED,
    TEMPLATE_BODY_TEXT,
    TEMPLATE_NAME,
    TEMPLATE_NAME_V1,
    TEMPLATE_URL_BUTTON_EXAMPLE_SUFFIX,
    build_template_payload,
    button_checkout_url_with_variable,
    compare_remote_to_contract,
    local_contract_summary,
    validate_template_contract,
)
from services.meta_template_operations_v1 import create_recovery_template, get_recovery_template_status
from services.whatsapp_provider import (
    META_RECOVERY_TEMPLATE_CARTFLOW_V2,
    resolve_meta_template_button_url_param,
    resolve_meta_template_parameters,
)


def _env_ok() -> dict[str, str]:
    return {
        "WHATSAPP_ACCESS_TOKEN": "tok-secret-NEVER-EXPOSE",
        "WHATSAPP_BUSINESS_ACCOUNT_ID": "111222333444555",
    }


def _v2_remote(*, status: str = "APPROVED", mutate=None) -> dict:
    payload = build_template_payload()
    remote = {
        "id": "tpl_v2_1",
        "name": TEMPLATE_NAME,
        "language": "ar",
        "category": "MARKETING",
        "status": status,
        "components": payload["components"],
    }
    if mutate:
        mutate(remote)
    return remote


class V2ContractTests(unittest.TestCase):
    def test_exact_v2_name(self) -> None:
        self.assertEqual(TEMPLATE_NAME, "cartflow_cart_reminder_ar_v2")
        self.assertEqual(META_RECOVERY_TEMPLATE_CARTFLOW_V2, TEMPLATE_NAME)
        self.assertEqual(TEMPLATE_NAME_V1, "cartflow_cart_reminder_ar_v1")
        self.assertNotEqual(TEMPLATE_NAME, TEMPLATE_NAME_V1)

    def test_body_unchanged_and_one_variable(self) -> None:
        payload = build_template_payload()
        body = payload["components"][0]
        self.assertEqual(body["text"], TEMPLATE_BODY_TEXT)
        self.assertIn("{{1}}", body["text"])
        self.assertEqual(body["text"].count("{{"), 1)

    def test_url_and_quick_reply_buttons(self) -> None:
        payload = build_template_payload()
        types = [c["type"] for c in payload["components"]]
        self.assertNotIn("HEADER", types)
        self.assertNotIn("FOOTER", types)
        buttons = payload["components"][1]["buttons"]
        self.assertEqual(buttons[0]["type"], "URL")
        self.assertEqual(buttons[0]["text"], BUTTON_URL_TEXT)
        self.assertEqual(buttons[0]["url"], "https://smartreplyai.net/wa/checkout/{{1}}")
        self.assertEqual(button_checkout_url_with_variable(), buttons[0]["url"])
        self.assertEqual(buttons[0]["example"], [TEMPLATE_URL_BUTTON_EXAMPLE_SUFFIX])
        self.assertEqual(TEMPLATE_URL_BUTTON_EXAMPLE_SUFFIX, "demo-checkout-token")
        self.assertEqual(buttons[1]["type"], "QUICK_REPLY")
        self.assertEqual(buttons[1]["text"], BUTTON_QUICK_REPLY_TEXT)

    def test_validate_accepts_canonical_payload(self) -> None:
        self.assertEqual(validate_template_contract(build_template_payload()), [])

    def test_v1_preserved_in_summary(self) -> None:
        summary = local_contract_summary()
        self.assertEqual(summary["template_name"], TEMPLATE_NAME)
        self.assertEqual(summary["historical_template_name_v1"], TEMPLATE_NAME_V1)
        self.assertTrue(summary["preserves_v1"])
        self.assertIn("overwrite_v1", summary["forbidden"])
        self.assertIn("delete_v1", summary["forbidden"])


class V2ComparisonTests(unittest.TestCase):
    def test_same_when_remote_matches(self) -> None:
        self.assertEqual(compare_remote_to_contract(_v2_remote()), COMPARISON_SAME)

    def test_different_when_body_only(self) -> None:
        remote = _v2_remote()
        remote["components"] = [remote["components"][0]]
        self.assertEqual(compare_remote_to_contract(remote), COMPARISON_DIFFERENT)

    def test_different_when_v1_name(self) -> None:
        remote = _v2_remote()
        remote["name"] = TEMPLATE_NAME_V1
        self.assertEqual(compare_remote_to_contract(remote), COMPARISON_DIFFERENT)


class V2OpsTests(unittest.TestCase):
    @patch("services.meta_template_operations_v1.requests.post")
    @patch("services.meta_template_operations_v1.requests.get")
    def test_status_not_created(self, mock_get: MagicMock, mock_post: MagicMock) -> None:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"data": []})
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = get_recovery_template_status()
        self.assertTrue(out["ok"])
        self.assertEqual(out["template_name"], TEMPLATE_NAME)
        self.assertEqual(out["status"], STATUS_NOT_CREATED)
        self.assertFalse(out["exists"])
        self.assertTrue(out["can_create"])
        self.assertEqual(out.get("historical_template_name_v1"), TEMPLATE_NAME_V1)
        mock_post.assert_not_called()
        # Must not call WhatsApp /messages
        for call in mock_get.call_args_list:
            url = str(call.args[0] if call.args else call.kwargs.get("url") or "")
            self.assertNotIn("/messages", url)

    @patch("services.meta_template_operations_v1.requests.post")
    @patch("services.meta_template_operations_v1.requests.get")
    def test_create_once_and_duplicate_blocked(
        self, mock_get: MagicMock, mock_post: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"data": []})
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "new_tpl", "status": "PENDING"},
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            created = create_recovery_template(confirm=True, template_name=TEMPLATE_NAME)
        self.assertTrue(created["ok"])
        self.assertTrue(created.get("created"))
        mock_post.assert_called_once()
        post_url = str(mock_post.call_args.args[0])
        self.assertIn("/message_templates", post_url)
        self.assertNotIn("/messages", post_url)

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [_v2_remote(status="APPROVED")]},
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            dup = create_recovery_template(confirm=True, template_name=TEMPLATE_NAME)
        self.assertFalse(dup["ok"])
        self.assertEqual(dup["error_code"], "template_already_exists")
        self.assertEqual(dup["comparison"], COMPARISON_SAME)
        self.assertEqual(mock_post.call_count, 1)

    @patch("services.meta_template_operations_v1.requests.post")
    @patch("services.meta_template_operations_v1.requests.get")
    def test_never_create_or_overwrite_v1(
        self, mock_get: MagicMock, mock_post: MagicMock
    ) -> None:
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = create_recovery_template(confirm=True, template_name=TEMPLATE_NAME_V1)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "v1_immutable")
        mock_get.assert_not_called()
        mock_post.assert_not_called()

    @patch("services.meta_template_operations_v1.requests.post")
    @patch("services.meta_template_operations_v1.requests.get")
    def test_same_different_status_comparison(
        self, mock_get: MagicMock, mock_post: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [_v2_remote(status="APPROVED")]},
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            same = get_recovery_template_status()
        self.assertEqual(same["comparison"], COMPARISON_SAME)
        self.assertEqual(same["status"], STATUS_APPROVED)

        remote = _v2_remote()
        remote["components"][0]["text"] = "other body"
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [remote]},
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            diff = get_recovery_template_status()
        self.assertEqual(diff["comparison"], COMPARISON_DIFFERENT)
        mock_post.assert_not_called()


class V2RuntimeMappingTests(unittest.TestCase):
    def test_body_uses_store_display_name(self) -> None:
        params, err = resolve_meta_template_parameters(
            {"store_display_name": "متجر الأمان"},
            template_name=TEMPLATE_NAME,
        )
        self.assertIsNone(err)
        self.assertEqual(params, ["متجر الأمان"])

    def test_button_uses_redirect_token_not_raw_url(self) -> None:
        with patch(
            "services.recovery_checkout_redirect_v1.mint_token_from_send_context",
            return_value="opaque-token-xyz",
        ):
            token, err = resolve_meta_template_button_url_param(
                {"checkout_url": "https://merchant.com/cart/abc"},
                template_name=TEMPLATE_NAME,
            )
        self.assertIsNone(err)
        self.assertEqual(token, "opaque-token-xyz")
        self.assertNotIn("https://", token or "")

    def test_v1_does_not_require_button_param(self) -> None:
        token, err = resolve_meta_template_button_url_param(
            {"checkout_url": "https://merchant.com/cart/abc"},
            template_name=TEMPLATE_NAME_V1,
        )
        self.assertIsNone(token)
        self.assertIsNone(err)


if __name__ == "__main__":
    unittest.main()
