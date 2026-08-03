# -*- coding: utf-8 -*-
"""Isolated tests for Meta Template Operations V1 (mocked Graph only)."""
from __future__ import annotations

import os
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from services.meta_recovery_template_contract_v1 import (
    COMPARISON_DIFFERENT,
    COMPARISON_SAME,
    STATUS_APPROVED,
    STATUS_NOT_CREATED,
    STATUS_PENDING,
    STATUS_REJECTED,
    TEMPLATE_BODY_TEXT,
    TEMPLATE_CATEGORY,
    TEMPLATE_EXAMPLE_VALUE,
    TEMPLATE_LANGUAGE,
    TEMPLATE_NAME,
    build_template_payload,
    normalize_meta_template_status,
    validate_template_contract,
)
from services.meta_template_operations_v1 import (
    create_recovery_template,
    get_recovery_template_status,
    list_meta_templates,
)
from services.whatsapp_provider import resolve_whatsapp_provider


def _env_ok() -> dict[str, str]:
    return {
        "WHATSAPP_ACCESS_TOKEN": "tok-secret-NEVER-EXPOSE",
        "WHATSAPP_BUSINESS_ACCOUNT_ID": "111222333444555",
    }


def _body_only_remote(*, status: str = "APPROVED", text=None) -> dict:
    return {
        "id": "tpl_remote_1",
        "name": TEMPLATE_NAME,
        "language": TEMPLATE_LANGUAGE,
        "category": TEMPLATE_CATEGORY,
        "status": status,
        "components": [{"type": "BODY", "text": text or TEMPLATE_BODY_TEXT}],
    }


class CredentialGateTests(unittest.TestCase):
    @patch("services.meta_template_operations_v1.requests.get")
    @patch("services.meta_template_operations_v1.requests.post")
    def test_missing_access_token(self, mock_post: MagicMock, mock_get: MagicMock) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ["WHATSAPP_BUSINESS_ACCOUNT_ID"] = "111222333444555"
            out = get_recovery_template_status()
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "meta_access_token_missing")
        self.assertNotIn("access_token", out)
        self.assertNotIn("tok-secret", str(out))
        mock_get.assert_not_called()
        mock_post.assert_not_called()

    @patch("services.meta_template_operations_v1.requests.get")
    @patch("services.meta_template_operations_v1.requests.post")
    def test_missing_waba_id(self, mock_post: MagicMock, mock_get: MagicMock) -> None:
        with patch.dict(
            os.environ,
            {"WHATSAPP_ACCESS_TOKEN": "tok-secret-NEVER-EXPOSE"},
            clear=True,
        ):
            out = list_meta_templates()
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "meta_waba_id_missing")
        mock_get.assert_not_called()
        mock_post.assert_not_called()


class ListAndStatusTests(unittest.TestCase):
    @patch("services.meta_template_operations_v1.requests.get")
    def test_list_templates_success(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "id": "1",
                        "name": "hello_world",
                        "status": "APPROVED",
                        "category": "UTILITY",
                        "language": "en_US",
                    }
                ]
            },
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = list_meta_templates()
        self.assertTrue(out["ok"])
        self.assertEqual(out["operation"], "list_templates")
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["templates"][0]["template_name"], "hello_world")
        self.assertEqual(out["templates"][0]["status"], STATUS_APPROVED)
        url = mock_get.call_args[0][0]
        self.assertIn("/message_templates", url)
        self.assertNotIn(
            "/messages",
            url.replace("/message_templates", ""),
        )

    @patch("services.meta_template_operations_v1.requests.get")
    def test_safe_meta_error_parsing(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MagicMock(
            status_code=401,
            json=lambda: {
                "error": {
                    "message": "Invalid OAuth access token.",
                    "code": 190,
                    "error_subcode": 463,
                }
            },
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = get_recovery_template_status()
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "190")
        self.assertEqual(out["error_subcode"], "463")
        self.assertEqual(out["error_message_safe"], "meta_auth_or_token_error")
        self.assertNotIn("tok-secret-NEVER-EXPOSE", str(out))

    @patch("services.meta_template_operations_v1.requests.get")
    def test_approved_template_found(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [_body_only_remote(status="APPROVED")]},
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = get_recovery_template_status()
        self.assertTrue(out["ok"])
        self.assertEqual(out["status"], STATUS_APPROVED)
        self.assertEqual(out["comparison"], COMPARISON_SAME)
        self.assertFalse(out["can_create"])
        self.assertTrue(out["exists"])

    @patch("services.meta_template_operations_v1.requests.get")
    def test_pending_template_found(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [_body_only_remote(status="PENDING")]},
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = get_recovery_template_status()
        self.assertEqual(out["status"], STATUS_PENDING)
        self.assertNotEqual(out["status"], STATUS_APPROVED)

    @patch("services.meta_template_operations_v1.requests.get")
    def test_rejected_template_found(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [_body_only_remote(status="REJECTED")]},
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = get_recovery_template_status()
        self.assertEqual(out["status"], STATUS_REJECTED)

    def test_status_normalization(self) -> None:
        self.assertEqual(normalize_meta_template_status("APPROVED"), STATUS_APPROVED)
        self.assertEqual(normalize_meta_template_status("PENDING"), STATUS_PENDING)
        self.assertEqual(normalize_meta_template_status("REJECTED"), STATUS_REJECTED)
        self.assertEqual(normalize_meta_template_status(""), "UNKNOWN")


class DuplicateSafetyTests(unittest.TestCase):
    @patch("services.meta_template_operations_v1.requests.get")
    @patch("services.meta_template_operations_v1.requests.post")
    def test_existing_same_does_not_post(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [_body_only_remote()]},
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = create_recovery_template(confirm=True, template_name=TEMPLATE_NAME)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "template_already_exists")
        self.assertEqual(out["comparison"], COMPARISON_SAME)
        mock_post.assert_not_called()

    @patch("services.meta_template_operations_v1.requests.get")
    @patch("services.meta_template_operations_v1.requests.post")
    def test_existing_different_does_not_post(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [_body_only_remote(text="نص مختلف مع {{1}}")]
            },
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = create_recovery_template(confirm=True, template_name=TEMPLATE_NAME)
        self.assertFalse(out["ok"])
        self.assertEqual(out["comparison"], COMPARISON_DIFFERENT)
        mock_post.assert_not_called()

    @patch("services.meta_template_operations_v1.requests.get")
    @patch("services.meta_template_operations_v1.requests.post")
    def test_missing_template_allows_creation(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"data": []})
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "id": "new_tpl",
                "status": "PENDING",
                "category": "MARKETING",
            },
        )
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = create_recovery_template(confirm=True, template_name=TEMPLATE_NAME)
        self.assertTrue(out["ok"])
        self.assertTrue(out["created"])
        self.assertEqual(out["status"], STATUS_PENDING)
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        types = [c["type"] for c in payload["components"]]
        self.assertEqual(types, ["BODY"])
        self.assertNotIn("HEADER", types)
        self.assertEqual(payload["components"][0]["text"], TEMPLATE_BODY_TEXT)
        self.assertEqual(
            payload["components"][0]["example"]["body_text"],
            [[TEMPLATE_EXAMPLE_VALUE]],
        )
        url = mock_post.call_args[0][0]
        self.assertIn("/message_templates", url)
        self.assertNotIn("/messages", url.replace("/message_templates", ""))

    def test_create_requires_confirmation(self) -> None:
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = create_recovery_template(confirm=False, template_name=TEMPLATE_NAME)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_code"], "confirmation_required")

    def test_create_requires_exact_name(self) -> None:
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = create_recovery_template(confirm=True, template_name="other_name")
        self.assertEqual(out["error_code"], "template_name_mismatch")


class ContractAndProviderTests(unittest.TestCase):
    def test_payload_body_only_exact_arabic(self) -> None:
        payload = build_template_payload()
        self.assertEqual(validate_template_contract(payload), [])
        self.assertEqual(payload["components"][0]["text"], TEMPLATE_BODY_TEXT)
        self.assertEqual(
            payload["components"][0]["example"]["body_text"],
            [[TEMPLATE_EXAMPLE_VALUE]],
        )
        types = [c["type"] for c in payload["components"]]
        self.assertEqual(types, ["BODY"])
        self.assertNotIn("HEADER", types)

    def test_production_provider_default_twilio(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WHATSAPP_PROVIDER", None)
            self.assertEqual(resolve_whatsapp_provider(), "twilio")

    @patch("services.meta_template_operations_v1.requests.get")
    @patch("services.meta_template_operations_v1.requests.post")
    def test_token_never_in_logs(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"data": []})
        buf = StringIO()
        with patch.dict(os.environ, _env_ok(), clear=False):
            with patch("sys.stdout", buf):
                get_recovery_template_status()
        printed = buf.getvalue()
        self.assertNotIn("tok-secret-NEVER-EXPOSE", printed)
        self.assertNotIn("Bearer ", printed)
        with patch.dict(os.environ, _env_ok(), clear=False):
            with patch(
                "services.meta_template_operations_v1.requests.get",
                return_value=MagicMock(status_code=200, json=lambda: {"data": []}),
            ):
                out = get_recovery_template_status()
        self.assertNotIn("tok-secret-NEVER-EXPOSE", str(out))
        self.assertNotIn("access_token", out)


class AdminRouteAuthTests(unittest.TestCase):
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

    def test_admin_auth_required_list(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "meta-tpl-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.get("/admin/api/whatsapp/meta-templates")
        self.assertEqual(r.status_code, 401)

    def test_admin_auth_required_create(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "meta-tpl-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.post(
            "/admin/api/whatsapp/meta-templates/recovery-contract/create",
            json={"confirm": True, "template_name": TEMPLATE_NAME},
        )
        self.assertEqual(r.status_code, 401)

    @patch("services.meta_template_operations_v1.get_recovery_template_status")
    def test_recovery_contract_ok_with_session(self, mock_status: MagicMock) -> None:
        from fastapi.testclient import TestClient

        from main import app

        mock_status.return_value = {
            "ok": True,
            "operation": "recovery_template_status",
            "template_name": TEMPLATE_NAME,
            "status": STATUS_NOT_CREATED,
            "comparison": "NOT_AVAILABLE",
            "can_create": True,
            "waba_masked": "111…555",
            "trace_id": "abc",
        }
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "meta-tpl-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "meta-tpl-auth-test", "next": "/admin/whatsapp"},
        )
        r = client.get("/admin/api/whatsapp/meta-templates/recovery-contract")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertNotIn("access_token", body)
        self.assertNotIn("token", body)

    @patch("services.meta_template_operations_v1.create_recovery_template")
    def test_create_route_requires_confirm_field(self, mock_create: MagicMock) -> None:
        from fastapi.testclient import TestClient

        from main import app

        mock_create.return_value = {
            "ok": False,
            "error_code": "confirmation_required",
            "operation": "create_recovery_template",
        }
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "meta-tpl-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "meta-tpl-auth-test", "next": "/admin/whatsapp"},
        )
        r = client.post(
            "/admin/api/whatsapp/meta-templates/recovery-contract/create",
            json={"confirm": False, "template_name": TEMPLATE_NAME},
        )
        self.assertEqual(r.status_code, 200)
        mock_create.assert_called()
        kwargs = mock_create.call_args.kwargs
        self.assertIs(kwargs.get("confirm"), False)

    @patch("services.admin_whatsapp_meta_send_test_v1.send_meta_whatsapp_test_message")
    def test_hello_world_admin_test_still_functional(self, mock_send: MagicMock) -> None:
        from fastapi.testclient import TestClient

        from main import app

        mock_send.return_value = {
            "ok": True,
            "provider": "meta",
            "message_id": "wamid.HELLO",
            "error": None,
        }
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "meta-tpl-auth-test"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "meta-tpl-auth-test", "next": "/admin/whatsapp"},
        )
        r = client.post(
            "/admin/api/whatsapp/meta-send-test",
            json={"to": "+966501234567"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))


class NotCreatedAllowsCreateUiFlag(unittest.TestCase):
    @patch("services.meta_template_operations_v1.requests.get")
    def test_not_created_sets_can_create(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"data": []})
        with patch.dict(os.environ, _env_ok(), clear=False):
            out = get_recovery_template_status()
        self.assertTrue(out["ok"])
        self.assertEqual(out["status"], STATUS_NOT_CREATED)
        self.assertTrue(out["can_create"])


if __name__ == "__main__":
    unittest.main()
